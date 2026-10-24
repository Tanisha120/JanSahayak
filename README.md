# JanSahayak (जनसहायक)
**Accessible Voice-First Banking Guidance & Request Preparation for Low-Literacy Customers**

JanSahayak is a working hackathon application engineered specifically for citizens who cannot read or write. It bridges the financial inclusion gap in India by providing spoken Hindi and English interaction, official-source-linked government banking/scheme education, structured request preparation with strict confirmation safeguards, and a demo staff review portal.

---

## 🌟 Key Capabilities

1. **Voice-First Accessible Interface**:
   - Spoken guidance in **Hindi (हिन्दी)** and **English** with text fallback.
   - High-contrast visual controls, clear icons, and quick-tap choice chips.
   - Every system prompt and explanation has high-quality audio playback (`gTTS`) so low-literacy customers do not need to read the screen.
2. **Three Cooperating Autonomous Agents**:
   - **Intake Agent**: Conducts conversational intake, asks exactly one follow-up question at a time, remembers confirmed slots, handles doubtful speech corrections, and manages bounded clarification loops.
   - **Banking & Scheme Agent**: Matches scheme names to 7 curated government banking and social security records (PMJDY, BSBDA, Regular Savings, PMSBY, PMJJBY, APY, KYC guidance), explains benefits in plain language, cites official URLs, and flags unverified rumors as uncertain. Matching is record retrieval only; it does not verify a customer's claim.
   - **Application Agent**: Enforces strict deterministic validation gates (completeness check, explicit customer confirmation gate, duplicate prevention via idempotency hashing), generates unique reference numbers (`JS-2026-XXXX`), records immutable audit trails, and manages the status lifecycle.
3. **Demo Bank Staff Review Portal**:
   - Separate demo portal for simulated branch review.
   - Allows bank staff to **Approve for Branch Processing**, **Return for Correction** (with mandatory reason), or **Reject** (with reason).
   - Customers can look up status, listen to spoken next steps, correct returned requests, re-confirm, and resubmit.
4. **Safety & Compliance Safeguards**:
   - Synthetic customer information only.
   - Strictly does NOT collect or upload OTPs, PINs, passwords, Aadhaar numbers, or real identity documents.
   - Generates physical KYC checklist for the branch visit; no real bank account is created online.

---

## 🏛️ Curated Official Knowledge Base

All banking and scheme guidance is grounded in official Government of India and Reserve Bank of India publications:

| Scheme / Record | Category | Official Source | Key Benefit |
| :--- | :--- | :--- | :--- |
| **PMJDY** | Zero-Balance Account | Dept of Financial Services, Ministry of Finance (`pmjdy.gov.in`) | Zero balance, RuPay debit card, ₹2 Lakh accident cover, DBT subsidies |
| **BSBDA** | Basic Savings Account | Reserve Bank of India Master Circular (`rbi.org.in`) | RBI-mandated fee-free zero-balance account, 4 free withdrawals/month |
| **Regular Savings** | Standard Account | Reserve Bank of India Guidelines (`rbi.org.in`) | Cheque book, netbanking, higher transaction limits (AMB applies) |
| **PMSBY** | Accident Insurance | Dept of Financial Services (`financialservices.gov.in`) | ₹2 Lakh accidental death/disability cover for just ₹20/year |
| **PMJJBY** | Life Insurance | Dept of Financial Services (`financialservices.gov.in`) | ₹2 Lakh life cover (any cause) for ₹436/year |
| **APY** | Pension Scheme | PFRDA & NSDL (`pfrda.org.in`) | Guaranteed ₹1,000–₹5,000 monthly pension after age 60 for unorganized workers |
| **KYC Guidance** | Official KYC Rules | RBI Master Direction - KYC Direction, 2016 (`rbi.org.in`) | OVD list + 'Small Account' facility (open with just a photo & thumb impression) |

*Uncertainty Guard*: Non-official rumors (e.g. loan waivers, free handouts) are flagged as uncertain and customers are directed to branch staff.

---

## 🚀 Quick Setup & Run on Windows

### Prerequisites
- Python 3.10+ (Tested on Python 3.14 on Windows)
- Modern web browser (Chrome, Edge, or Firefox)

### 1. Clone / Open Project
```powershell
git clone https://github.com/Tanisha120/JanSahayak.git
cd JanSahayak
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Optional: Configure LLM API Keys
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Add your Google Gemini or OpenAI API key inside `.env`:
```env
GEMINI_API_KEY=AIzaSy...
LLM_MODEL=gemini-2.5-flash
```
> **Note**: An API key is **optional**. If no API key is provided, JanSahayak runs seamlessly in an explicitly labeled **Scripted Demo Mode** with deterministic intelligence, ensuring hackathon reviewers can test 100% of the workflows without needing credentials!

### 4. Run the Application
```powershell
streamlit run app.py
```
Streamlit will launch in your browser at `http://localhost:8501`.

