"""
JanSahayak Language Switching Test Suite
Verifies Hindi <-> English language switching consistency across the full customer and staff journey:
1. Intake phase (questions, quick options, prompt updates, preservation of profile data)
2. Scheme advisory phase (recommendations, plain explanations, URLs, preservation of selection)
3. Confirmation phase (readback summary, KYC checklist, explicit consent standards)
4. Application submission (success display, next steps, unique reference ID preservation)
5. Status tracking & staff review (statuses, notes, approve, return, correction, and resubmission)
6. Negative verification: No English translations in brackets in Hindi mode, no Hindi translations in English mode.
"""

import os
import re
import unittest
import tempfile

os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from database import (
    init_db,
    create_request,
    get_request_by_ref,
    list_requests,
    update_request_status,
    resubmit_returned_request
)
from knowledge import (
    get_record_by_id,
    get_document_checklist,
    match_schemes
)
from agents.intake_agent import IntakeAgent, get_quick_options
from agents.scheme_agent import BankingSchemeAgent
from agents.application_agent import ApplicationAgent
from orchestrator import JanSahayakOrchestrator, SharedSessionState
from translations import t, get_status_label, get_phase_label, STATUS_LABELS


class TestLanguageSwitching(unittest.TestCase):

    def setUp(self):
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db_file.name
        self.temp_db_file.close()
        init_db(self.temp_db_path)

        self.orchestrator = JanSahayakOrchestrator(db_path=self.temp_db_path)
        self.intake_agent = IntakeAgent()
        self.scheme_agent = BankingSchemeAgent()
        self.app_agent = ApplicationAgent()

    def tearDown(self):
        try:
            os.remove(self.temp_db_path)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # 1. Intake Phase Language Switching
    # --------------------------------------------------------------------------
    def test_intake_language_switch_preserves_state(self):
        """Test Hindi -> English -> Hindi during intake preserves entered values and adapts prompts."""
        state = self.orchestrator.create_new_session("hi")
        self.assertEqual(state.language, "hi")
        self.assertIn("नमस्ते", state.last_assistant_message)

        # Quick options in Hindi must not contain English in brackets
        hi_options = get_quick_options("occupation", "hi")
        for opt in hi_options:
            self.assertFalse(re.search(r"\([A-Za-z\s]+\)", opt), f"Hindi option '{opt}' has English in brackets")

        # Customer enters name in Hindi session
        self.orchestrator.handle_user_input(state, "मेरा नाम रमेश है")
        self.assertEqual(state.customer_profile["name"], "रमेश")
        self.assertEqual(state.pending_slot, "location")

        # Switch to English
        self.orchestrator.set_language(state, "en")
        self.assertEqual(state.language, "en")
        # Name must be preserved
        self.assertEqual(state.customer_profile["name"], "रमेश")
        self.assertEqual(state.pending_slot, "location")
        # Current prompt must be in English
        self.assertIn("village, town, or city", state.last_assistant_message)
        self.assertNotIn("गाँव", state.last_assistant_message)

        # Quick options in English must not contain Hindi
        en_options = get_quick_options("occupation", "en")
        for opt in en_options:
            self.assertFalse(re.search(r"[\u0900-\u097F]", opt), f"English option '{opt}' contains Hindi")

        # Customer enters location in English
        self.orchestrator.handle_user_input(state, "I live in Rampur")
        self.assertEqual(state.customer_profile["location"], "Rampur")
        self.assertEqual(state.pending_slot, "occupation")

        # Switch back to Hindi
        self.orchestrator.set_language(state, "hi")
        self.assertEqual(state.language, "hi")
        self.assertEqual(state.customer_profile["name"], "रमेश")
        self.assertEqual(state.customer_profile["location"], "Rampur")
        self.assertIn("काम करते हैं", state.last_assistant_message)

    # --------------------------------------------------------------------------
    # 2. Scheme Advisory Phase Language Switching
    # --------------------------------------------------------------------------
    def test_scheme_advisory_language_switching(self):
        """Test switching language in Scheme Advisory adapts scheme names and plain text."""
        state = self.orchestrator.create_new_session("hi")
        state.customer_profile = {
            "name": "सुरेश",
            "location": "पटना",
            "occupation": "किसान",
            "purpose": "बचत"
        }
        state.current_phase = "SCHEME_ADVISORY"
        state.pending_slot = None

        # Advise in Hindi
        self.orchestrator.set_language(state, "hi")
        advice_hi = state.last_assistant_message
        self.assertIn("सरकारी नियमों", advice_hi)

        # Switch to English
        self.orchestrator.set_language(state, "en")
        advice_en = state.last_assistant_message
        self.assertIn("official options", advice_en)
        self.assertNotIn("सरकारी नियमों", advice_en)

        # Verify document checklist in both languages has no brackets
        hi_docs = get_document_checklist("PMJDY", "hi")
        for doc in hi_docs:
            self.assertFalse(re.search(r"\([A-Za-z0-9\s]+\)", doc), f"Hindi doc checklist item '{doc}' has English in brackets")

        en_docs = get_document_checklist("PMJDY", "en")
        for doc in en_docs:
            self.assertFalse(re.search(r"[\u0900-\u097F]", doc), f"English doc checklist item '{doc}' has Hindi characters")

    # --------------------------------------------------------------------------
    # 3. Confirmation Phase Language Switching
    # --------------------------------------------------------------------------
    def test_confirmation_phase_language_switch_no_auto_submit(self):
        """Test switching language in confirmation updates readback and NEVER creates duplicate requests."""
        state = self.orchestrator.create_new_session("hi")
        state.customer_profile = {
            "name": "राजेश",
            "location": "जयपुर",
            "occupation": "कारीगर",
            "purpose": "सुरक्षित बचत"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)

        count_before = len(list_requests(db_path=self.temp_db_path))
        self.assertEqual(count_before, 0)

        # Summary in Hindi
        self.assertIn("नाम", state.readback_summary["display_summary"])
        self.assertIn("कृपया ध्यान से सुनें", state.last_spoken_text)

        # Switch to English
        self.orchestrator.set_language(state, "en")
        self.assertEqual(state.current_phase, "CONFIRMATION")
        self.assertIn("Name", state.readback_summary["display_summary"])
        self.assertIn("Please listen carefully", state.last_spoken_text)

        # Switching language MUST NOT create an application
        count_after_switch = len(list_requests(db_path=self.temp_db_path))
        self.assertEqual(count_after_switch, 0)

        # Switch back to Hindi
        self.orchestrator.set_language(state, "hi")
        self.assertIn("नाम", state.readback_summary["display_summary"])
        self.assertIn("कृपया ध्यान से सुनें", state.last_spoken_text)
        self.assertEqual(len(list_requests(db_path=self.temp_db_path)), 0)

    # --------------------------------------------------------------------------
    # 4. Submission & Status Tracking Across Language Switch
    # --------------------------------------------------------------------------
    def test_submission_and_tracking_language_switch(self):
        """Test submission and status guidance updates across languages without duplicating records."""
        state = self.orchestrator.create_new_session("hi")
        state.customer_profile = {
            "name": "मीना",
            "location": "लखनऊ",
            "occupation": "गृहणी",
            "purpose": "सरकारी योजना"
        }
        state.selected_scheme_id = "PMJDY"
        self.orchestrator.transition_to_confirmation(state)

        # Explicit confirmation
        res = self.orchestrator.handle_user_input(state, "हाँ, सब सही है, जमा करें")
        self.assertEqual(res["status"], "submitted")
        ref_id = state.submission_id
        self.assertIsNotNone(ref_id)

        # Verify submission message in Hindi
        self.assertIn("सफलतापूर्वक दर्ज", state.last_assistant_message)

        # Switch to English
        self.orchestrator.set_language(state, "en")
        self.assertIn("Submitted Successfully", state.last_assistant_message)
        self.assertEqual(state.submission_id, ref_id)

        # Test status check in both languages
        status_hi = self.orchestrator.check_status(ref_id, language="hi")
        self.assertIn("प्रतीक्षा में", status_hi["spoken_message"])
        self.assertEqual(get_status_label(status_hi["status"], "hi"), "प्रतीक्षा में")

        status_en = self.orchestrator.check_status(ref_id, language="en")
        self.assertIn("waiting for bank staff", status_en["spoken_message"])
        self.assertEqual(get_status_label(status_en["status"], "en"), "Under Review")

    # --------------------------------------------------------------------------
    # 5. Full Staff Review Lifecycle: Approve, Return, Correction, Resubmission
    # --------------------------------------------------------------------------
    def test_staff_lifecycle_approve_return_correction_resubmission(self):
        """Test staff return -> customer correction & resubmission -> staff approval with language switching."""
        ref_id = "JS-2026-9999"
        create_request(
            reference_id=ref_id,
            customer_name="कमला",
            location="रामपुर",
            occupation="मजदूर",
            income_bracket="< ₹10,000",
            purpose="सब्सिडी",
            selected_scheme="PMJDY",
            language="hi",
            idempotency_token="token_lifecycle_99",
            status="SUBMITTED",
            db_path=self.temp_db_path
        )

        # 1. Staff returns request with note
        staff_note = "कृपया अपना पूरा पता गाँव और वार्ड सहित बताएं"
        ok_ret, _ = update_request_status(ref_id, "RETURNED", staff_note, db_path=self.temp_db_path)
        self.assertTrue(ok_ret)

        req_after_ret = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertEqual(req_after_ret["status"], "RETURNED")
        self.assertEqual(req_after_ret["staff_notes"], staff_note)

        # Check status in English - note is preserved intact
        stat_en = self.app_agent.retrieve_status_and_guidance(ref_id, language="en", db_path=self.temp_db_path)
        self.assertIn("returned your application", stat_en["spoken_message"])
        self.assertIn(staff_note, stat_en["spoken_message"])

        # 2. Customer corrects and resubmits
        ok_resub, _ = resubmit_returned_request(
            reference_id=ref_id,
            updated_fields={"location": "रामपुर वार्ड 4"},
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_resub)

        req_after_resub = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertEqual(req_after_resub["status"], "SUBMITTED")
        self.assertEqual(req_after_resub["location"], "रामपुर वार्ड 4")

        # 3. Staff approves
        approval_note = "शाखा सत्यापन हेतु प्राथमिक स्वीकृति दी गई"
        ok_app, _ = update_request_status(ref_id, "APPROVED_FOR_PROCESSING", approval_note, db_path=self.temp_db_path)
        self.assertTrue(ok_app)

        req_final = get_request_by_ref(ref_id, db_path=self.temp_db_path)
        self.assertEqual(req_final["status"], "APPROVED_FOR_PROCESSING")
        self.assertEqual(get_status_label(req_final["status"], "hi"), "शाखा सत्यापन हेतु स्वीकृत")
        self.assertEqual(get_status_label(req_final["status"], "en"), "Approved for Branch Verification")

    # --------------------------------------------------------------------------
    # 6. Negative Check: Clean Language Separation
    # --------------------------------------------------------------------------
    def test_negative_verification_no_mixed_parentheses(self):
        """Verify UI translations dictionary has no English in brackets in Hindi and no Hindi in English."""
        from translations import UI_TEXT, STATUS_LABELS

        for key, trans in UI_TEXT.items():
            hi_val = trans.get("hi", "")
            en_val = trans.get("en", "")

            # Check that Hindi text doesn't contain English in brackets (e.g. '(Name)', '(Track)')
            bracket_english = re.findall(r"\([A-Za-z\s]+\)", hi_val)
            self.assertEqual(
                len(bracket_english), 0,
                f"Key '{key}' Hindi value contains English brackets: {bracket_english}"
            )

            # Check that English text doesn't contain Devanagari characters
            devanagari_chars = re.findall(r"[\u0900-\u097F]", en_val)
            self.assertEqual(
                len(devanagari_chars), 0,
                f"Key '{key}' English value contains Devanagari characters: {devanagari_chars}"
            )

        for status_key, trans in STATUS_LABELS.items():
            hi_label = trans.get("hi", "")
            en_label = trans.get("en", "")

            self.assertFalse(
                re.search(r"\([A-Za-z\s]+\)", hi_label),
                f"Status '{status_key}' Hindi label contains English brackets: '{hi_label}'"
            )
            self.assertFalse(
                re.search(r"[\u0900-\u097F]", en_label),
                f"Status '{status_key}' English label contains Devanagari: '{en_label}'"
            )


if __name__ == "__main__":
    unittest.main()
