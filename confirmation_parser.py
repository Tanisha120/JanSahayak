"""
JanSahayak Centralized Shared Confirmation Parser
Enforces strict consent standards for BOTH initial application submission and returned-request resubmission:
- Accepts ONLY clear, explicit, unequivocal affirmative consent.
- Strictly rejects:
  * Negative utterances ("do not submit", "not correct", "नहीं, सही नहीं है", "wrong", "cancel")
  * Mixed utterances ("yes but wait", "submit but I'm not sure", "हाँ लेकिन गलत है")
  * Conditional utterances ("if interest is high then yes", "only if it is free", "अगर कोई फीस नहीं है")
  * Question-like utterances ("is this right?", "will I get money?", "खाते में ब्याज कितना मिलता है?")
  * Ambiguous / hesitant utterances ("maybe", "thinking", "tell me more", "शायद")
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfirmationResult:
    is_confirmed: bool
    decision: str  # 'CONFIRMED', 'CANCELLED', 'CORRECTION_REQUESTED', 'QUESTION_REJECTED', 'CONDITIONAL_REJECTED', 'MIXED_REJECTED', 'AMBIGUOUS_REJECTED'
    reason: str
    feedback_message_hi: str
    feedback_message_en: str


def parse_customer_confirmation(utterance: str, language: str = "hi") -> ConfirmationResult:
    """
    Unified, single confirmation parser for initial submission and resubmission.
    Accepts ONLY clear, explicit consent; rejects negative, mixed, conditional, and question-like utterances.
    """
    text = (utterance or "").strip().lower()

    if not text:
        return ConfirmationResult(
            is_confirmed=False,
            decision="EMPTY",
            reason="No input provided.",
            feedback_message_hi="कोई उत्तर प्राप्त नहीं हुआ। कृपया स्पष्ट बताएं।",
            feedback_message_en="No input received. Please speak or type clearly."
        )

    # --------------------------------------------------------------------------
    # 1. Question-Like Utterances Check
    # --------------------------------------------------------------------------
    has_question_mark = "?" in text or "؟" in text
    question_patterns = [
        r"(?:\b|^)(?:what|why|how|when|where|which|who|is\s*it|is\s*this|can\s*i|could\s*i|will\s*i|should\s*i|do\s*i|are\s*these)(?:\b|\s)",
        r"(?:क्या|क्यों|कैसे|कब|कहाँ|किस|कितना|कितने|कितनी|मिलेगा|होगी|सकते\s*हैं)(?:\b|\s)"
    ]
    is_question = has_question_mark or any(re.search(pat, text) for pat in question_patterns)

    if is_question:
        return ConfirmationResult(
            is_confirmed=False,
            decision="QUESTION_REJECTED",
            reason="Question-like utterance rejected. Confirmation requires clear affirmative consent, not a question.",
            feedback_message_hi=(
                "यह एक प्रश्न प्रतीत होता है। आपका आवेदन अभी जमा नहीं हुआ है। "
                "यदि आप संतुष्ट हैं और जमा करना चाहते हैं, तो स्पष्ट रूप से 'हाँ, जमा करें' कहें, "
                "या सुधार के लिए 'विवरण बदलें' बोलें।"
            ),
            feedback_message_en=(
                "This appears to be a question. Your request has NOT been submitted. "
                "If you are satisfied and wish to submit, please clearly say 'Yes, submit', "
                "or say 'Change details' to correct something."
            )
        )

    # --------------------------------------------------------------------------
    # 2. Conditional Utterances Check
    # --------------------------------------------------------------------------
    conditional_patterns = [
        r"(?:\b|^)(?:if|only\s*if|even\s*if|provided\s*that|as\s*long\s*as|in\s*case|assuming|unless)(?:\b|\s)",
        r"(?:\b|^)(?:अगर|यदि|हो\s*सके\s*तो|बशर्ते|जब\s*तक|तभी|शर्त)(?:\b|\s)"
    ]
    is_conditional = any(re.search(pat, text) for pat in conditional_patterns)

    if is_conditional:
        return ConfirmationResult(
            is_confirmed=False,
            decision="CONDITIONAL_REJECTED",
            reason="Conditional consent rejected. Unconditional explicit confirmation is required before submission.",
            feedback_message_hi=(
                "सशर्त सहमति स्वीकार नहीं की जा सकती। आपका आवेदन जमा नहीं हुआ है। "
                "कृपया बिना शर्त स्पष्ट पुष्टि दें: जमा करने के लिए 'हाँ, जमा करें' कहें, "
                "या सुधार के लिए 'विवरण बदलें' कहें।"
            ),
            feedback_message_en=(
                "Conditional consent cannot be accepted. Your request has NOT been submitted. "
                "Please provide clear, unconditional consent: say 'Yes, submit' to confirm, "
                "or 'Change details' to edit."
            )
        )

    # --------------------------------------------------------------------------
    # 3. Mixed / Conflicting Utterances Check
    # (e.g. contains an affirmative word paired with contrast, hesitation, or doubt)
    # --------------------------------------------------------------------------
    contrast_patterns = [
        r"(?:\b|^)(?:but|however|except|although|though|maybe|not\s*sure|wait|hold\s*on|hold|thinking)(?:\b|\s)",
        r"(?:\b|^)(?:लेकिन|परंतु|मगर|पर|किंतु|शायद|रुकिए|रुक|सोच\s*रहा|पक्का\s*नहीं)(?:\b|\s)"
    ]
    has_contrast = any(re.search(pat, text) for pat in contrast_patterns)
    has_affirmative_fragment = any(w in text for w in ["yes", "submit", "confirm", "proceed", "correct", "हाँ", "जमा", "सही", "पुष्टि"])

    if has_contrast and has_affirmative_fragment:
        return ConfirmationResult(
            is_confirmed=False,
            decision="MIXED_REJECTED",
            reason="Mixed or conflicting utterance detected. Consent must be clear and unequivocal.",
            feedback_message_hi=(
                "मिश्रित या असमंजस भरा उत्तर मिला। आपका आवेदन जमा नहीं किया गया है। "
                "जमा करने के लिए केवल 'हाँ, जमा करें' कहें, या सुधार के लिए 'विवरण बदलें' बोलें।"
            ),
            feedback_message_en=(
                "Mixed or conflicting answer detected. Your request has NOT been submitted. "
                "Please clearly say 'Yes, submit' to confirm, or 'Change details' to correct."
            )
        )

    # --------------------------------------------------------------------------
    # 4. Explicit Negative / Cancellation Commands
    # (e.g. "do not submit", "don't submit", "cancel", "मत जमा करो")
    # --------------------------------------------------------------------------
    cancel_patterns = [
        r"(?:do\s*not\s*submit|don'?t\s*submit|never\s*submit|not\s*submit|stop\s*submission|cancel\s*submission|cancel|abort|halt|stop)",
        r"(?:मत\s*जमा\s*करो|जमा\s*मत\s*करना|जमा\s*मत\s*करो|नहीं\s*जमा\s*करना|रद्द\s*करें|कैंसिल|मत\s*करो|रोकें|रुकें)"
    ]
    if any(re.search(pat, text) for pat in cancel_patterns):
        return ConfirmationResult(
            is_confirmed=False,
            decision="CANCELLED",
            reason="Customer issued explicit cancellation or command not to submit.",
            feedback_message_hi="आवेदन जमा नहीं किया गया है। आपकी मांग पर प्रक्रिया रोक दी गई है। कोई अनुरोध दर्ज नहीं हुआ है।",
            feedback_message_en="Request has NOT been submitted. Process halted per your instruction. No application was created."
        )

    # --------------------------------------------------------------------------
    # 5. Explicit Negative / Correction Phrases
    # (e.g. "not correct", "isn't correct", "wrong", "नहीं, सही नहीं है", "गलत है")
    # --------------------------------------------------------------------------
    correction_patterns = [
        r"(?:not\s*correct|isn'?t\s*correct|is\s*not\s*correct|not\s*right|wrong|incorrect|change\s*details|change|modify|edit|redo|not\s*yet|no|nope)",
        r"(?:नहीं\s*,\s*सही\s*नहीं\s*है|सही\s*नहीं\s*है|गलत\s*है|गलत|सुधारना\s*है|बदलो|सुधार|गलती\s*है|नहीं|ना)"
    ]
    has_negation_word = bool(re.search(r"(?:\b|^)(?:not|don'?t|never|no|stop|cancel|wrong|नहीं|ना|मत|गलत|रद्द)(?:\b|\s|[.,!?]|$)", text))

    if any(re.search(pat, text) for pat in correction_patterns) or has_negation_word:
        return ConfirmationResult(
            is_confirmed=False,
            decision="CORRECTION_REQUESTED",
            reason="Customer indicated details are not correct or requested correction.",
            feedback_message_hi="कोई बात नहीं! चलिए विवरण दोबारा ठीक करते हैं। कृपया अपना सही नाम बताएं?",
            feedback_message_en="No problem! Let us correct your details. What is your correct name?"
        )

    # --------------------------------------------------------------------------
    # 6. Clear, Explicit Affirmative Consent ONLY
    # Must be unambiguous, direct consent without any negation, condition, or question.
    # --------------------------------------------------------------------------
    # Strip punctuation for clean token matching (e.g. "हाँ, सब सही है, जमा करें" -> "हाँ सब सही है जमा करें")
    norm_text = re.sub(r"[,;:.!\-]", " ", text)
    norm_text = re.sub(r"\s+", " ", norm_text).strip()

    affirmative_patterns = [
        r"^(?:yes|confirm|proceed|submit|please\s*submit|submit\s*now|yes\s*submit|yes\s*submit\s*now|yes\s*confirm|all\s*correct|everything\s*is\s*correct|looks\s*good|approved|i\s*confirm|yes\s*please\s*submit|yes\s*that\s*is\s*correct\s*submit|yes\s*all\s*correct|yes\s*everything\s*is\s*correct\s*submit|yes\s*correct|yes\s*it\s*is\s*correct\s*submit)$",
        r"^(?:हाँ|हाँ\s*सही\s*है|पुष्टि\s*करता\s*हूँ|पुष्टि\s*करें|जमा\s*करें|अब\s*जमा\s*करें|हाँ\s*जमा\s*करें|हाँ\s*अब\s*जमा\s*करें|हाँ\s*जमा\s*कर\s*दीजिए|सब\s*सही\s*है|सब\s*सही\s*है\s*जमा\s*करें|हाँ\s*सही\s*है\s*जमा\s*करें|हाँ\s*सही\s*है\s*अब\s*जमा\s*करें|हाँ\s*सब\s*सही\s*है\s*जमा\s*करें|हाँ\s*सब\s*सही\s*है|हाँ\s*सब\s*सही\s*है\s*जमा\s*कर\s*दीजिए|ठीक\s*है\s*जमा\s*करें|बिल्कुल\s*सही|मंजूर\s*है)$"
    ]
    if any(re.search(pat, norm_text) for pat in affirmative_patterns):
        return ConfirmationResult(
            is_confirmed=True,
            decision="CONFIRMED",
            reason="Clear, explicit, unconditional consent confirmed.",
            feedback_message_hi="सहमति प्राप्त। आवेदन जमा किया जा रहा है...",
            feedback_message_en="Explicit consent confirmed. Submitting application..."
        )

    # --------------------------------------------------------------------------
    # 7. Fallback: Ambiguous / Hesitant / Unrecognized Utterance
    # (e.g. "maybe", "thinking", "tell me more", "how are you", random words)
    # --------------------------------------------------------------------------
    return ConfirmationResult(
        is_confirmed=False,
        decision="AMBIGUOUS_REJECTED",
        reason="Ambiguous or unrecognized utterance rejected. Explicit consent is required.",
        feedback_message_hi=(
            "स्पष्ट सहमति नहीं मिली। आपका आवेदन अभी जमा नहीं हुआ है। "
            "यदि विवरण सही हैं तो स्पष्ट रूप से 'हाँ, जमा करें' कहें, "
            "या सुधार के लिए 'विवरण बदलें' बोलें।"
        ),
        feedback_message_en=(
            "Clear consent was not detected. Your request has NOT been submitted. "
            "If details are correct, clearly say 'Yes, submit', "
            "or say 'Change details' to correct something."
        )
    )