---

## 🧪 Automated Test Suite

JanSahayak includes a comprehensive automated test suite covering all core requirements and regression gates:

```powershell
python -m unittest tests/test_jansahayak.py
```

### Test Coverage Summary (14/14 Passing):
1. `test_1_complete_request_and_confirmation_gate`: Validates complete submission journey and verifies that omitting explicit customer confirmation is strictly blocked.
2. `test_2_missing_information_gate`: Verifies that incomplete profiles are caught and missing slots are prompted one at a time.
3. `test_3_duplicate_submission_prevention`: Verifies that repeated clicks or Streamlit reruns do not create duplicate database records.
4. `test_4_correction_after_doubtful_speech`: Tests speech correction and doubtful transcription reprompting.
5. `test_5_missing_or_conflicting_source_evidence`: Validates fact uncertainty detection and source citation integrity.
6. `test_6_staff_return_correction_and_resubmission`: Verifies end-to-end staff return lifecycle and customer resubmission with updated audit events.
7. `test_7_status_lookup_and_persistence`: Tests reference ID status tracking, spoken next steps, and SQLite session persistence.
8. `test_8_external_service_failure_resilience`: Verifies graceful fallback to labeled deterministic mode and safe speech error handling.
9. `test_9_regression_negative_confirmation_do_not_submit`: Verifies `"do not submit"` halts submission and creates no database record.
10. `test_10_regression_negative_confirmation_not_correct`: Verifies `"not correct"` routes to intake for correction and creates no database record.
11. `test_11_regression_negative_confirmation_hindi_nahi_sahi_nahi_hai`: Verifies `"नहीं, सही नहीं है"` routes to intake and creates no database record.
12. `test_12_regression_ambiguous_confirmation_does_not_submit`: Verifies ambiguous input reprompts without submitting; creates no database record.
13. `test_13_honest_source_verification_labels`: Verifies that scheme-name matches show "Official source available" (claim not verified, no dates), rumors are marked uncertain, and unknown topics are marked `UNVERIFIED_UNKNOWN_TOPIC`.
14. `test_14_honest_llm_status_after_fallback`: Verifies provider status honestly reports scripted fallback mode when live AI encounters failure.

---

## 🎬 Demo Walkthrough Guide

### Step 1: Customer Intake (Voice or Text)
1. In the sidebar, select **🗣️ ग्राहक सेवा (Customer Portal)** and choose **🇮🇳 हिन्दी** or **🇬🇧 English**.
2. Press the microphone 🎙️ button or type:
   - *"मेरा नाम रमेश है और मैं रामपुर गाँव में रहता हूँ"* (or click quick chip "रमेश").
3. JanSahayak extracts `name: रमेश` and `location: रामपुर`, and asks the next question: *"आप क्या काम करते हैं?"*
4. Answer: *"मैं किसान हूँ"* (or click "किसान (Farmer)").
5. JanSahayak asks for purpose: Answer *"मुझे सरकारी योजना का पैसा पाना है"* (or click "सरकारी योजना / सब्सिडी").

### Step 2: Scheme Advisory
- The Banking Agent automatically recommends **Pradhan Mantri Jan Dhan Yojana (PMJDY)** and **PMSBY (सुरक्षा बीमा)**.
- Notice the "Official source available" label with the RBI / Ministry of Finance citation on each card (record lookup only; the customer's claim is not verified).
- Click **✅ यह चुनें (PMJDY)** to select.

### Step 3: Review & Explicit Confirmation Gate
- JanSahayak reads back the complete summary aloud in spoken audio.
- Shows the physical document checklist (2 photos + ID or Small Account option) and displays the safety notice: *No real Aadhaar or identity docs taken online!*
- Click **✅ हाँ, सब सही है — जमा करें (Confirm & Submit)**.

### Step 4: Tracked Request & Staff Review
1. A unique Reference ID is generated (e.g. `JS-2026-4892`).
2. Switch in sidebar to **👥 बैंक कर्मचारी समीक्षा (Staff Review Demo)**.
3. Locate the request, enter staff review notes (e.g., *"Please confirm exact village locality"*), and click **🟡 लौटाएं (Return)**.
4. Switch back to Customer Portal -> Click **🔍 स्थिति देखें (Track)**.
5. Enter `JS-2026-4892`. Listen to the audio notice explaining why staff returned it.
6. Update the location, check the confirmation box, and click **📤 सुधार जमा करें (Resubmit Request)**.
7. Check the complete immutable audit trail!

---

## ⚖️ Limitations & Disclaimers
- **Demo Mode**: Real banking account opening requires physical in-person branch verification, biometrics, and original documentation as mandated by RBI KYC Master Directions.
- **No Financial Operations**: JanSahayak does not perform funds transfers, balance inquiries, or credit underwriting.
- **Synthetic Data**: Never enter real Aadhaar numbers, PAN cards, OTPs, or passwords.
