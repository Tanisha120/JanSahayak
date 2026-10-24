"""
JanSahayak Application Agent
Enforces deterministic validation gates:
1. Completeness verification
2. Explicit customer confirmation gate
3. Idempotency and duplicate submission prevention
4. Unique reference ID generation (JS-2026-XXXX)
5. SQLite persistence, status tracking, and returned request resubmission
"""

import random
from typing import Dict, Any, Tuple, Optional, List
from database import (
    compute_idempotency_token,
    create_request,
    get_request_by_ref,
    resubmit_returned_request,
    get_audit_trail
)
from confirmation_parser import parse_customer_confirmation, ConfirmationResult


class ApplicationAgent:
    """Agent responsible for deterministic validation, submission, and status lifecycle."""

    def parse_confirmation(self, utterance: str, language: str = "hi") -> ConfirmationResult:
        """Shared confirmation parser ensuring only clear, explicit consent is accepted."""
        return parse_customer_confirmation(utterance, language=language)

    def generate_reference_id(self) -> str:
        """Generates a human-friendly unique reference code e.g. JS-2026-7842."""
        num = random.randint(1000, 9999)
        return f"JS-2026-{num}"

    def check_completeness(self, profile: Dict[str, Any], selected_scheme: str) -> Tuple[bool, List[str]]:
        """
        Deterministic check: ensures all required synthetic customer fields and scheme are present.
        Returns: (is_complete: bool, missing_fields: list)
        """
        missing = []
        for field in ["name", "location", "occupation", "purpose"]:
            val = profile.get(field)
            if not val or not str(val).strip():
                missing.append(field)

        if not selected_scheme or not selected_scheme.strip():
            missing.append("selected_scheme")

        return len(missing) == 0, missing

    def submit_application(
        self,
        profile: Dict[str, Any],
        selected_scheme: str,
        session_id: str,
        language: str = "hi",
        confirmed_by_customer: bool = False,
        db_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Submits the request after passing through strict deterministic validation gates.
        """
        # Gate 1: Completeness check
        is_complete, missing = self.check_completeness(profile, selected_scheme)
        if not is_complete:
            err = f"Submission rejected: Missing required fields: {', '.join(missing)}"
            return False, err, None

        # Gate 2: Explicit Confirmation Gate
        if not confirmed_by_customer:
            err = "Submission blocked: Explicit customer confirmation is mandatory before submitting."
            return False, err, None

        # Gate 3: Idempotency / Duplicate Prevention Gate
        name = profile.get("name", "").strip()
        loc = profile.get("location", "").strip()
        occ = profile.get("occupation", "").strip()
        purp = profile.get("purpose", "").strip()
        token = compute_idempotency_token(name, loc, occ, purp, session_id)

        # Generate unique reference code
        ref_id = self.generate_reference_id()

        # Database creation with duplicate protection
        kwargs = {
            "reference_id": ref_id,
            "customer_name": name,
            "location": loc,
            "occupation": occ,
            "income_bracket": profile.get("income_bracket", "उपलब्ध नहीं"),
            "purpose": purp,
            "selected_scheme": selected_scheme,
            "language": language,
            "idempotency_token": token,
            "status": "SUBMITTED"
        }
        if db_path:
            kwargs["db_path"] = db_path
        success, msg, record = create_request(**kwargs)

        return success, msg, record

    def retrieve_status_and_guidance(self, reference_id: str, language: str = "hi", db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves request status from SQLite and generates spoken next steps in Hindi or English.
        """
        clean_ref = reference_id.strip().upper()
        record = get_request_by_ref(clean_ref, db_path=db_path) if db_path else get_request_by_ref(clean_ref)

        if not record:
            msg_hi = f"संदर्भ संख्या '{clean_ref}' का कोई आवेदन नहीं मिला। कृपया सही संख्या जांचें।"
            msg_en = f"No application found with reference ID '{clean_ref}'. Please verify the ID."
            return {
                "found": False,
                "spoken_message": msg_hi if language == "hi" else msg_en,
                "record": None,
                "audit_trail": []
            }

        status = record["status"]
        name = record["customer_name"]
        scheme = record["selected_scheme"]
        notes = record.get("staff_notes", "")
        audit = get_audit_trail(clean_ref)

        # Generate spoken next steps based on status
        if status == "SUBMITTED":
            spoken_hi = (
                f"नमस्ते {name} जी! आपका आवेदन (क्रमांक {clean_ref}) सफलतापूर्वक दर्ज है और बैंक कर्मचारियों की "
                f"समीक्षा के लिए प्रतीक्षा में है। आपको जल्द ही सूचना दी जाएगी।"
            )
            spoken_en = (
                f"Hello {name}! Your application (ID {clean_ref}) is successfully recorded and waiting for bank staff review. "
                f"You will be updated soon."
            )
            next_step_hi = "कृपया अपनी संदर्भ संख्या लिखकर या याद रखें। बैंक अधिकारी जल्द ही इसकी प्राथमिक जांच करेंगे।"
            next_step_en = "Please note down your reference number. Bank staff will conduct the initial review shortly."

        elif status == "APPROVED_FOR_PROCESSING":
            spoken_hi = (
                f"शुभ समाचार {name} जी! आपका अनुरोध बैंक समीक्षा में प्राथमिक रूप से स्वीकृत हो चुका है। "
                f"अब आप अपने आवश्यक दस्तावेज लेकर अपनी नजदीकी बैंक शाखा में जाएं। "
                f"ध्यान दें: यह एक प्रारंभिक सहायता स्वीकृति है, असली खाता बैंक शाखा में व्यक्तिगत रूप से खुलेगा।"
            )
            spoken_en = (
                f"Good news {name}! Your request has been approved for processing. "
                f"Please take your physical documents to your nearest bank branch. "
                f"Note: This is a demo pre-approval; the actual bank account will be opened in person at the branch."
            )
            next_step_hi = "दस्तावेज चेकलिस्ट के अनुसार कागजात लेकर बैंक शाखा संपर्क करें।"
            next_step_en = "Visit your bank branch with documents according to the checklist."

        elif status == "RETURNED":
            spoken_hi = (
                f"{name} जी, आपके आवेदन में बैंक कर्मचारी ने अतिरिक्त जानकारी या सुधार मांगा है। "
                f"कारण: '{notes or 'विवरण अधूरा है'}'. आप अभी नीचे अपनी जानकारी सुधार कर दोबारा जमा कर सकते हैं।"
            )
            spoken_en = (
                f"{name}, bank staff returned your application requesting corrections. "
                f"Reason: '{notes or 'Incomplete details'}'. You can correct and resubmit below."
            )
            next_step_hi = f"सुधार का कारण: {notes}। कृपया विवरण सुधार कर दोबारा पुष्टि करें।"
            next_step_en = f"Reason for return: {notes}. Please correct the details and re-confirm."

        elif status == "REJECTED":
            spoken_hi = (
                f"{name} जी, आपका अनुरोध स्वीकृत नहीं किया जा सका। कारण: '{notes or 'नियमों के अनुकूल नहीं'}'. "
                f"अधिक जानकारी के लिए कृपया नजदीकी बैंक शाखा के सहायता केंद्र से संपर्क करें।"
            )
            spoken_en = (
                f"{name}, your request could not be approved. Reason: '{notes or 'Does not meet criteria'}'. "
                f"Please consult your local bank branch helpdesk for further options."
            )
            next_step_hi = f"अस्वीकृति कारण: {notes}।"
            next_step_en = f"Rejection reason: {notes}."

        else:
            spoken_hi = f"आवेदन क्रमांक {clean_ref} की वर्तमान स्थिति: {status}।"
            spoken_en = f"Current status of application {clean_ref}: {status}."
            next_step_hi = "बैंक शाखा से संपर्क करें।"
            next_step_en = "Contact your bank branch."

        return {
            "found": True,
            "status": status,
            "record": record,
            "spoken_message": spoken_hi if language == "hi" else spoken_en,
            "next_steps": next_step_hi if language == "hi" else next_step_en,
            "audit_trail": audit
        }

    def resubmit_application(
        self,
        reference_id: str,
        updated_fields: Dict[str, Any],
        confirmed: bool = False
    ) -> Tuple[bool, str]:
        """
        Resubmits a returned request after explicit customer confirmation.
        """
        if not confirmed:
            return False, "Cannot resubmit without explicit customer confirmation."

        return resubmit_returned_request(reference_id, updated_fields)


# Global singleton instance
application_agent = ApplicationAgent()
