"""
JanSahayak Centralized UI Translations Dictionary
Provides consistent, separate Hindi and English translations for all system-generated interface text.
- When Hindi is selected: clean Hindi without English in brackets.
- When English is selected: clean English without Hindi in brackets.
Zero external LLM calls used for interface translations.
"""

from typing import Dict, Any

UI_TEXT: Dict[str, Dict[str, str]] = {
    # --------------------------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------------------------
    "app_title": {
        "hi": "जनसहायक",
        "en": "JanSahayak"
    },
    "app_caption": {
        "hi": "आवाज़ से बैंकिंग सहायता",
        "en": "Voice Banking Assistance"
    },
    "select_portal": {
        "hi": "पोर्टल चुनें:",
        "en": "Select Portal:"
    },
    "portal_customer": {
        "hi": "🗣️ ग्राहक सेवा",
        "en": "🗣️ Customer Portal"
    },
    "portal_staff": {
        "hi": "👥 बैंक कर्मचारी समीक्षा",
        "en": "👥 Staff Review Demo"
    },
    "select_language": {
        "hi": "भाषा चुनें",
        "en": "Select Language"
    },
    "system_status": {
        "hi": "सिस्टम स्थिति",
        "en": "System Status"
    },
    "active_agent": {
        "hi": "सक्रिय एजेंट:",
        "en": "Active Agent:"
    },
    "current_phase": {
        "hi": "वर्तमान चरण:",
        "en": "Current Phase:"
    },
    "session_controls": {
        "hi": "सत्र नियंत्रण",
        "en": "Session Controls"
    },
    "new_session": {
        "hi": "नया आवेदन शुरू करें",
        "en": "Start New Application"
    },
    "sidebar_safety_disclaimer": {
        "hi": "<small>🔒 **सुरक्षा सूचना**: यह ऐप केवल सहायता और फॉर्म तैयारी के लिए है। कोई वास्तविक वित्तीय लेनदेन या असली दस्तावेज यहाँ नहीं लिए जाते।</small>",
        "en": "<small>🔒 **Safety Notice**: This app is for guidance and form preparation only. No actual financial transactions or real documents are collected here.</small>"
    },

    # --------------------------------------------------------------------------
    # Customer Portal Header & Steps
    # --------------------------------------------------------------------------
    "customer_title": {
        "hi": "जनसहायक",
        "en": "JanSahayak"
    },
    "customer_subtitle": {
        "hi": "अपनी बोलचाल की भाषा में सरकारी बैंक खाता और योजनाएं समझें",
        "en": "Voice-Guided Assistance for Government Banking & Schemes"
    },
    "track_status_btn": {
        "hi": "🔍 स्थिति देखें",
        "en": "🔍 Check Status"
    },
    "step_details": {
        "hi": "1. विवरण",
        "en": "1. Your Details"
    },
    "step_schemes": {
        "hi": "2. योजनाएं",
        "en": "2. Select Scheme"
    },
    "step_review": {
        "hi": "3. समीक्षा व पुष्टि",
        "en": "3. Review & Confirm"
    },
    "step_track": {
        "hi": "4. आवेदन स्थिति",
        "en": "4. Track Request"
    },

    # --------------------------------------------------------------------------
    # Sub-view A: Intake Phase
    # --------------------------------------------------------------------------
    "intake_heading": {
        "hi": "बोलकर या लिखकर उत्तर दें",
        "en": "Respond by Voice or Text"
    },
    "microphone": {
        "hi": "माइक्रोफोन",
        "en": "Microphone"
    },
    "press_mic_speak": {
        "hi": "माइक दबाकर अपनी आवाज़ में बोलें:",
        "en": "Press mic and speak in your voice:"
    },
    "transcribing": {
        "hi": "आवाज़ समझी जा रही है...",
        "en": "Transcribing audio..."
    },
    "heard_prefix": {
        "hi": "🗣️ हमने सुना:",
        "en": "🗣️ Heard:"
    },
    "text_fallback": {
        "hi": "टेक्स्ट विकल्प",
        "en": "Text Input"
    },
    "type_here": {
        "hi": "यहाँ लिखें:",
        "en": "Type here:"
    },
    "type_placeholder": {
        "hi": "जैसे: मेरा नाम रमेश है, मैं रामपुर में रहता हूँ...",
        "en": "e.g. My name is Ramesh, I live in Rampur..."
    },
    "send_btn": {
        "hi": "आगे बढ़ें",
        "en": "Send"
    },
    "quick_options_heading": {
        "hi": "या सीधे नीचे से चुनें:",
        "en": "Or select a quick option below:"
    },
    "recorded_profile_heading": {
        "hi": "अब तक दर्ज विवरण",
        "en": "Recorded Profile So Far"
    },
    "metric_name": {
        "hi": "👤 नाम",
        "en": "👤 Name"
    },
    "metric_loc": {
        "hi": "📍 स्थान",
        "en": "📍 Location"
    },
    "metric_occ": {
        "hi": "💼 पेशा",
        "en": "💼 Occupation"
    },
    "metric_purp": {
        "hi": "🎯 उद्देश्य",
        "en": "🎯 Purpose"
    },

    # --------------------------------------------------------------------------
    # Sub-view B: Scheme Advisory Phase
    # --------------------------------------------------------------------------
    "schemes_heading": {
        "hi": "आपके लिए अनुशंसित सरकारी विकल्प",
        "en": "Recommended Banking Options for You"
    },
    "schemes_caption": {
        "hi": "भारत सरकार एवं भारतीय रिज़र्व बैंक के आधिकारिक स्रोतों से जुड़े रिकॉर्ड",
        "en": "Official records from Government of India and Reserve Bank of India sources"
    },
    "voice_scheme_heading": {
        "hi": "बोलकर योजना चुनें",
        "en": "Speak to Select Scheme"
    },
    "voice_scheme_mic": {
        "hi": "माइक दबाकर अपनी पसंद बोलें (जैसे: जन धन खाता, सुरक्षा बीमा, पेंशन):",
        "en": "Press mic and speak your choice (e.g. Jan Dhan account, accident insurance, pension):"
    },
    "voice_scheme_tip": {
        "hi": "💡 **आवाज़ में बोल सकते हैं:** 'मुझे जन धन खाता चाहिए', 'सुरक्षा बीमा', 'जीवन ज्योति', या 'पेंशन'।",
        "en": "💡 **You can say:** 'I want Jan Dhan account', 'Accident insurance', 'Life insurance', or 'Pension'."
    },
    "min_balance": {
        "hi": "न्यूनतम बैलेंस:",
        "en": "Minimum Balance:"
    },
    "source_available": {
        "hi": "आधिकारिक स्रोत उपलब्ध:",
        "en": "Official source available:"
    },
    "select_scheme_btn": {
        "hi": "✅ यह योजना चुनें",
        "en": "✅ Select This Option"
    },
    "go_back_details": {
        "hi": "⬅️ विवरण बदलें",
        "en": "⬅️ Go Back & Change Details"
    },

    # --------------------------------------------------------------------------
    # Sub-view C: Confirmation & KYC Checklist Phase
    # --------------------------------------------------------------------------
    "conf_heading": {
        "hi": "आवेदन समीक्षा व आवश्यक दस्तावेज",
        "en": "Application Review & Required Documents"
    },
    "summary_heading": {
        "hi": "आपके आवेदन का सारांश",
        "en": "Application Summary"
    },
    "voice_conf_heading": {
        "hi": "आवाज़ द्वारा पुष्टि",
        "en": "Voice Confirmation"
    },
    "voice_conf_info": {
        "hi": "कृपया ध्यान से सुनें। यदि जानकारी सही है, तो 'हाँ, सब सही है' बोलें या नीचे दिए गए हरे बटन को दबाएं।",
        "en": "Please listen carefully. If details are correct, say 'Yes, submit' or click the green button below."
    },
    "voice_conf_mic": {
        "hi": "पुष्टि के लिए बोलें:",
        "en": "Speak to confirm:"
    },
    "checklist_heading": {
        "hi": "बैंक शाखा ले जाने के लिए आवश्यक दस्तावेज",
        "en": "Physical Documents for Bank Branch"
    },
    "ready_question": {
        "hi": "क्या आप यह आवेदन पत्र जमा करना चाहते हैं?",
        "en": "Do you want to submit this request?"
    },
    "confirm_submit_btn": {
        "hi": "✅ हाँ, सब सही है — जमा करें",
        "en": "✅ Yes, Everything Is Correct — Submit"
    },
    "correct_details_btn": {
        "hi": "🔄 नहीं, विवरण सुधारें",
        "en": "🔄 No, Correct Details"
    },

    # --------------------------------------------------------------------------
    # Sub-view D: Submitted Request Phase
    # --------------------------------------------------------------------------
    "submitted_heading": {
        "hi": "आपका आवेदन सफलतापूर्वक दर्ज हो गया है!",
        "en": "Your Application Has Been Successfully Submitted!"
    },
    "reference_badge_label": {
        "hi": "संदर्भ संख्या",
        "en": "Reference ID"
    },
    "app_details_heading": {
        "hi": "आवेदन विवरण",
        "en": "Application Details"
    },
    "field_name_label": {
        "hi": "नाम",
        "en": "Name"
    },
    "field_loc_label": {
        "hi": "स्थान",
        "en": "Location"
    },
    "field_occ_label": {
        "hi": "पेशा",
        "en": "Occupation"
    },
    "field_scheme_label": {
        "hi": "चुनी गई योजना",
        "en": "Selected Scheme"
    },
    "field_status_label": {
        "hi": "वर्तमान स्थिति",
        "en": "Current Status"
    },
    "status_under_review": {
        "hi": "प्रतीक्षा में",
        "en": "Submitted / Queued for Review"
    },
    "next_steps_heading": {
        "hi": "आपके लिए अगला कदम",
        "en": "Next Steps for You"
    },
    "next_steps_body": {
        "hi": "1. अपनी संदर्भ संख्या लिखकर रख लें।\n2. बैंक कर्मचारी समीक्षा पोर्टल में आपके विवरण की प्राथमिक जांच करेंगे।\n3. स्वीकृति मिलने पर आवश्यक कागजात लेकर अपनी नजदीकी बैंक शाखा जाएं।",
        "en": "1. Note down your Reference ID.\n2. Bank staff will conduct initial review in the staff portal.\n3. Upon approval, visit your nearest bank branch with the required documents."
    },
    "check_status_btn": {
        "hi": "🔍 इस आवेदन की स्थिति देखें",
        "en": "🔍 Track This Request"
    },
    "new_app_btn": {
        "hi": "➕ नया आवेदन शुरू करें",
        "en": "➕ Start New Application"
    },

    # --------------------------------------------------------------------------
    # Sub-view E: Status Tracking & Resubmission Phase
    # --------------------------------------------------------------------------
    "tracking_heading": {
        "hi": "आवेदन की स्थिति जांचें",
        "en": "Track Application Status"
    },
    "enter_ref": {
        "hi": "संदर्भ संख्या दर्ज करें:",
        "en": "Enter Reference ID:"
    },
    "search_btn": {
        "hi": "जांचें",
        "en": "Search"
    },
    "staff_notes_next_steps": {
        "hi": "बैंक कर्मचारी टिप्पणी व अगला कदम:",
        "en": "Staff Notes & Next Steps:"
    },
    "staff_note_prefix": {
        "hi": "बैंक टिप्पणी:",
        "en": "Staff Note:"
    },
    "app_date": {
        "hi": "आवेदन तिथि:",
        "en": "Application Date:"
    },
    "correct_resubmit_heading": {
        "hi": "आवेदन में सुधार करें और दोबारा जमा करें",
        "en": "Correct Details and Resubmit"
    },
    "return_reason_heading": {
        "hi": "बैंक कर्मचारी का कारण / टिप्पणी:",
        "en": "Bank Staff Reason / Note:"
    },
    "voice_corr_heading": {
        "hi": "बोलकर सुधार बताएं",
        "en": "Speak Your Correction"
    },
    "voice_corr_mic": {
        "hi": "माइक दबाकर सुधार बोलें (जैसे: मेरा सही स्थान रामपुर उत्तर है):",
        "en": "Press mic to speak correction (e.g. My correct location is Rampur North):"
    },
    "voice_corr_tip": {
        "hi": "💡 **आवाज़ में बोलें:** 'मेरा स्थान रामपुर उत्तर है' या 'मेरा काम बढ़ई है'। सिस्टम आपकी आवाज़ से विवरण स्वतः भर देगा।",
        "en": "💡 **Speak:** 'My location is Rampur North' or 'My work is carpenter'. The system will automatically update the fields."
    },
    "input_name_label": {
        "hi": "नाम:",
        "en": "Name:"
    },
    "input_loc_label": {
        "hi": "स्थान:",
        "en": "Location:"
    },
    "input_occ_label": {
        "hi": "पेशा:",
        "en": "Occupation:"
    },
    "input_scheme_label": {
        "hi": "योजना:",
        "en": "Scheme:"
    },
    "voice_resubmit_heading": {
        "hi": "आवाज़ द्वारा पुनः पुष्टि",
        "en": "Voice Confirmation for Resubmission"
    },
    "voice_resubmit_mic": {
        "hi": "माइक दबाकर पुष्टि बोलें ('हाँ, सब सही है, जमा करें'):",
        "en": "Press mic to confirm ('Yes, submit'):"
    },
    "voice_consent_received": {
        "hi": "🗣️ स्पष्ट सहमति प्राप्त:",
        "en": "🗣️ Explicit consent confirmed:"
    },
    "confirm_checkbox": {
        "hi": "✅ मैं पुष्टि करता हूँ कि ये सुधारे गए विवरण सही हैं",
        "en": "✅ I confirm that these corrected details are accurate"
    },
    "resubmit_btn": {
        "hi": "📤 सुधारे गए विवरण जमा करें",
        "en": "📤 Resubmit Corrected Details"
    },
    "resubmit_success": {
        "hi": "आवेदन सफलतापूर्वक सुधारा गया और पुनः बैंक समीक्षा के लिए भेज दिया गया!",
        "en": "Application successfully updated and resubmitted for bank staff review!"
    },
    "resubmit_check_error": {
        "hi": "कृपया सबमिट करने से पहले पुष्टि बॉक्स पर टिक करें या आवाज़ से पुष्टि करें।",
        "en": "Please check the confirmation box or speak your confirmation before submitting."
    },
    "audit_trail_expander": {
        "hi": "पूर्ण ऑडिट इतिहास",
        "en": "Complete Audit Trail"
    },
    "back_to_home": {
        "hi": "⬅️ मुख्य पृष्ठ पर वापस जाएं",
        "en": "⬅️ Back to Home"
    },

    # --------------------------------------------------------------------------
    # Staff Portal
    # --------------------------------------------------------------------------
    "staff_title": {
        "hi": "बैंक कर्मचारी समीक्षा पोर्टल",
        "en": "Bank Staff Review Portal"
    },
    "staff_subtitle": {
        "hi": "जनसहायक सहायता अनुरोधों की प्राथमिक जांच एवं सत्यापन",
        "en": "Initial Screening & Verification for JanSahayak Requests"
    },
    "staff_disclaimer": {
        "hi": "⚠️ **डेमो अस्वीकरण**: यह बैंक कर्मचारियों के लिए एक प्रदर्शन (डेमो) इंटरफ़ेस है। यहाँ दी गई स्वीकृति केवल शाखा दस्तावेज़ सत्यापन के लिए अग्रसारण है; यहाँ स्वीकृति से कोई वास्तविक बैंक खाता नहीं खुलता। वास्तविक खाता केवल बैंक शाखा में शारीरिक सत्यापन के बाद ही खुलता है।",
        "en": "⚠️ **DEMO DISCLAIMER**: This is a demonstration interface for bank staff. Approval here is solely a referral for branch document verification; approval here does not open a real bank account. The actual bank account is opened only after in-person verification at the bank branch."
    },
    "filter_by_status": {
        "hi": "स्थिति के अनुसार फ़िल्टर करें:",
        "en": "Filter by Status:"
    },
    "refresh_list": {
        "hi": "🔄 सूची रीफ़्रेश करें",
        "en": "🔄 Refresh List"
    },
    "total_requests": {
        "hi": "कुल अनुरोध मिले:",
        "en": "Total Requests Found:"
    },
    "no_requests": {
        "hi": "इस फ़िल्टर के तहत कोई अनुरोध उपलब्ध नहीं है।",
        "en": "No requests found under this filter."
    },
    "staff_profile_heading": {
        "hi": "ग्राहक प्रोफ़ाइल",
        "en": "Customer Profile"
    },
    "staff_profile_name": {
        "hi": "• **नाम:**",
        "en": "• **Name:**"
    },
    "staff_profile_loc": {
        "hi": "• **गाँव/स्थान:**",
        "en": "• **Village/Location:**"
    },
    "staff_profile_occ": {
        "hi": "• **पेशा:**",
        "en": "• **Occupation:**"
    },
    "staff_profile_income": {
        "hi": "• **आय वर्ग:**",
        "en": "• **Income Bracket:**"
    },
    "staff_profile_purpose": {
        "hi": "• **उद्देश्य:**",
        "en": "• **Purpose:**"
    },
    "staff_profile_scheme": {
        "hi": "• **अनुरोधित योजना:**",
        "en": "• **Requested Scheme:**"
    },
    "staff_profile_lang": {
        "hi": "• **सत्र भाषा:**",
        "en": "• **Session Language:**"
    },
    "staff_profile_time": {
        "hi": "• **अनुरोध समय:**",
        "en": "• **Submission Time:**"
    },
    "staff_profile_notes": {
        "hi": "• **मौजूदा बैंक टिप्पणी:**",
        "en": "• **Existing Staff Note:**"
    },
    "staff_action_heading": {
        "hi": "कर्मचारी कार्रवाई",
        "en": "Staff Action"
    },
    "staff_action_caption": {
        "hi": "कारण या निर्देश दर्ज करें:",
        "en": "Enter reason or instructions:"
    },
    "staff_notes_label": {
        "hi": "कर्मचारी टिप्पणी:",
        "en": "Staff Notes / Reason:"
    },
    "staff_notes_placeholder": {
        "hi": "उदा. दस्तावेज़ सत्यापन हेतु शाखा में आमंत्रित / पता अस्पष्ट है...",
        "en": "e.g. Please bring original voter ID to branch..."
    },
    "btn_approve": {
        "hi": "🟢 स्वीकृत",
        "en": "🟢 Approve"
    },
    "btn_return": {
        "hi": "🟡 लौटाएं",
        "en": "🟡 Return"
    },
    "btn_reject": {
        "hi": "🔴 अस्वीकृत",
        "en": "🔴 Reject"
    },
    "audit_trail_heading": {
        "hi": "अपरिवर्तनीय ऑडिट इतिहास",
        "en": "Immutable Audit Trail"
    },
    "approve_default_note": {
        "hi": "शाखा दस्तावेज़ सत्यापन हेतु स्वीकृत",
        "en": "Approved for branch document verification"
    },
    "return_reason_required": {
        "hi": "लौटाने के लिए कारण दर्ज करना आवश्यक है!",
        "en": "Reason is required to return a request!"
    },
    "reject_reason_required": {
        "hi": "अस्वीकृति के लिए कारण दर्ज करना आवश्यक है!",
        "en": "Reason is required to reject a request!"
    },
    "approved_msg": {
        "hi": "को स्वीकृत किया गया!",
        "en": "approved for processing!"
    },
    "returned_msg": {
        "hi": "को सुधार हेतु वापस भेजा गया!",
        "en": "returned for correction!"
    },
    "rejected_msg": {
        "hi": "को अस्वीकृत किया गया!",
        "en": "has been rejected!"
    }
}

