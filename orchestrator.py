"""
JanSahayak Orchestrator
Coordinates the multi-agent workflow with shared structured state:
IntakeAgent -> BankingSchemeAgent -> ApplicationAgent
Enforces deterministic validation gates, bounded clarification loops,
spoken audio generation, and SQLite state persistence.
"""

import uuid
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

from database import init_db, save_session_state, load_session_state
from agents.intake_agent import intake_agent
from agents.scheme_agent import scheme_agent
from agents.application_agent import application_agent
from speech_service import speech_service


@dataclass
class SharedSessionState:
    session_id: str
    language: str = "hi"  # "hi" or "en"
    current_phase: str = "INTAKE"  # INTAKE, SCHEME_ADVISORY, CONFIRMATION, SUBMITTED, STATUS_TRACKING
    active_agent: str = "IntakeAgent"  # IntakeAgent, BankingSchemeAgent, ApplicationAgent
    customer_profile: Dict[str, Any] = field(default_factory=lambda: {
        "name": "",
        "location": "",
        "occupation": "",
        "income_bracket": "",
        "purpose": ""
    })
    pending_slot: Optional[str] = "name"
    clarification_count: int = 0
    dialogue_history: List[Dict[str, str]] = field(default_factory=list)
    recommended_schemes: List[Dict[str, Any]] = field(default_factory=list)
    selected_scheme_id: str = "PMJDY"
    selected_scheme_name: str = "Pradhan Mantri Jan Dhan Yojana"
    document_guidance: Dict[str, Any] = field(default_factory=dict)
    readback_summary: Dict[str, Any] = field(default_factory=dict)
    confirmed_by_customer: bool = False
    submission_id: Optional[str] = None
    submission_record: Optional[Dict[str, Any]] = None
    last_spoken_text: str = ""
    last_assistant_message: str = ""
    error_message: Optional[str] = None


