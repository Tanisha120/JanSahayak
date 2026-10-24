"""
JanSahayak Intake Agent
Responsible for conversing with the customer, extracting structured customer profile slots,
asking exactly one necessary follow-up question at a time, remembering confirmed answers,
handling doubtful speech corrections, and enforcing bounded clarification loops.
"""

import re
from typing import Dict, Any, Tuple, Optional
from llm_service import llm_service


REQUIRED_SLOTS = ["name", "location", "occupation", "purpose"]

SLOT_QUESTIONS = {
    "name": {
        "hi": "नमस्ते! जनसहायक में आपका स्वागत है। कृपया अपना नाम बताएं?",
        "en": "Hello! Welcome to JanSahayak. What is your name, please?",
        "quick_options_hi": ["रमेश", "सुनीता", "राजेश", "मीना"],
        "quick_options_en": ["Ramesh", "Sunita", "Rajesh", "Meena"],
        "quick_options": ["रमेश", "सुनीता", "राजेश", "मीना"]
    },
    "location": {
        "hi": "आप किस गाँव, कस्बे या शहर में रहते हैं?",
        "en": "Which village, town, or city do you live in?",
        "quick_options_hi": ["रामपुर गाँव", "पटना", "जयपुर", "लखनऊ"],
        "quick_options_en": ["Rampur Village", "Patna", "Jaipur", "Lucknow"],
        "quick_options": ["रामपुर गाँव", "पटना", "जयपुर", "लखनऊ"]
    },
    "occupation": {
        "hi": "आप क्या काम करते हैं? (जैसे: खेती, मजदूरी, दुकान, या घर का काम)",
        "en": "What work do you do? (e.g. farming, daily wage work, shopkeeping, or homemaker)",
        "quick_options_hi": [
            "किसान",
            "मजदूर / दैनिक वेतनभोगी",
            "दुकानदार",
            "गृहणी"
        ],
        "quick_options_en": [
            "Farmer",
            "Daily Wage Earner",
            "Shopkeeper",
            "Homemaker"
        ],
        "quick_options": [
            "किसान",
            "मजदूर / दैनिक वेतनभोगी",
            "दुकानदार",
            "गृहणी"
        ]
    },
    "purpose": {
        "hi": "आप बैंक खाता किस काम के लिए खोलना चाहते हैं?",
        "en": "What is the main purpose of opening this bank account?",
        "quick_options_hi": [
            "सरकारी योजना व सब्सिडी",
            "सुरक्षित बचत",
            "बुढ़ापे की पेंशन",
            "परिवार का बीमा"
        ],
        "quick_options_en": [
            "Government Subsidies & DBT",
            "Safe Savings",
            "Old Age Pension",
            "Life / Accident Insurance"
        ],
        "quick_options": [
            "सरकारी योजना व सब्सिडी",
            "सुरक्षित बचत",
            "बुढ़ापे की पेंशन",
            "परिवार का बीमा"
        ]
    }
}


def get_quick_options(slot: str, language: str = "hi"):
    
    q_info = SLOT_QUESTIONS.get(slot, {})
    if language == "en":
        return q_info.get("quick_options_en", q_info.get("quick_options", []))
    return q_info.get("quick_options_hi", q_info.get("quick_options", []))


def _norm_text(text: str) -> str:
    """Case/whitespace-insensitive form used for comparisons."""
    return " ".join(str(text or "").split()).casefold()


def _is_quick_option(slot: str, text: str, language: str = "hi") -> bool:
    """
    True if `text` exactly matches a quick-option button of `slot` in the CURRENT language.
    Language-pure on purpose: an English phrase typed while Hindi is active (or vice versa)
    still goes through normal extraction so it is normalised to the active language's label.
    """
    wanted = _norm_text(text)
    return bool(wanted) and any(_norm_text(opt) == wanted for opt in get_quick_options(slot, language=language))