STATUS_LABELS: Dict[str, Dict[str, str]] = {
    "SUBMITTED": {
        "hi": "प्रतीक्षा में",
        "en": "Under Review"
    },
    "APPROVED_FOR_PROCESSING": {
        "hi": "शाखा सत्यापन हेतु स्वीकृत",
        "en": "Approved for Branch Verification"
    },
    "RETURNED": {
        "hi": "सुधार हेतु वापस",
        "en": "Returned for Correction"
    },
    "REJECTED": {
        "hi": "अस्वीकृत",
        "en": "Rejected"
    },
    "ALL": {
        "hi": "सभी",
        "en": "All"
    }
}

PHASE_LABELS: Dict[str, Dict[str, str]] = {
    "INTAKE": {
        "hi": "विवरण संकलन",
        "en": "Intake"
    },
    "SCHEME_ADVISORY": {
        "hi": "योजना परामर्श",
        "en": "Scheme Advisory"
    },
    "CONFIRMATION": {
        "hi": "समीक्षा व पुष्टि",
        "en": "Review & Confirmation"
    },
    "SUBMITTED": {
        "hi": "जमा हो चुका",
        "en": "Submitted"
    },
    "STATUS_TRACKING": {
        "hi": "स्थिति ट्रैकिंग",
        "en": "Status Tracking"
    }
}

STATUS_BADGES: Dict[str, str] = {
    "SUBMITTED": "🔵",
    "APPROVED_FOR_PROCESSING": "🟢",
    "RETURNED": "🟡",
    "REJECTED": "🔴"
}


def t(key: str, lang: str = "hi") -> str:
    """Retrieve UI text for given key and language. Falls back to Hindi if key missing in English, or key itself."""
    entry = UI_TEXT.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("hi", key))


def get_status_label(status_code: str, lang: str = "hi") -> str:
    """Translate internal status code to display label without bilingual brackets."""
    entry = STATUS_LABELS.get(status_code.upper())
    if entry:
        return entry.get(lang, status_code)
    return status_code


def get_status_badge(status_code: str) -> str:
    """Get emoji badge for status code."""
    return STATUS_BADGES.get(status_code.upper(), "▫️")


def get_phase_label(phase_code: str, lang: str = "hi") -> str:
    """Translate internal workflow phase code to display label."""
    entry = PHASE_LABELS.get(phase_code.upper())
    if entry:
        return entry.get(lang, phase_code)
    return phase_code
