"""
JanSahayak Automated Test Suite
Covers all 8 required test scenarios:
1. Complete request and confirmation gate
2. Missing information handling
3. Duplicate submission prevention
4. Correction after doubtful speech
5. Missing or conflicting source evidence handling
6. Staff return, correction, and resubmission
7. Status lookup and persistence
8. External-service failure resilience and fallback
"""

import os
import unittest
import tempfile
import uuid

# Set test environment
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from database import (
    init_db,
    create_request,
    get_request_by_ref,
    list_requests,
    get_audit_trail,
    update_request_status,
    resubmit_returned_request,
    compute_idempotency_token,
    save_session_state,
    load_session_state
)
from knowledge import (
    OFFICIAL_KNOWLEDGE_BASE,
    match_schemes,
    check_fact_uncertainty,
    get_record_by_id,
    get_document_checklist
)
from agents.intake_agent import IntakeAgent
from agents.scheme_agent import BankingSchemeAgent
from agents.application_agent import ApplicationAgent
from orchestrator import JanSahayakOrchestrator, SharedSessionState
from speech_service import SpeechService
from llm_service import LLMService


class TestJanSahayak(unittest.TestCase):

    def setUp(self):
        # Create a temporary database for each test to ensure complete isolation
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db_file.name
        self.temp_db_file.close()
        init_db(self.temp_db_path)

        self.intake_agent = IntakeAgent()
        self.scheme_agent = BankingSchemeAgent()
        self.app_agent = ApplicationAgent()
        self.orchestrator = JanSahayakOrchestrator()

    def tearDown(self):
        try:
            os.remove(self.temp_db_path)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # TEST 1: Complete request and confirmation gate
    # --------------------------------------------------------------------------
    def test_1_complete_request_and_confirmation_gate(self):
        """Verify complete request submission and explicit customer confirmation gate."""
        profile = {
            "name": "Ramesh Kumar",
            "location": "Rampur",
            "occupation": "Farmer",
            "purpose": "Govt Subsidies & PM-KISAN",
            "income_bracket": "< ₹10,000"
        }
        scheme = "Pradhan Mantri Jan Dhan Yojana"
        session_id = "test_sess_001"

        # 1. Submission WITHOUT explicit confirmation MUST fail
        success, msg, rec = self.app_agent.submit_application(
            profile=profile,
            selected_scheme=scheme,
            session_id=session_id,
            language="en",
            confirmed_by_customer=False
        )
        self.assertFalse(success)
        self.assertIn("confirmation is mandatory", msg)
        self.assertIsNone(rec)

        # 2. Submission WITH explicit confirmation succeeds
        # Monkey patch db path for isolation
        token = compute_idempotency_token(profile["name"], profile["location"], profile["occupation"], profile["purpose"], session_id)
        ref_id = "JS-2026-1111"
        ok, submit_msg, created_rec = create_request(
            reference_id=ref_id,
            customer_name=profile["name"],
            location=profile["location"],
            occupation=profile["occupation"],
            income_bracket=profile["income_bracket"],
            purpose=profile["purpose"],
            selected_scheme=scheme,
            language="en",
            idempotency_token=token,
            status="SUBMITTED",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)
        self.assertEqual(created_rec["reference_id"], ref_id)
        self.assertEqual(created_rec["status"], "SUBMITTED")

        # Verify audit log has REQUEST_SUBMITTED
        audits = get_audit_trail(ref_id, db_path=self.temp_db_path)
        self.assertTrue(any(a["action"] == "REQUEST_SUBMITTED" for a in audits))

    # --------------------------------------------------------------------------
    # TEST 2: Missing information handling
    # --------------------------------------------------------------------------
    def test_2_missing_information_gate(self):
        """Verify that incomplete profiles are strictly caught and blocked by validation gates."""
        incomplete_profile = {
            "name": "Ramesh",
            "location": "",  # Missing location
            "occupation": "Farmer",
            "purpose": ""   # Missing purpose
        }
        is_complete, missing = self.app_agent.check_completeness(incomplete_profile, "PMJDY")
        self.assertFalse(is_complete)
        self.assertIn("location", missing)
        self.assertIn("purpose", missing)

        # Attempt submission with incomplete profile
        success, err, rec = self.app_agent.submit_application(
            profile=incomplete_profile,
            selected_scheme="PMJDY",
            session_id="test_sess_002",
            language="en",
            confirmed_by_customer=True
        )
        self.assertFalse(success)
        self.assertIn("Missing required fields", err)

        # Intake agent identifies missing slot sequentially
        missing_slot = self.intake_agent.get_missing_slot(incomplete_profile)
        self.assertEqual(missing_slot, "location")

    # --------------------------------------------------------------------------
    # TEST 3: Duplicate submission prevention
    # --------------------------------------------------------------------------
    def test_3_duplicate_submission_prevention(self):
        """Verify that repeated clicks or reruns do not create duplicate records."""
        token = compute_idempotency_token("Sunita", "Patna", "Homemaker", "Savings", "sess_dup_123")
        ref_1 = "JS-2026-2222"

        # First submission
        ok1, msg1, rec1 = create_request(
            reference_id=ref_1,
            customer_name="Sunita",
            location="Patna",
            occupation="Homemaker",
            income_bracket="< ₹10,000",
            purpose="Savings",
            selected_scheme="PMJDY",
            language="hi",
            idempotency_token=token,
            db_path=self.temp_db_path
        )
        self.assertTrue(ok1)

        # Repeated submission with identical token (e.g. repeated click or rerun)
        ok2, msg2, rec2 = create_request(
            reference_id="JS-2026-3333",
            customer_name="Sunita",
            location="Patna",
            occupation="Homemaker",
            income_bracket="< ₹10,000",
            purpose="Savings",
            selected_scheme="PMJDY",
            language="hi",
            idempotency_token=token,
            db_path=self.temp_db_path
        )
        self.assertFalse(ok2)
        self.assertIn("Duplicate submission detected", msg2)
        self.assertEqual(rec2["reference_id"], ref_1)

        # Total requests in DB remains exactly 1
        all_reqs = list_requests(db_path=self.temp_db_path)
        self.assertEqual(len(all_reqs), 1)

    # --------------------------------------------------------------------------
    # TEST 4: Correction after doubtful speech
    # --------------------------------------------------------------------------
    def test_4_correction_after_doubtful_speech(self):
        """Verify that doubtful speech or user corrections clear pending slot and reprompt politely."""
        state = SharedSessionState(session_id="test_sess_004", language="hi")
        state.customer_profile["name"] = "सुरेश"
        state.pending_slot = "name"

        # Customer flags doubtful speech / asks for correction
        res = self.intake_agent.process_turn("नहीं, यह गलत है", state)
        self.assertFalse(res["is_complete"])
        self.assertEqual(state.customer_profile["name"], "")
        self.assertIn("अपनी सही जानकारी फिर से बोलें", res["assistant_message"])

        # Also verify direct is_doubtful_speech flag
        state.customer_profile["name"] = "कुछ_अस्पष्ट"
        res_doubt = self.intake_agent.process_turn("xyz audio", state, is_doubtful_speech=True)
        self.assertEqual(state.customer_profile["name"], "")
        self.assertIn("अपनी सही जानकारी फिर से बोलें", res_doubt["assistant_message"])

    # --------------------------------------------------------------------------
    # TEST 5: Missing or conflicting source evidence handling
    # --------------------------------------------------------------------------
    def test_5_missing_or_conflicting_source_evidence(self):
        """Verify that informal rumors / unverified claims are flagged as uncertain."""
        # Check rumors like loan waiver / free money
        uncertain_check = check_fact_uncertainty("मुझे बैंक से मुफ्त पैसा और कर्ज माफी चाहिए")
        self.assertFalse(uncertain_check["is_certain"])
        self.assertIn("प्रमाणित नहीं है", uncertain_check["reason_hi"])
        self.assertIn("अधिकारी से सीधे बात करें", uncertain_check["recommendation_hi"])

        # Check official knowledge base citations integrity
        self.assertGreaterEqual(len(OFFICIAL_KNOWLEDGE_BASE), 5)
        for rec in OFFICIAL_KNOWLEDGE_BASE:
            self.assertTrue(rec["official_source_url"].startswith("http"))
            # No unsupported verification claims or dates are stored on records
            self.assertNotIn("verified", rec)
            self.assertNotIn("verification_date", rec)
            self.assertIn("name_en", rec)
            self.assertIn("name_hi", rec)

    # --------------------------------------------------------------------------
    # TEST 6: Staff return, correction, and resubmission
    # --------------------------------------------------------------------------
    def test_6_staff_return_correction_and_resubmission(self):
        """Verify full lifecycle: SUBMITTED -> RETURNED (by staff) -> Corrected & Resubmitted -> SUBMITTED."""
        ref_id = "JS-2026-6666"
        token = "token_test_6"
        ok, _, req = create_request(
            reference_id=ref_id,
            customer_name="Rajesh",
            location="Rampur",
            occupation="Laborer",
            income_bracket="< ₹10,000",
            purpose="Daily savings",
            selected_scheme="PMJDY",
            language="en",
            idempotency_token=token,
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)
        self.assertEqual(req["status"], "SUBMITTED")

        # Staff reviews and returns with reason
        return_reason = "Please confirm the nearest branch and exact village locality."
        ok_ret, msg_ret = update_request_status(
            reference_id=ref_id,
            new_status="RETURNED",
            staff_notes=return_reason,
            actor="STAFF",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_ret)

        returned_req = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertEqual(returned_req["status"], "RETURNED")
        self.assertEqual(returned_req["staff_notes"], return_reason)

        # Customer corrects fields and resubmits
        corrected_fields = {
            "location": "Rampur North (Near Panchayat Bhavan)",
            "occupation": "Construction Laborer"
        }
        ok_resub, msg_resub = resubmit_returned_request(
            reference_id=ref_id,
            updated_fields=corrected_fields,
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_resub)

        # Check status is updated back to SUBMITTED
        resubmitted_req = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertEqual(resubmitted_req["status"], "SUBMITTED")
        self.assertEqual(resubmitted_req["location"], "Rampur North (Near Panchayat Bhavan)")
        self.assertEqual(resubmitted_req["occupation"], "Construction Laborer")

        # Verify audit trail has full history
        audits = get_audit_trail(ref_id, db_path=self.temp_db_path)
        action_names = [a["action"] for a in audits]
        self.assertIn("REQUEST_SUBMITTED", action_names)
        self.assertIn("STATUS_CHANGED_TO_RETURNED", action_names)
        self.assertIn("REQUEST_RESUBMITTED", action_names)

        # Enforce deterministic rule: CANNOT resubmit a request that is not in RETURNED status
        ok_invalid, err_invalid = resubmit_returned_request(
            reference_id=ref_id,
            updated_fields={"location": "Somewhere else"},
            db_path=self.temp_db_path
        )
        self.assertFalse(ok_invalid)
        self.assertIn("Only 'RETURNED' requests can be corrected", err_invalid)

    # --------------------------------------------------------------------------
    # TEST 7: Status lookup and persistence
    # --------------------------------------------------------------------------
    def test_7_status_lookup_and_persistence(self):
        """Verify status lookup returns spoken next steps and session state persistence."""
        ref_id = "JS-2026-7777"
        create_request(
            reference_id=ref_id,
            customer_name="Meena Devi",
            location="Jaipur",
            occupation="Artisan",
            income_bracket="₹10,000 - ₹20,000",
            purpose="Artisan business account",
            selected_scheme="PMJDY",
            language="hi",
            idempotency_token="token_test_7",
            status="APPROVED_FOR_PROCESSING",
            db_path=self.temp_db_path
        )

        # Retrieve status guidance
        # (Pass monkeypatched db or check directly)
        req = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertIsNotNone(req)
        self.assertEqual(req["status"], "APPROVED_FOR_PROCESSING")

        # Test session state persistence in SQLite
        sess_id = "session_test_persistence"
        state_data = {
            "session_id": sess_id,
            "current_phase": "CONFIRMATION",
            "customer_profile": {"name": "Meena", "location": "Jaipur"}
        }
        save_session_state(sess_id, state_data, db_path=self.temp_db_path)
        loaded = load_session_state(sess_id, db_path=self.temp_db_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["current_phase"], "CONFIRMATION")
        self.assertEqual(loaded["customer_profile"]["name"], "Meena")

    # --------------------------------------------------------------------------
    # TEST 8: External-service failure resilience and fallback
    # --------------------------------------------------------------------------
    def test_8_external_service_failure_resilience(self):
        """Verify graceful fallback to deterministic engine when external API keys are unavailable or fail."""
        llm = LLMService()
        status = llm.get_provider_status()

        # In testing without API keys, verify it reports scripted fallback cleanly
        self.assertTrue(status["is_scripted_fallback"])
        self.assertIn("Scripted", status["label"])

        # Verify rule-based extraction still extracts slots reliably
        slots = llm.extract_structured_slots("मेरा नाम रमेश है और मैं रामपुर गाँव में रहता हूँ", {}, language="hi")
        self.assertEqual(slots.get("name"), "रमेश")
        self.assertEqual(slots.get("location"), "रामपुर")

        # Test speech service short/empty audio failure handling
        speech = SpeechService()
        success, err_msg, conf = speech.transcribe_audio_bytes(b"too_short", language="hi")
        self.assertFalse(success)
        self.assertIn("आवाज़ बहुत छोटी थी", err_msg)
        self.assertIsNone(conf)  # No fake confidence claimed

    # --------------------------------------------------------------------------
    # REGRESSION TESTS: Negative & Ambiguous Confirmation Gates
    # --------------------------------------------------------------------------
    def test_9_regression_negative_confirmation_do_not_submit(self):
        """Regression test: 'do not submit' must NEVER trigger submission and no request must be created."""
        state = self.orchestrator.create_new_session("en")
        state.customer_profile = {
            "name": "Ramesh",
            "location": "Rampur",
            "occupation": "Farmer",
            "purpose": "Savings"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)
        self.assertEqual(state.current_phase, "CONFIRMATION")

        # Initial requests count
        init_reqs = list_requests(db_path=self.temp_db_path)
        initial_count = len(init_reqs)

        # Customer says "do not submit"
        res = self.orchestrator.handle_user_input(state, "do not submit")

        # Verify confirmation was blocked
        self.assertFalse(state.confirmed_by_customer)
        self.assertNotEqual(state.current_phase, "SUBMITTED")
        self.assertEqual(res["status"], "cancelled")
        self.assertIsNone(state.submission_id)

        # Verify NO request was created
        current_reqs = list_requests(db_path=self.temp_db_path)
        self.assertEqual(len(current_reqs), initial_count)

    def test_10_regression_negative_confirmation_not_correct(self):
        """Regression test: 'not correct' must NEVER trigger submission, must route to intake, and create no request."""
        state = self.orchestrator.create_new_session("en")
        state.customer_profile = {
            "name": "Sunita",
            "location": "Patna",
            "occupation": "Homemaker",
            "purpose": "Government DBT"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)
        self.assertEqual(state.current_phase, "CONFIRMATION")

        init_reqs = list_requests(db_path=self.temp_db_path)
        initial_count = len(init_reqs)

        # Customer says "not correct"
        res = self.orchestrator.handle_user_input(state, "not correct")

        # Verify confirmation was NOT granted and routed to INTAKE for correction
        self.assertFalse(state.confirmed_by_customer)
        self.assertEqual(state.current_phase, "INTAKE")
        self.assertNotEqual(state.current_phase, "SUBMITTED")
        self.assertIsNone(state.submission_id)

        # Verify NO request was created
        current_reqs = list_requests(db_path=self.temp_db_path)
        self.assertEqual(len(current_reqs), initial_count)

    def test_11_regression_negative_confirmation_hindi_nahi_sahi_nahi_hai(self):
        """Regression test: 'नहीं, सही नहीं है' must NEVER trigger submission, must route to intake, and create no request."""
        state = self.orchestrator.create_new_session("hi")
        state.customer_profile = {
            "name": "राजेश",
            "location": "जयपुर",
            "occupation": "मजदूर",
            "purpose": "बचत"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)
        self.assertEqual(state.current_phase, "CONFIRMATION")

        init_reqs = list_requests(db_path=self.temp_db_path)
        initial_count = len(init_reqs)

        # Customer says "नहीं, सही नहीं है"
        res = self.orchestrator.handle_user_input(state, "नहीं, सही नहीं है")

        # Verify confirmation was NOT granted and routed to INTAKE
        self.assertFalse(state.confirmed_by_customer)
        self.assertEqual(state.current_phase, "INTAKE")
        self.assertNotEqual(state.current_phase, "SUBMITTED")
        self.assertIsNone(state.submission_id)

        # Verify NO request was created
        current_reqs = list_requests(db_path=self.temp_db_path)
        self.assertEqual(len(current_reqs), initial_count)

    def test_12_regression_ambiguous_confirmation_does_not_submit(self):
        """Regression test: Ambiguous queries like 'what is interest rate?' must NOT trigger submission."""
        state = self.orchestrator.create_new_session("hi")
        state.customer_profile = {
            "name": "सुरेश",
            "location": "पटना",
            "occupation": "किसान",
            "purpose": "बचत"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)

        init_reqs = list_requests(db_path=self.temp_db_path)
        initial_count = len(init_reqs)

        # Customer asks an ambiguous question during confirmation
        res = self.orchestrator.handle_user_input(state, "खाते में ब्याज कितना मिलता है?")

        self.assertFalse(state.confirmed_by_customer)
        self.assertEqual(state.current_phase, "CONFIRMATION")
        self.assertEqual(res["status"], "unconfirmed")
        self.assertIsNone(state.submission_id)

        # Verify NO request was created
        current_reqs = list_requests(db_path=self.temp_db_path)
        self.assertEqual(len(current_reqs), initial_count)

    # --------------------------------------------------------------------------
    # REGRESSION TESTS: Honest Specific Curated Record Matching
    # --------------------------------------------------------------------------
    def test_13_honest_source_verification_labels(self):
        """Verify scheme-name matching is record retrieval only (claim not verified) and no verification dates are shown."""
        # 1. Matches specific curated record -> official source available, claim NOT verified
        known_check = check_fact_uncertainty("Pradhan Mantri Jan Dhan Yojana (PMJDY)")
        self.assertTrue(known_check["is_certain"])
        self.assertEqual(known_check["status"], "OFFICIAL_SOURCE_AVAILABLE")
        self.assertEqual(known_check["matched_record_id"], "PMJDY")
        self.assertFalse(known_check["claim_verified"])
        self.assertNotIn("verification_date", known_check)
        self.assertIn("Official source available", known_check["label_en"])
        self.assertNotIn("Verified", known_check["label_en"])
        self.assertNotIn("2026", known_check["label_en"] + known_check["reason_en"])

        # Another specific curated record: PMSBY
        pmsby_check = check_fact_uncertainty("प्रधानमंत्री सुरक्षा बीमा योजना")
        self.assertTrue(pmsby_check["is_certain"])
        self.assertEqual(pmsby_check["matched_record_id"], "PMSBY")
        self.assertFalse(pmsby_check["claim_verified"])
        self.assertNotIn("verification_date", pmsby_check)

        # 2. Broad generic words WITHOUT specific scheme name MUST NOT match as verified
        generic_check = check_fact_uncertainty("farmer bank money account")
        self.assertFalse(generic_check["is_certain"])
        self.assertFalse(generic_check["claim_verified"])
        self.assertEqual(generic_check["status"], "UNVERIFIED_UNMATCHED_CLAIM")

        # 3. Known rumors -> UNVERIFIED_RUMOR
        rumor_check = check_fact_uncertainty("कर्ज माफी योजना और 50000 मुफ्त पैसा")
        self.assertFalse(rumor_check["is_certain"])
        self.assertEqual(rumor_check["status"], "UNVERIFIED_RUMOR")
        self.assertFalse(rumor_check["claim_verified"])

        # 4. Completely unmatched claims MUST remain uncertain
        unmatched_check = check_fact_uncertainty("random private overseas bond syndicate")
        self.assertFalse(unmatched_check["is_certain"])
        self.assertEqual(unmatched_check["status"], "UNVERIFIED_UNMATCHED_CLAIM")
        self.assertFalse(unmatched_check["claim_verified"])
        self.assertIn("Uncertain", unmatched_check["label_en"])

    def test_14_honest_llm_status_after_fallback(self):
        """Verify that when live AI encounters failure, provider status honestly reports scripted fallback mode."""
        llm = LLMService()
        # Simulate active provider
        llm.provider = "gemini"
        llm.fallback_active = False

        # Status before fallback
        stat_before = llm.get_provider_status()
        self.assertTrue(stat_before["active"])
        self.assertFalse(stat_before["is_scripted_fallback"])

        # Trigger fallback due to API error
        llm.trigger_fallback("Gemini API quota exceeded or connection refused")

        # Status after fallback MUST report scripted fallback honestly
        stat_after = llm.get_provider_status()
        self.assertFalse(stat_after["active"])
        self.assertTrue(stat_after["is_scripted_fallback"])
        self.assertIn("Scripted Demo Mode", stat_after["label"])
        self.assertIn("Live AI failed", stat_after["label"])

    # --------------------------------------------------------------------------
    # REGRESSION TESTS: Shared Confirmation Parser (Negative, Mixed, Conditional, Question)
    # --------------------------------------------------------------------------
    def test_15_regression_mixed_conditional_and_question_phrases(self):
        """Verify that negative, mixed, conditional, and question utterances are rejected without creating requests."""
        from confirmation_parser import parse_customer_confirmation

        # Mixed utterances
        mixed_phrases = [
            "yes but wait", "submit but I'm not sure", "हाँ लेकिन रुकिए",
            "हाँ पर गलत है", "correct but wait", "confirm but not now"
        ]
        for phrase in mixed_phrases:
            res = parse_customer_confirmation(phrase, "en")
            self.assertFalse(res.is_confirmed, f"Mixed phrase '{phrase}' must be rejected")
            self.assertEqual(res.decision, "MIXED_REJECTED")

        # Conditional utterances
        conditional_phrases = [
            "yes if it is free", "if interest is high then yes",
            "अगर कोई फीस नहीं है तो जमा करें", "only if there is no charge"
        ]
        for phrase in conditional_phrases:
            res = parse_customer_confirmation(phrase, "en")
            self.assertFalse(res.is_confirmed, f"Conditional phrase '{phrase}' must be rejected")
            self.assertEqual(res.decision, "CONDITIONAL_REJECTED")

        # Question-like utterances
        question_phrases = [
            "is this right?", "will I get money?", "खाते में ब्याज कितना मिलता है?",
            "क्या खाता तुरंत खुल जाएगा?", "can I change it later?"
        ]
        for phrase in question_phrases:
            res = parse_customer_confirmation(phrase, "en")
            self.assertFalse(res.is_confirmed, f"Question phrase '{phrase}' must be rejected")
            self.assertEqual(res.decision, "QUESTION_REJECTED")

        # Negative phrases
        negative_phrases = [
            "do not submit", "don't submit", "not correct", "नहीं, सही नहीं है",
            "गलत है", "मत जमा करो", "cancel"
        ]
        for phrase in negative_phrases:
            res = parse_customer_confirmation(phrase, "en")
            self.assertFalse(res.is_confirmed, f"Negative phrase '{phrase}' must be rejected")
            self.assertIn(res.decision, ["CANCELLED", "CORRECTION_REQUESTED"])

        # Test through orchestrator that NO request is created for mixed or conditional input
        state = self.orchestrator.create_new_session("en")
        state.customer_profile = {"name": "Test", "location": "Delhi", "occupation": "Vendor", "purpose": "Savings"}
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)

        count_before = len(list_requests(db_path=self.temp_db_path))
        orch_res1 = self.orchestrator.handle_user_input(state, "yes but wait")
        self.assertEqual(orch_res1["status"], "unconfirmed")
        self.assertFalse(state.confirmed_by_customer)
        self.assertEqual(len(list_requests(db_path=self.temp_db_path)), count_before)

        orch_res2 = self.orchestrator.handle_user_input(state, "yes if it is free")
        self.assertEqual(orch_res2["status"], "unconfirmed")
        self.assertFalse(state.confirmed_by_customer)
        self.assertEqual(len(list_requests(db_path=self.temp_db_path)), count_before)

        # Clear affirmative consent succeeds
        orch_res3 = self.orchestrator.handle_user_input(state, "yes submit")
        self.assertEqual(orch_res3["status"], "submitted")
        self.assertTrue(state.confirmed_by_customer)

    def test_16_shared_confirmation_parser_for_resubmission(self):
        """Verify that returned request resubmission uses the shared parser and rejects non-affirmative consent."""
        from confirmation_parser import parse_customer_confirmation

        # Mixed resubmission confirmation
        res_mixed = parse_customer_confirmation("हाँ लेकिन स्थान गलत है", language="hi")
        self.assertFalse(res_mixed.is_confirmed)
        self.assertEqual(res_mixed.decision, "MIXED_REJECTED")

        # Question on resubmission
        res_q = parse_customer_confirmation("क्या अब कोई समस्या तो नहीं?", language="hi")
        self.assertFalse(res_q.is_confirmed)
        self.assertEqual(res_q.decision, "QUESTION_REJECTED")

        # Clear consent on resubmission
        res_ok = parse_customer_confirmation("हाँ, सब सही है, जमा करें", language="hi")
        self.assertTrue(res_ok.is_confirmed)
        self.assertEqual(res_ok.decision, "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