class JanSahayakOrchestrator:
    """Explicit orchestrator managing multi-agent handoffs and shared state."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        if db_path:
            init_db(db_path)
        else:
            init_db()

    def create_new_session(self, language: str = "hi") -> SharedSessionState:
        """Initializes a brand-new customer session with initial spoken greeting."""
        session_id = str(uuid.uuid4())[:8]
        state = SharedSessionState(session_id=session_id, language=language)

        # Initial prompt from IntakeAgent
        if language == "hi":
            welcome = (
                "नमस्ते! मैं आपका जनसहायक हूँ। "
                "मैं आपको सरकारी बैंक खाता और योजनाओं की जानकारी में मदद करूँगा। "
                "शुरू करने के लिए, कृपया अपना नाम बताएं?"
            )
        else:
            welcome = (
                "Hello! I am your JanSahayak assistant. "
                "I will help you understand government bank accounts and schemes. "
                "To get started, please tell me your name?"
            )

        state.last_assistant_message = welcome
        state.last_spoken_text = welcome
        state.dialogue_history.append({"role": "assistant", "agent": "IntakeAgent", "text": welcome})

        # Persist initial state
        self.persist_state(state)
        return state

    def persist_state(self, state: SharedSessionState) -> None:
        """Saves current state snapshot to SQLite."""
        try:
            if self.db_path:
                save_session_state(state.session_id, asdict(state), db_path=self.db_path)
            else:
                save_session_state(state.session_id, asdict(state))
        except Exception:
            pass

    def set_language(self, state: SharedSessionState, new_lang: str) -> None:
        """Changes conversational language and adapts current prompt and audio across all phases."""
        if new_lang in ["hi", "en"]:
            state.language = new_lang
            if state.current_phase == "INTAKE":
                slot = state.pending_slot or "name"
                from agents.intake_agent import SLOT_QUESTIONS
                if not any(state.customer_profile.get(s) for s in ["name", "location", "occupation", "purpose"]):
                    if new_lang == "hi":
                        welcome = (
                            "नमस्ते! मैं आपका जनसहायक हूँ। "
                            "मैं आपको सरकारी बैंक खाता और योजनाओं की जानकारी में मदद करूँगा। "
                            "शुरू करने के लिए, कृपया अपना नाम बताएं?"
                        )
                    else:
                        welcome = (
                            "Hello! I am your JanSahayak assistant. "
                            "I will help you understand government bank accounts and schemes. "
                            "To get started, please tell me your name?"
                        )
                    state.last_assistant_message = welcome
                    state.last_spoken_text = welcome
                else:
                    q = SLOT_QUESTIONS.get(slot, {}).get(new_lang, "Please answer.")
                    state.last_assistant_message = q
                    state.last_spoken_text = q

            elif state.current_phase == "SCHEME_ADVISORY":
                advice = scheme_agent.advise_options(state.customer_profile, language=new_lang)
                state.recommended_schemes = advice["recommendations"]
                for rec in state.recommended_schemes:
                    if rec["id"] == state.selected_scheme_id:
                        state.selected_scheme_name = rec["name"]
                        break
                state.last_assistant_message = advice["intro_message"]
                state.last_spoken_text = advice["intro_message"]

            elif state.current_phase == "CONFIRMATION":
                self.transition_to_confirmation(state)

            elif state.current_phase == "SUBMITTED" and state.submission_id:
                status_info = application_agent.retrieve_status_and_guidance(
                    state.submission_id, language=new_lang, db_path=self.db_path
                )
                name = state.customer_profile.get("name") or ("ग्राहक" if new_lang == "hi" else "Customer")
                rec_scheme = state.selected_scheme_name or state.selected_scheme_id
                from knowledge import get_record_by_id
                scheme_rec = get_record_by_id(state.selected_scheme_id)
                if scheme_rec:
                    rec_scheme = scheme_rec["name_hi"] if new_lang == "hi" else scheme_rec["name_en"]
                    state.selected_scheme_name = rec_scheme

                if new_lang == "hi":
                    success_display = (
                        f"🎉 **आवेदन सफलतापूर्वक दर्ज हुआ!**\n\n"
                        f"🔖 **आपकी संदर्भ संख्या**: `{state.submission_id}`\n\n"
                        f"👤 **आवेदक**: {name}\n\n"
                        f"🏦 **योजना**: {rec_scheme}\n\n"
                        f"📌 **अगला कदम**: {status_info['next_steps']}\n\n"
                        f"⚠️ *यह अनुरोध अब बैंक कर्मचारी समीक्षा पोर्टल में समीक्षा के लिए उपलब्ध है।* "
                        f"*(डेमो नोट: वास्तविक बैंक खाता केवल बैंक शाखा में आवश्यक सत्यापन के बाद ही खुलता है)*"
                    )
                else:
                    success_display = (
                        f"🎉 **Request Submitted Successfully!**\n\n"
                        f"🔖 **Your Reference ID**: `{state.submission_id}`\n\n"
                        f"👤 **Applicant**: {name}\n\n"
                        f"🏦 **Scheme**: {rec_scheme}\n\n"
                        f"📌 **Next Steps**: {status_info['next_steps']}\n\n"
                        f"⚠️ *Your request has been queued for bank staff demo review.* "
                        f"*(Demo note: Real accounts are only opened in person at the bank branch).* "
                    )
                state.last_assistant_message = success_display
                state.last_spoken_text = status_info["spoken_message"]

            self.persist_state(state)

    def handle_user_input(
        self,
        state: SharedSessionState,
        user_utterance: str,
        is_doubtful_speech: bool = False
    ) -> Dict[str, Any]:
        """
        Main orchestration entry point. Routes customer utterance to the active agent,
        manages state transitions and handoffs, and prepares spoken voice output.
        """
        user_utterance = user_utterance.strip()
        if not user_utterance:
            return {"status": "empty", "state": state}

        # Record user turn in dialogue history
        state.dialogue_history.append({
            "role": "user",
            "agent": state.active_agent,
            "text": user_utterance
        })
        state.error_message = None

        # -------------------------------------------------------------
        # PHASE 1: INTAKE PHASE (Managed by IntakeAgent)
        # -------------------------------------------------------------
        if state.current_phase == "INTAKE":
            state.active_agent = "IntakeAgent"
            intake_result = intake_agent.process_turn(
                user_utterance, state, is_doubtful_speech=is_doubtful_speech
            )

            state.customer_profile = intake_result["updated_profile"]
            state.last_assistant_message = intake_result["assistant_message"]
            state.last_spoken_text = intake_result["assistant_message"]
            state.dialogue_history.append({
                "role": "assistant",
                "agent": "IntakeAgent",
                "text": intake_result["assistant_message"]
            })

            # Check if Intake is complete -> HANDOFF to BankingSchemeAgent
            if intake_result["is_complete"]:
                # Transition to SCHEME_ADVISORY
                state.current_phase = "SCHEME_ADVISORY"
                state.active_agent = "BankingSchemeAgent"

                # BankingSchemeAgent retrieves verified records & prepares recommendations
                advice = scheme_agent.advise_options(state.customer_profile, language=state.language)
                state.recommended_schemes = advice["recommendations"]
                state.selected_scheme_id = advice["default_scheme_id"]

                # Find name of default scheme
                for rec in state.recommended_schemes:
                    if rec["id"] == state.selected_scheme_id:
                        state.selected_scheme_name = rec["name"]
                        break

                # Update prompt and spoken audio
                combined_msg = f"{intake_result['assistant_message']}\n\n---\n\n{advice['intro_message']}"
                state.last_assistant_message = combined_msg
                state.last_spoken_text = advice["intro_message"]

                state.dialogue_history.append({
                    "role": "assistant",
                    "agent": "BankingSchemeAgent",
                    "text": advice["intro_message"]
                })

            self.persist_state(state)
            return {"status": "ok", "state": state}

        # -------------------------------------------------------------
        # PHASE 2: SCHEME ADVISORY PHASE (Managed by BankingSchemeAgent)
        # -------------------------------------------------------------
        elif state.current_phase == "SCHEME_ADVISORY":
            state.active_agent = "BankingSchemeAgent"
            lowered = user_utterance.lower()

            # Check if user spoke a specific scheme choice or general consent
            if "pmsby" in lowered or "accident" in lowered or "दुर्घटना" in lowered or "सुरक्षा बीमा" in lowered:
                state.selected_scheme_id = "PMSBY"
            elif "pmjjby" in lowered or "life" in lowered or "जीवन" in lowered or "जीवन ज्योति" in lowered:
                state.selected_scheme_id = "PMJJBY"
            elif "apy" in lowered or "pension" in lowered or "पेंशन" in lowered or "अटल" in lowered:
                state.selected_scheme_id = "APY"
            elif "bsbda" in lowered or "basic" in lowered or "बुनियादी" in lowered:
                state.selected_scheme_id = "BSBDA"
            elif "regular" in lowered or "नियमित" in lowered:
                state.selected_scheme_id = "REGULAR_SAVINGS"
            elif "pmjdy" in lowered or "jan dhan" in lowered or "जन धन" in lowered or "जनधन" in lowered or "zero" in lowered or "जीरो" in lowered:
                state.selected_scheme_id = "PMJDY"
            else:
                # If user says proceed/ok/recommended, pick default recommended
                state.selected_scheme_id = state.recommended_schemes[0]["id"] if state.recommended_schemes else "PMJDY"

            # Transition to CONFIRMATION phase with KYC documents
            self.transition_to_confirmation(state)
            self.persist_state(state)
            return {"status": "ok", "state": state}

        # -------------------------------------------------------------
        # PHASE 3: CONFIRMATION PHASE (Managed by ApplicationAgent)
        # -------------------------------------------------------------
        elif state.current_phase == "CONFIRMATION":
            state.active_agent = "ApplicationAgent"
            # Use unified shared confirmation parser
            parsed_conf = application_agent.parse_confirmation(user_utterance, language=state.language)

            if parsed_conf.is_confirmed and parsed_conf.decision == "CONFIRMED":
                # Clear explicit consent granted!
                state.confirmed_by_customer = True
                return self.execute_submission(state)

            elif parsed_conf.decision == "CANCELLED":
                # Customer said "do not submit" / "cancel"
                state.confirmed_by_customer = False
                msg = parsed_conf.feedback_message_hi if state.language == "hi" else parsed_conf.feedback_message_en
                state.last_assistant_message = msg
                state.last_spoken_text = msg
                state.dialogue_history.append({"role": "assistant", "agent": "ApplicationAgent", "text": msg})
                self.persist_state(state)
                return {"status": "cancelled", "message": msg, "state": state}

            elif parsed_conf.decision == "CORRECTION_REQUESTED":
                # Customer said "not correct" / "नहीं, सही नहीं है" / "wrong"
                state.confirmed_by_customer = False
                state.current_phase = "INTAKE"
                state.active_agent = "IntakeAgent"
                state.pending_slot = "name"
                state.customer_profile["name"] = ""

                msg = parsed_conf.feedback_message_hi if state.language == "hi" else parsed_conf.feedback_message_en
                state.last_assistant_message = msg
                state.last_spoken_text = msg
                state.dialogue_history.append({"role": "assistant", "agent": "IntakeAgent", "text": msg})
                self.persist_state(state)
                return {"status": "ok", "state": state}

            else:
                # Question-like, conditional, mixed, or ambiguous input: STRICTLY REJECTED
                state.confirmed_by_customer = False
                msg = parsed_conf.feedback_message_hi if state.language == "hi" else parsed_conf.feedback_message_en
                state.last_assistant_message = msg
                state.last_spoken_text = msg
                self.persist_state(state)
                return {
                    "status": "unconfirmed",
                    "decision": parsed_conf.decision,
                    "reason": parsed_conf.reason,
                    "message": msg,
                    "state": state
                }

        self.persist_state(state)
        return {"status": "ok", "state": state}

    def select_scheme_and_proceed(self, state: SharedSessionState, scheme_id: str) -> None:
        """Triggered when customer clicks a scheme card or confirms selection."""
        state.selected_scheme_id = scheme_id
        self.transition_to_confirmation(state)
        self.persist_state(state)

    def transition_to_confirmation(self, state: SharedSessionState) -> None:
        """Prepares KYC checklist, verbal readback, and moves to CONFIRMATION phase."""
        state.current_phase = "CONFIRMATION"
        state.active_agent = "ApplicationAgent"

        # Generate physical KYC document guidance
        doc_guidance = scheme_agent.get_kyc_and_document_guidance(state.selected_scheme_id, language=state.language)
        state.document_guidance = doc_guidance

        # Generate spoken readback summary
        summary = scheme_agent.create_readback_summary(
            state.customer_profile, state.selected_scheme_id, language=state.language
        )
        state.readback_summary = summary
        state.selected_scheme_name = summary["scheme_name"]

        docs_heading = (
            "### 📄 आवश्यक दस्तावेज (बैंक शाखा ले जाने के लिए):\n"
            if state.language == "hi"
            else "### 📄 Required Documents (To bring to bank branch):\n"
        )
        combined_msg = (
            f"### 📋 {summary['scheme_name']}\n\n"
            f"{summary['display_summary']}\n\n"
            f"---\n"
            f"{docs_heading}"
            + "\n".join(doc_guidance["checklist"]) + "\n\n"
            f"{doc_guidance['notice']}\n\n"
            f"---\n"
            f"🔊 **{summary['spoken_readback']}**"
        )
        state.last_assistant_message = combined_msg
        state.last_spoken_text = summary["spoken_readback"]

        state.dialogue_history.append({
            "role": "assistant",
            "agent": "BankingSchemeAgent",
            "text": summary["spoken_readback"]
        })

    def execute_submission(self, state: SharedSessionState, db_path: Optional[str] = None) -> Dict[str, Any]:
        """Executes application submission through deterministic gates."""
        state.active_agent = "ApplicationAgent"
        target_db = db_path or self.db_path

        success, msg, record = application_agent.submit_application(
            profile=state.customer_profile,
            selected_scheme=state.selected_scheme_name or state.selected_scheme_id,
            session_id=state.session_id,
            language=state.language,
            confirmed_by_customer=state.confirmed_by_customer,
            db_path=target_db
        )

        if not success:
            state.error_message = msg
            state.last_assistant_message = f"❌ {msg}"
            state.last_spoken_text = msg
            self.persist_state(state)
            return {"status": "error", "message": msg, "state": state}

        # Submission succeeded!
        ref_id = record["reference_id"]
        state.submission_id = ref_id
        state.submission_record = record
        state.current_phase = "SUBMITTED"

        # Fetch status guidance
        status_info = application_agent.retrieve_status_and_guidance(ref_id, language=state.language, db_path=target_db)

        name = state.customer_profile.get("name") or ("ग्राहक" if state.language == "hi" else "Customer")
        if state.language == "hi":
            success_display = (
                f"🎉 **आवेदन सफलतापूर्वक दर्ज हुआ!**\n\n"
                f"🔖 **आपकी संदर्भ संख्या**: `{ref_id}`\n\n"
                f"👤 **आवेदक**: {name}\n\n"
                f"🏦 **योजना**: {state.selected_scheme_name}\n\n"
                f"📌 **अगला कदम**: {status_info['next_steps']}\n\n"
                f"⚠️ *यह अनुरोध अब बैंक कर्मचारी समीक्षा पोर्टल में समीक्षा के लिए उपलब्ध है।* "
                f"*(डेमो नोट: वास्तविक बैंक खाता केवल बैंक शाखा में आवश्यक सत्यापन के बाद ही खुलता है)*"
            )
        else:
            success_display = (
                f"🎉 **Request Submitted Successfully!**\n\n"
                f"🔖 **Your Reference ID**: `{ref_id}`\n\n"
                f"👤 **Applicant**: {name}\n\n"
                f"🏦 **Scheme**: {state.selected_scheme_name}\n\n"
                f"📌 **Next Steps**: {status_info['next_steps']}\n\n"
                f"⚠️ *Your request has been queued for bank staff demo review.* "
                f"*(Demo note: Real accounts are only opened in person at the bank branch).* "
            )

        state.last_assistant_message = success_display
        state.last_spoken_text = status_info["spoken_message"]
        state.dialogue_history.append({
            "role": "assistant",
            "agent": "ApplicationAgent",
            "text": status_info["spoken_message"]
        })

        self.persist_state(state)
        return {"status": "submitted", "reference_id": ref_id, "state": state}

    def check_status(self, reference_id: str, language: str = "hi", db_path: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves request status for customer lookup."""
        target_db = db_path or self.db_path
        return application_agent.retrieve_status_and_guidance(reference_id, language=language, db_path=target_db)


# Global singleton instance
orchestrator = JanSahayakOrchestrator()