class DuplicateInputGuard:
    """
    Protects against the same typed/clicked input being processed twice (Streamlit reruns,
    double clicks) WITHOUT blocking legitimate repeats.

    
    """

    def __init__(self):
        self._last = None  # (scope, state_version_after_processing)

    @staticmethod
    def _scope(state: Any, text: str):
        return (
            getattr(state, "session_id", None),
            getattr(state, "current_phase", None),
            getattr(state, "pending_slot", None),
            _norm_text(text),
        )

    @staticmethod
    def _state_version(state: Any):
        profile = getattr(state, "customer_profile", None) or {}
        return (
            getattr(state, "language", None),
            getattr(state, "clarification_count", 0),
            getattr(state, "selected_scheme_id", None),
            bool(getattr(state, "confirmed_by_customer", False)),
            getattr(state, "submission_id", None),
            tuple(sorted((str(k), str(v or "")) for k, v in profile.items())),
        )

    def is_duplicate(self, state: Any, text: str) -> bool:
        if self._last is None or not _norm_text(text):
            return False
        last_scope, last_version = self._last
        return last_scope == self._scope(state, text) and last_version == self._state_version(state)

    def submit(self, state: Any, text: str, handler) -> Tuple[bool, Any]:
        """
        Run `handler(state, text)` unless this is an exact duplicate.
        Returns (processed, handler_result). The guard is only armed after the handler
        returns, so a failed/raising submission never blocks the customer's retry.
        """
        if self.is_duplicate(state, text):
            return False, None
        scope = self._scope(state, text)  # scope BEFORE processing (phase/pending field being answered)
        result = handler(state, text)
        self._last = (scope, self._state_version(state))  # state AFTER processing
        return True, result

    def reset(self) -> None:
        self._last = None


