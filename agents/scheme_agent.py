"""
JanSahayak Banking and Scheme Agent
Retrieves official banking and government scheme records by scheme name
(record retrieval only; this does not verify a customer's claim),
generates accessible plain-language explanations in Hindi or English,
cites published official sources (no verification dates are claimed),
flags unverified rumors as uncertain, generates safe KYC checklists,
and crafts verbal readback summaries for customer confirmation.
"""

from typing import Dict, Any, List
from knowledge import (
    match_schemes,
    check_fact_uncertainty,
    get_document_checklist,
    get_record_by_id
)


class BankingSchemeAgent:
    """Agent responsible for banking guidance, scheme matching, and KYC checklists."""

    def advise_options(self, profile: Dict[str, Any], language: str = "hi") -> Dict[str, Any]:
        """
        Retrieves recommended accounts and schemes tailored to customer profile.
        Attaches official source citations and URLs. Matching is record retrieval only.
        """
        occupation = profile.get("occupation", "")
        purpose = profile.get("purpose", "")
        income = profile.get("income_bracket", "")

        # Check for uncertain rumors in customer purpose or input
        uncertainty_check = check_fact_uncertainty(f"{purpose} {occupation}")

        # Retrieve official records (lookup by scheme name; not claim verification)
        matched_records = match_schemes(occupation=occupation, purpose=purpose, income_bracket=income, language=language)

        # Structure recommendations with plain language and citations
        recommendations = []
        for rec in matched_records:
            # Skip pure KYC guidance record from scheme options list (it will be shown in documents)
            if rec["category"] == "KYC_GUIDANCE":
                continue

            name = rec["name_hi"] if language == "hi" else rec["name_en"]
            explanation = rec["plain_explanation_hi"] if language == "hi" else rec["plain_explanation_en"]
            benefits = rec["benefits_hi"] if language == "hi" else rec["benefits_en"]
            eligibility = rec["eligibility_hi"] if language == "hi" else rec["eligibility_en"]

            recommendations.append({
                "id": rec["id"],
                "name": name,
                "category": rec["category"],
                "plain_explanation": explanation,
                "benefits": benefits,
                "eligibility": eligibility,
                "min_balance": f"₹{rec['min_balance_inr']}",
                "official_source": rec["official_source_title"],
                "official_url": rec["official_source_url"]
            })

        # Default recommended scheme is the first one (typically PMJDY or BSBDA)
        default_scheme = recommendations[0]["id"] if recommendations else "PMJDY"

        # Generate verbal overview message with honest uncertainty disclosure
        uncertainty_prefix = ""
        if not uncertainty_check["is_certain"]:
            if language == "hi":
                uncertainty_prefix = (
                    f"{uncertainty_check.get('label_hi', '⚠️ असत्यापित जानकारी')}: "
                    f"{uncertainty_check.get('reason_hi', '')} "
                    f"{uncertainty_check.get('recommendation_hi', '')}\n\n---\n\n"
                )
            else:
                uncertainty_prefix = (
                    f"{uncertainty_check.get('label_en', '⚠️ Unverified Information')}: "
                    f"{uncertainty_check.get('reason_en', '')} "
                    f"{uncertainty_check.get('recommendation_en', '')}\n\n---\n\n"
                )

        if language == "hi":
            intro_msg = (
                f"{uncertainty_prefix}"
                f"आपके काम और आवश्यकता के अनुसार, हमने सरकारी नियमों के तहत ये सबसे उपयोगी विकल्प चुने हैं:\n"
                f"1. **{recommendations[0]['name']}**: {recommendations[0]['plain_explanation']}\n\n"
                f"आप नीचे दिए गए विकल्पों में से अपना पसंदीदा खाता या योजना चुन सकते हैं।"
            )
        else:
            intro_msg = (
                f"{uncertainty_prefix}"
                f"Based on your profile and needs, we have selected these official options:\n"
                f"1. **{recommendations[0]['name']}**: {recommendations[0]['plain_explanation']}\n\n"
                f"You can choose your preferred option below."
            )

        return {
            "intro_message": intro_msg,
            "recommendations": recommendations,
            "default_scheme_id": default_scheme,
            "uncertainty_info": uncertainty_check
        }

    def get_kyc_and_document_guidance(self, scheme_id: str, language: str = "hi") -> Dict[str, Any]:
        """
        Provides physical document checklist for branch visit.
        Reiterates that NO real documents are collected online.
        """
        checklist = get_document_checklist(scheme_id, language=language)
        kyc_record = get_record_by_id("KYC_GUIDELINES")

        notice_hi = (
            "⚠️ **सुरक्षा सूचना**: जनसहायक ऐप में कोई भी असली पहचान पत्र, आधार नंबर, या फोटो अपलोड नहीं करना है। "
            "आपको ये सामान्य कागजात केवल अपनी नजदीकी बैंक शाखा में ले जाने हैं।"
        )
        notice_en = (
            "⚠️ **Safety Notice**: Do NOT upload any real identity documents, Aadhaar numbers, or photos into JanSahayak. "
            "You only need to take these physical documents to your nearest bank branch."
        )

        return {
            "checklist": checklist,
            "notice": notice_hi if language == "hi" else notice_en,
            "official_source": kyc_record["official_source_title"] if kyc_record else "Reserve Bank of India",
            "official_url": kyc_record["official_source_url"] if kyc_record else "https://rbi.org.in/"
        }

    def create_readback_summary(
        self,
        profile: Dict[str, Any],
        selected_scheme_id: str,
        language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Creates spoken summary and readback for explicit customer confirmation.
        """
        scheme = get_record_by_id(selected_scheme_id) or get_record_by_id("PMJDY")
        scheme_name = scheme["name_hi"] if language == "hi" else scheme["name_en"]

        name = profile.get("name") or ("ग्राहक" if language == "hi" else "Customer")
        loc = profile.get("location") or ("गाँव" if language == "hi" else "Town")
        occ = profile.get("occupation") or ("दैनिक कार्य" if language == "hi" else "Daily Work")
        purp = profile.get("purpose") or ("बचत" if language == "hi" else "Savings")

        if language == "hi":
            readback_text = (
                f"कृपया ध्यान से सुनें। आपका नाम {name} है, आप {loc} के रहने वाले हैं, "
                f"आपका कार्य {occ} है, और आप '{scheme_name}' खाता खोलने के लिए आवेदन तैयार कर रहे हैं। "
                f"क्या यह जानकारी पूरी तरह सही है? यदि हाँ, तो 'हाँ, सब सही है' बोलें या हरा बटन दबाएं।"
            )
            short_summary = (
                f"👤 **नाम**: {name}\n\n"
                f"📍 **स्थान**: {loc}\n\n"
                f"💼 **पेशा**: {occ}\n\n"
                f"🎯 **उद्देश्य**: {purp}\n\n"
                f"🏦 **चुनी गई योजना**: {scheme_name}\n\n"
                f"📜 **आधिकारिक स्रोत**: {scheme['official_source_title']}"
            )
        else:
            readback_text = (
                f"Please listen carefully. Your name is {name}, you live in {loc}, "
                f"your work is {occ}, and you are preparing a request for '{scheme_name}'. "
                f"Is this information completely correct? If yes, please say 'Yes, submit' or click the green button."
            )
            short_summary = (
                f"👤 **Name**: {name}\n\n"
                f"📍 **Location**: {loc}\n\n"
                f"💼 **Occupation**: {occ}\n\n"
                f"🎯 **Purpose**: {purp}\n\n"
                f"🏦 **Selected Scheme**: {scheme_name}\n\n"
                f"📜 **Official Source**: {scheme['official_source_title']}"
            )

        return {
            "spoken_readback": readback_text,
            "display_summary": short_summary,
            "scheme_name": scheme_name
        }


# Global singleton instance
scheme_agent = BankingSchemeAgent()