class IntakeAgent:
    """Agent responsible for understanding customer needs and extracting profile slots."""

    def __init__(self):
        self.max_clarifications_per_slot = 3

    def get_missing_slot(self, profile: Dict[str, Any]) -> Optional[str]:
        """Identifies the next missing required slot in strict sequence."""
        for slot in REQUIRED_SLOTS:
            val = profile.get(slot)
            if not val or not str(val).strip():
                return slot
        return None

    def is_intake_complete(self, profile: Dict[str, Any]) -> bool:
        """Deterministic check whether all mandatory intake slots have been filled."""
        return self.get_missing_slot(profile) is None

    def handle_correction(self, state: Any, correction_text: str) -> Tuple[str, str]:
        """
        Handles speech transcription doubts or user-initiated corrections.
        Clears the uncertain slot and reprompts politely.
        """
        lang = getattr(state, "language", "hi")
        # Reset current pending slot or ask which detail needs changing
        pending = getattr(state, "pending_slot", "name") or "name"
        state.customer_profile[pending] = ""
        state.clarification_count = 0

        if lang == "hi":
            msg = f"कोई बात नहीं! कृपया अपनी सही जानकारी फिर से बोलें: {SLOT_QUESTIONS[pending]['hi']}"
        else:
            msg = f"No problem! Please speak your correct detail again: {SLOT_QUESTIONS[pending]['en']}"

        return msg, pending

    def process_turn(
        self,
        user_utterance: str,
        state: Any,
        is_doubtful_speech: bool = False
    ) -> Dict[str, Any]:
        """
        Processes a single conversational turn from the customer.
        Returns a structured dictionary with:
        - assistant_message: plain language prompt
        - current_slot: the slot being targeted
        - is_complete: bool
        - updated_profile: dict
        - quick_options: list of suggested answers
        """
        lang = getattr(state, "language", "hi")
        profile = getattr(state, "customer_profile", {})

        # If flagged as doubtful speech from audio recognition
        if is_doubtful_speech:
            msg, pending = self.handle_correction(state, user_utterance)
            return {
                "assistant_message": msg,
                "current_slot": pending,
                "is_complete": False,
                "updated_profile": profile,
                "quick_options": get_quick_options(pending, language=lang)
            }

        # Check if user says "wrong" or "change" in Hindi or English (using word boundaries, avoid substring matching like 'योजना' matching 'ना')
        lowered = user_utterance.lower().strip()
        neg_pattern = r"(?:\s|^)(?:गलत|सुधारना|बदलो|नहीं|गलत\s*है|wrong|change|incorrect|redo|not\s*correct)(?:\s|[.,!?]|$)"
        if re.search(neg_pattern, lowered) and any(profile.get(s) for s in REQUIRED_SLOTS):
            msg, pending = self.handle_correction(state, user_utterance)
            return {
                "assistant_message": msg,
                "current_slot": pending,
                "is_complete": False,
                "updated_profile": profile,
                "quick_options": get_quick_options(pending, language=lang)
            }

        # Fast path: a quick-option button for the pending slot (in the active language)
        # is assigned directly, skipping the LLM call entirely. Corrections were already
        # handled above, so spoken/typed "wrong"/"change" still win.
        pending_slot = getattr(state, "pending_slot", None) or self.get_missing_slot(profile)
        if pending_slot and _is_quick_option(pending_slot, user_utterance, language=lang):
            profile[pending_slot] = user_utterance.strip()
        else:
            # Extract structured slots from utterance (may call the LLM)
            extracted = llm_service.extract_structured_slots(user_utterance, profile, language=lang)
            for k, v in extracted.items():
                if v and str(v).strip():
                    profile[k] = v

        # If user directly answered the pending slot specifically
        if pending_slot and not profile.get(pending_slot) and user_utterance.strip():
            # If the user spoke a short direct answer to the pending question
            clean_ans = user_utterance.strip()
            # If not a generic sentence, treat as answer for pending slot
            if len(clean_ans.split()) <= 4:
                profile[pending_slot] = clean_ans

        # Re-check what slot is missing now
        next_slot = self.get_missing_slot(profile)

        # Handle bounded clarification loop
        if next_slot == pending_slot:
            state.clarification_count = getattr(state, "clarification_count", 0) + 1
        else:
            state.clarification_count = 0

        # Update state pending slot
        state.pending_slot = next_slot

        if next_slot is None:
            # All required slots filled!
            name = profile.get("name", "ग्राहक")
            loc = profile.get("location", "")
            occ = profile.get("occupation", "")
            purp = profile.get("purpose", "")

            if lang == "hi":
                completion_msg = (
                    f"धन्यवाद {name} जी! हमने आपकी जानकारी दर्ज कर ली है:\n"
                    f"• निवास: {loc}\n"
                    f"• काम: {occ}\n"
                    f"• उद्देश्य: {purp}\n\n"
                    f"अब हमारे बैंकिंग विशेषज्ञ आपके लिए उपयुक्त सरकारी बैंक खाते और योजनाओं की जानकारी तैयार कर रहे हैं।"
                )
            else:
                completion_msg = (
                    f"Thank you, {name}! We have recorded your details:\n"
                    f"• Location: {loc}\n"
                    f"• Work: {occ}\n"
                    f"• Purpose: {purp}\n\n"
                    f"Our banking advisor is now matching the most suitable government accounts and schemes for you."
                )

            return {
                "assistant_message": completion_msg,
                "current_slot": None,
                "is_complete": True,
                "updated_profile": profile,
                "quick_options": []
            }

        # Ask next single question
        q_info = SLOT_QUESTIONS.get(next_slot, {})
        prompt = q_info.get(lang, q_info.get("en", "Please provide more details."))
        quick_opts = get_quick_options(next_slot, language=lang)

        # If user reached bounded clarification threshold, give extra helpful prompt
        if state.clarification_count >= self.max_clarifications_per_slot:
            if lang == "hi":
                prompt = f"कृपया नीचे दिए गए बटनों में से एक चुन लें, या साफ आवाज़ में बताएं: {prompt}"
            else:
                prompt = f"Please select one of the buttons below or speak clearly: {prompt}"

        return {
            "assistant_message": prompt,
            "current_slot": next_slot,
            "is_complete": False,
            "updated_profile": profile,
            "quick_options": quick_opts
        }


# Global singleton instance
intake_agent = IntakeAgent()
