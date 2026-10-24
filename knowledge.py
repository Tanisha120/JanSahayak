"""
JanSahayak Curated Official Knowledge Base
Contains 7 curated banking and scheme records that point to official Government of India
and Reserve Bank of India sources, complete with source URLs.

Includes plain-language summaries (Hindi and English), eligibility rules, KYC guidance,
and uncertainty handling for conflicting or unverified requests.

Note: matching a scheme name to a record is record retrieval only. It does NOT verify a
customer's claim, and no verification dates are stored or displayed.
"""

import re
from typing import List, Dict, Any, Optional

OFFICIAL_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "id": "PMJDY",
        "name_en": "Pradhan Mantri Jan Dhan Yojana (PMJDY)",
        "name_hi": "प्रधानमंत्री जन धन योजना (PMJDY)",
        "category": "ACCOUNT",
        "official_source_title": "Department of Financial Services, Ministry of Finance, Govt of India",
        "official_source_url": "https://pmjdy.gov.in/",
        "min_balance_inr": 0,
        "eligibility_en": "Any Indian citizen aged 10 years or older. Overdraft facility available for ages 18-65.",
        "eligibility_hi": "10 वर्ष या उससे अधिक आयु का कोई भी भारतीय नागरिक। ओवरड्राफ्ट सुविधा 18-65 वर्ष के लिए उपलब्ध है।",
        "benefits_en": [
            "Zero balance account (no penalty for maintaining zero balance)",
            "Free RuPay Debit Card with ₹2 Lakh accidental insurance cover",
            "Direct Benefit Transfer (DBT) for PM-KISAN, ration, subsidies and pensions",
            "Overdraft facility up to ₹10,000 (after 6 months satisfactory operation)"
        ],
        "benefits_hi": [
            "जीरो बैलेंस खाता (खाते में शून्य रुपये रहने पर भी कोई जुर्माना नहीं)",
            "मुफ्त रुपे डेबिट कार्ड जिसके साथ 2 लाख रुपये का दुर्घटना बीमा मिलता है",
            "सरकारी योजनाओं (पीएम किसान, पेंशन, सब्सिडी) का सीधा पैसा खाते में (DBT)",
            "6 महीने खाते के अच्छे संचालन के बाद ₹10,000 तक की ओवरड्राफ्ट सुविधा"
        ],
        "plain_explanation_en": "This is a zero-balance government bank account made for every citizen. You do not need to keep any money in it, you get a free card, and all government financial help comes straight into this account.",
        "plain_explanation_hi": "यह हर नागरिक के लिए सरकार का जीरो बैलेंस बैंक खाता है। इसमें हमेशा पैसे रखने का कोई दबाव नहीं होता, आपको मुफ्त एटीएम कार्ड मिलता है और सरकारी योजनाओं का पैसा सीधे इसमें आता है।",
        "recommended_for": ["daily_wage", "farmer", "homemaker", "student", "low_income", "unbanked", "subsidies"]
    },
    {
        "id": "BSBDA",
        "name_en": "Basic Savings Bank Deposit Account (BSBDA)",
        "name_hi": "बुनियादी बचत बैंक जमा खाता (BSBDA)",
        "category": "ACCOUNT",
        "official_source_title": "Reserve Bank of India Master Circular on BSBDA (DBOD.No.Leg.BC.35/09.07.005/2012-13)",
        "official_source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx?id=9862",
        "min_balance_inr": 0,
        "eligibility_en": "Any individual resident. The account holder cannot hold any other savings account in the same bank.",
        "eligibility_hi": "कोई भी निवासी नागरिक। इस खाते वाले व्यक्ति का उसी बैंक में कोई दूसरा बचत खाता नहीं हो सकता।",
        "benefits_en": [
            "Zero minimum balance requirement",
            "Unlimited free cash deposits at branch and ATMs",
            "Four free cash withdrawals per month (including branch and ATM)",
            "Free basic ATM-cum-debit card without annual fees"
        ],
        "benefits_hi": [
            "खाते में न्यूनतम राशि रखने की कोई बाध्यता नहीं",
            "बैंक शाखा और एटीएम में पैसे जमा करने पर कोई सीमा या शुल्क नहीं",
            "हर महीने 4 बार मुफ्त में पैसे निकालने की सुविधा",
            "मुफ्त बेसिक एटीएम-कम-डेबिट कार्ड बिना वार्षिक शुल्क के"
        ],
        "plain_explanation_en": "A simple, fee-free savings account mandated by RBI for all banks. It has no minimum balance requirement and provides 4 free withdrawals each month.",
        "plain_explanation_hi": "आरबीआई द्वारा सभी बैंकों के लिए तय किया गया साधारण बचत खाता। इसमें शून्य बैलेंस रहता है और महीने में 4 बार मुफ्त पैसे निकाल सकते हैं।",
        "recommended_for": ["general_savings", "no_fees", "simple_banking", "rural"]
    },
    {
        "id": "REGULAR_SAVINGS",
        "name_en": "Regular Savings Bank Account",
        "name_hi": "नियमित बचत बैंक खाता",
        "category": "ACCOUNT",
        "official_source_title": "Reserve Bank of India Guidelines on Customer Service in Banks",
        "official_source_url": "https://www.rbi.org.in/",
        "min_balance_inr": 1000,
        "eligibility_en": "Resident individuals with standard KYC documents.",
        "eligibility_hi": "मानक पहचान दस्तावेजों (केवाईसी) वाले निवासी नागरिक।",
        "benefits_en": [
            "Unlimited deposit and withdrawal flexibility (subject to branch limits)",
            "Cheque book, full internet banking and UPI facilities",
            "Quarterly interest on savings balance",
            "Higher daily ATM withdrawal limits"
        ],
        "benefits_hi": [
            "असीमित लेनदेन और चेक बुक की सुविधा",
            "पूर्ण इंटरनेट बैंकिंग और यूपीआई सुविधा",
            "बचत राशि पर त्रैमासिक ब्याज",
            "दैनिक निकासी की अधिक सीमा"
        ],
        "plain_explanation_en": "A standard bank account with complete banking services, cheque book, and high transaction limits. It usually requires maintaining ₹500 to ₹3,000 average balance depending on the branch location.",
        "plain_explanation_hi": "यह पूर्ण सुविधाओं वाला सामान्य बैंक खाता है जिसमें चेक बुक और अधिक लेनदेन की सुविधा होती है। इसमें आमतौर पर ₹500 से ₹3,000 तक न्यूनतम बैलेंस रखना होता है।",
        "recommended_for": ["shopkeeper", "salaried", "business", "higher_income"]
    },
    {
        "id": "PMSBY",
        "name_en": "Pradhan Mantri Suraksha Bima Yojana (PMSBY)",
        "name_hi": "प्रधानमंत्री सुरक्षा बीमा योजना (PMSBY)",
        "category": "SCHEME_INSURANCE",
        "official_source_title": "Department of Financial Services, Ministry of Finance, Govt of India",
        "official_source_url": "https://financialservices.gov.in/beta/en/pmsby",
        "min_balance_inr": 0,
        "eligibility_en": "Bank account holders aged 18 to 70 years.",
        "eligibility_hi": "18 से 70 वर्ष के बैंक खाताधारक।",
        "benefits_en": [
            "₹2,00,000 for accidental death or permanent total disability",
            "₹1,00,000 for permanent partial disability",
            "Very affordable premium of only ₹20 per year",
            "Automatic debit from bank account annually in May"
        ],
        "benefits_hi": [
            "दुर्घटना में मृत्यु या पूर्ण विकलांगता होने पर ₹2 लाख की सहायता",
            "स्थायी आंशिक विकलांगता पर ₹1 लाख की सहायता",
            "सालाना मात्र ₹20 का अत्यंत कम प्रीमियम",
            "हर साल मई माह में बैंक खाते से स्वतः भुगतान"
        ],
        "plain_explanation_en": "For just ₹20 per year, this government accident insurance gives ₹2 Lakh financial safety to your family if any accident happens.",
        "plain_explanation_hi": "साल में केवल ₹20 देकर आप यह दुर्घटना बीमा ले सकते हैं। किसी दुर्घटना की स्थिति में परिवार को 2 लाख रुपये तक की आर्थिक सुरक्षा मिलती है।",
        "recommended_for": ["all", "daily_wage", "farmer", "driver", "laborer", "construction", "low_income"]
    },
    {
        "id": "PMJJBY",
        "name_en": "Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)",
        "name_hi": "प्रधानमंत्री जीवन ज्योति बीमा योजना (PMJJBY)",
        "category": "SCHEME_INSURANCE",
        "official_source_title": "Department of Financial Services, Ministry of Finance, Govt of India",
        "official_source_url": "https://financialservices.gov.in/beta/en/pmjjby",
        "min_balance_inr": 0,
        "eligibility_en": "Bank account holders aged 18 to 50 years with consent to auto-debit.",
        "eligibility_hi": "18 से 50 वर्ष के बैंक खाताधारक।",
        "benefits_en": [
            "₹2,00,000 life insurance cover for death due to any reason (illness or accident)",
            "Affordable premium of ₹436 per year",
            "Renewable on annual basis up to age 55",
            "Simple claim process credited directly to nominee"
        ],
        "benefits_hi": [
            "किसी भी कारण (बीमारी या दुर्घटना) से मृत्यु होने पर परिवार को ₹2 लाख की जीवन सुरक्षा",
            "सालाना मात्र ₹436 का प्रीमियम",
            "55 वर्ष की आयु तक प्रतिवर्ष नवीकरणीय",
            "नॉमिनी के खाते में सीधा और सरल दावा निपटान"
        ],
        "plain_explanation_en": "This is life insurance for ₹436 per year. If anything happens to you due to sickness or accident, your family receives ₹2 Lakh.",
        "plain_explanation_hi": "यह सालाना ₹436 का सरकारी जीवन बीमा है। बीमारी या किसी भी कारण से जान जाने पर आपके परिवार को ₹2 लाख मिलते हैं।",
        "recommended_for": ["family_head", "sole_earner", "informal_worker", "farmer", "artisan"]
    },
    {
        "id": "APY",
        "name_en": "Atal Pension Yojana (APY)",
        "name_hi": "अटल पेंशन योजना (APY)",
        "category": "SCHEME_PENSION",
        "official_source_title": "Pension Fund Regulatory and Development Authority (PFRDA) & NSDL",
        "official_source_url": "https://www.pfrda.org.in/",
        "min_balance_inr": 0,
        "eligibility_en": "Indian citizens aged 18 to 40 years holding a savings bank account (non-taxpayers).",
        "eligibility_hi": "18 से 40 वर्ष के भारतीय नागरिक जिनके पास बचत खाता है (गैर-आयकरदाता)।",
        "benefits_en": [
            "Guaranteed monthly pension of ₹1,000, ₹2,000, ₹3,000, ₹4,000, or ₹5,000 after age 60",
            "Govt guaranteed minimum pension returns",
            "Spouse continues to receive the exact same pension after subscriber's demise",
            "Full accumulated pension corpus returned to the nominee"
        ],
        "benefits_hi": [
            "60 वर्ष की आयु के बाद हर महीने ₹1,000 से लेकर ₹5,000 तक की पक्की पेंशन",
            "भारत सरकार द्वारा न्यूनतम पेंशन की गारंटी",
            "खाताधारक के बाद पति/पत्नी को आजीवन वही मासिक पेंशन",
            "दोनों के बाद जमा पूरा फंड नामांकित व्यक्ति (नॉमिनी) को वापस"
        ],
        "plain_explanation_en": "A pension plan for your old age. You save a small amount every month now, and after you turn 60, government gives you a fixed monthly pension up to ₹5,000 every month for life.",
        "plain_explanation_hi": "बुढ़ापे के लिए मासिक पेंशन योजना। अभी से हर महीने थोड़ी बचत करने पर 60 साल की उम्र के बाद सरकार से हर महीने ₹1,000 से ₹5,000 की पक्की पेंशन मिलती है।",
        "recommended_for": ["unorganized_worker", "daily_wage", "vendor", "farmer", "craftsperson", "pension"]
    },
    {
        "id": "KYC_GUIDELINES",
        "name_en": "RBI KYC Master Direction & Simplified KYC for Small Accounts",
        "name_hi": "आरबीआई केवाईसी दिशानिर्देश एवं छोटे खातों के सरल नियम",
        "category": "KYC_GUIDANCE",
        "official_source_title": "Reserve Bank of India Master Direction - Know Your Customer (KYC) Direction, 2016",
        "official_source_url": "https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566",
        "min_balance_inr": 0,
        "eligibility_en": "All resident individuals applying for bank accounts.",
        "eligibility_hi": "बैंक खाता खोलने वाले सभी निवासी नागरिक।",
        "benefits_en": [
            "Officially Valid Documents (OVD): Voter ID, Passport, Driving Licence, NREGA Job Card, Aadhaar proof",
            "Small Account facility: If you have NO official identity card, you can still open an account with just a passport photo and thumb impression in front of bank staff",
            "JanSahayak does NOT collect real documents or Aadhaar numbers online"
        ],
        "benefits_hi": [
            "मान्य पहचान दस्तावेज: वोटर कार्ड, मनरेगा जॉब कार्ड, ड्राइविंग लाइसेंस, पासपोर्ट या आधार",
            "छोटा खाता सुविधा: यदि आपके पास कोई सरकारी पहचान पत्र नहीं है, तो भी बैंक अधिकारी के सामने केवल फोटो और अंगूठा लगाकर खाता खुल सकता है",
            "जनसहायक ऐप में कोई असली दस्तावेज या आधार नंबर नहीं लिया जाता"
        ],
        "plain_explanation_en": "You only need basic documents to open an account. If you do not have documents, you can still open a 'Small Account' at the branch with just a photo and thumb impression.",
        "plain_explanation_hi": "खाता खोलने के लिए बहुत सरल कागजात चाहिए। अगर आपके पास कोई भी पहचान पत्र नहीं है, तो भी आप बैंक जाकर केवल फोटो और अंगूठा लगाकर 'छोटा खाता' खुलवा सकते हैं।",
        "recommended_for": ["all", "unbanked", "no_documents"]
    }
]


def get_all_records() -> List[Dict[str, Any]]:
    """Return all curated official records."""
    return OFFICIAL_KNOWLEDGE_BASE


def get_record_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single official record by its ID."""
    for rec in OFFICIAL_KNOWLEDGE_BASE:
        if rec["id"].upper() == record_id.upper():
            return rec
    return None


def match_schemes(occupation: str = "", purpose: str = "", income_bracket: str = "", language: str = "en") -> List[Dict[str, Any]]:
    """
    Deterministically retrieve relevant curated records based on customer profile & needs.
    Always returns at least PMJDY/BSBDA and relevant social security scheme (PMSBY/PMJJBY/APY).
    """
    occ = occupation.lower()
    purp = purpose.lower()
    results = []

    # Check for accounts
    if "business" in occ or "shop" in occ or "salaried" in occ or "regular" in purp:
        rec = get_record_by_id("REGULAR_SAVINGS")
        if rec:
            results.append(rec)
    else:
        rec = get_record_by_id("PMJDY")
        if rec:
            results.append(rec)

    # Always include BSBDA as alternative zero-balance option
    bsbda = get_record_by_id("BSBDA")
    if bsbda and bsbda not in results:
        results.append(bsbda)

    # Check for social security schemes based on purpose/occupation
    if "pension" in purp or "old age" in purp or "बुढ़ापा" in purp or "पेंशन" in purp:
        apy = get_record_by_id("APY")
        if apy and apy not in results:
            results.append(apy)

    if "insurance" in purp or "death" in purp or "life" in purp or "बीमा" in purp:
        pmjjby = get_record_by_id("PMJJBY")
        if pmjjby and pmjjby not in results:
            results.append(pmjjby)

    # Always recommend PMSBY (accidental insurance at ₹20/yr) for low-income or general workers
    pmsby = get_record_by_id("PMSBY")
    if pmsby and pmsby not in results:
        results.append(pmsby)

    # If APY not yet included and customer is unorganized worker, include APY
    if any(k in occ for k in ["farmer", "wage", "labor", "mazdoor", "driver", "maid", "vendor", "artisan"]):
        apy = get_record_by_id("APY")
        if apy and apy not in results:
            results.append(apy)

    # Always attach KYC guidance
    kyc = get_record_by_id("KYC_GUIDELINES")
    if kyc and kyc not in results:
        results.append(kyc)

    return results


# Specific official identifiers mapped directly to curated records in OFFICIAL_KNOWLEDGE_BASE
CURATED_SCHEME_SPECIFIC_IDENTIFIERS: Dict[str, List[str]] = {
    "PMJDY": [
        "pmjdy", "pradhan mantri jan dhan yojana", "प्रधानमंत्री जन धन योजना",
        "jan dhan yojana", "जन धन योजना", "jan dhan", "जन धन", "जनधन",
        "pm jan dhan", "पीएम जन धन"
    ],
    "BSBDA": [
        "bsbda", "basic savings bank deposit account", "बुनियादी बचत बैंक जमा खाता",
        "basic savings bank account", "बुनियादी बचत खाता", "rbi basic savings"
    ],
    "REGULAR_SAVINGS": [
        "regular savings account", "नियमित बचत बैंक खाता", "नियमित बचत खाता",
        "standard savings account", "commercial bank savings account"
    ],
    "PMSBY": [
        "pmsby", "pradhan mantri suraksha bima yojana", "प्रधानमंत्री सुरक्षा बीमा योजना",
        "suraksha bima yojana", "सुरक्षा बीमा योजना", "suraksha bima", "सुरक्षा बीमा"
    ],
    "PMJJBY": [
        "pmjjby", "pradhan mantri jeevan jyoti bima yojana", "प्रधानमंत्री जीवन ज्योति बीमा योजना",
        "jeevan jyoti bima yojana", "जीवन ज्योति बीमा योजना", "jeevan jyoti", "जीवन ज्योति"
    ],
    "APY": [
        "apy", "atal pension yojana", "अटल पेंशन योजना", "atal pension", "अटल पेंशन"
    ],
    "KYC_GUIDELINES": [
        "rbi kyc guidelines", "small account facility", "छोटा खाता सुविधा",
        "rbi simplified kyc", "small account rules", "छोटा खाता नियम",
        "rbi kyc master direction"
    ]
}


def match_claim_to_curated_record(query_or_topic: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the curated official record whose scheme name/identifier appears in the text.
    Requires specific scheme identifiers rather than broad generic words.
    This is record retrieval only; it does not verify the customer's claim.
    """
    lowered = (query_or_topic or "").lower().strip()
    if not lowered:
        return None

    for scheme_id, identifiers in CURATED_SCHEME_SPECIFIC_IDENTIFIERS.items():
        for ident in identifiers:
            # Word boundary or exact phrase match
            pattern = rf"(?:\b|^){re.escape(ident)}(?:\b|$)"
            if re.search(pattern, lowered):
                return get_record_by_id(scheme_id)

    return None


def check_fact_uncertainty(query_or_topic: str) -> Dict[str, Any]:
    """
    Safeguard against non-official, unverified, or conflicting claims.
    Replaces broad keyword matching with specific curated record matching.
    - Matched curated records: OFFICIAL_SOURCE_AVAILABLE. The record was retrieved by scheme
      name only; the customer's claim is NOT verified (claim_verified=False). No date is claimed.
      is_certain=True here only means "no uncertainty warning is needed", not "claim verified".
    - Rumors / misleading claims: Explicitly marked UNVERIFIED_RUMOR.
    - Unmatched claims: Strictly remain UNCERTAIN (is_certain=False).
    """
    lowered = (query_or_topic or "").lower().strip()
    if not lowered:
        return {
            "is_certain": True,
            "status": "DEFAULT_INTAKE",
            "matched_record": None,
            "claim_verified": False,
            "reason_en": "Standard banking assistance request.",
            "reason_hi": "सामान्य बैंकिंग सहायता अनुरोध।"
        }

    # 1. Known informal rumors, misleading claims, or conflicting financial topics
    rumor_keywords = [
        "free money", "loan waiver", "maafi", "कर्ज माफी", "muft", "मुफ्त पैसा",
        "lottery", "crypto", "get rich", "unlimited loan", "guaranteed return",
        "interest free loan", "cash handout", "free cash", "बिना ब्याज कर्ज"
    ]
    for kw in rumor_keywords:
        if kw in lowered:
            return {
                "is_certain": False,
                "status": "UNVERIFIED_RUMOR",
                "matched_record": None,
                "claim_verified": False,
                "label_en": "⚠️ Unverified Rumor / Misleading Claim",
                "label_hi": "⚠️ असत्यापित अफवाह / अनधिकृत दावा",
                "reason_en": "This claim is not an official government scheme and is marked as UNCERTAIN. Informal rumors should not be trusted.",
                "reason_hi": "यह जानकारी भारत सरकार या आरबीआई के आधिकारिक रिकॉर्ड में प्रमाणित नहीं है। कृपया ऐसी अफवाहों पर विश्वास न करें और बैंक शाखा जाकर पूछताछ करें।",
                "recommendation_en": "Speak directly with authorized bank branch officers.",
                "recommendation_hi": "बैंक शाखा में उपस्थित अधिकृत अधिकारी से सीधे बात करें।"
            }

    # 2. Match to specific curated official records
    matched_record = match_claim_to_curated_record(lowered)
    if matched_record:
        return {
            "is_certain": True,  # no uncertainty warning needed; NOT a claim verification
            "status": "OFFICIAL_SOURCE_AVAILABLE",
            "claim_verified": False,
            "matched_record_id": matched_record["id"],
            "matched_record_name": matched_record["name_en"],
            "official_source_title": matched_record["official_source_title"],
            "official_source_url": matched_record["official_source_url"],
            "label_en": f"Official source available: {matched_record['name_en']}",
            "label_hi": f"आधिकारिक स्रोत उपलब्ध: {matched_record['name_hi']}",
            "reason_en": f"An official record was retrieved from {matched_record['official_source_title']} by matching the scheme name. This is a record lookup only; it does not verify the customer's claim.",
            "reason_hi": f"{matched_record['name_hi']} के लिए आधिकारिक स्रोत ({matched_record['official_source_title']}) का रिकॉर्ड योजना के नाम से खोजा गया है। यह केवल रिकॉर्ड खोज है; इससे ग्राहक के दावे की पुष्टि नहीं होती।"
        }

    # 3. Unmatched claims MUST remain uncertain (no verification date or claim-verified status without evidence)
    return {
        "is_certain": False,
        "status": "UNVERIFIED_UNMATCHED_CLAIM",
        "matched_record": None,
        "claim_verified": False,
        "official_source_title": None,
        "official_source_url": None,
        "label_en": "⚠️ Uncertain / Unmatched Claim (No Official Record)",
        "label_hi": "⚠️ अनिश्चित / असत्यापित दावा (कोई आधिकारिक रिकॉर्ड नहीं)",
        "reason_en": "This claim does not match any specific official Government of India or RBI curated record in our repository. It remains UNCERTAIN.",
        "reason_hi": "यह दावा हमारे ज्ञानकोष में मौजूद किसी विशिष्ट प्रमाणित सरकारी/आरबीआई रिकॉर्ड से मेल नहीं खाता है। यह जानकारी अनिश्चित है।",
        "recommendation_en": "Please consult an authorized bank branch officer to verify whether this claim or scheme exists.",
        "recommendation_hi": "कृपया यह जानने के लिए कि क्या ऐसी कोई योजना या दावा अस्तित्व में है, अधिकृत बैंक शाखा अधिकारी से परामर्श लें।"
    }


def get_document_checklist(selected_scheme_id: str, language: str = "en") -> List[str]:
    """
    Generate customer-friendly physical document checklist to take to the bank branch.
    NEVER asks for real documents online.
    """
    if language == "hi":
        return [
            "1. दो हालिया पासपोर्ट साइज फोटो",
            "2. कोई भी एक सरकारी पहचान पत्र (वोटर कार्ड, मनरेगा जॉब कार्ड, या आधार कार्ड यदि उपलब्ध हो)",
            "3. निवास प्रमाण (बिजली बिल, राशन कार्ड, या सरपंच/प्रधान द्वारा जारी पत्र)",
            "4. यदि कोई पहचान पत्र नहीं है: आप केवल अपनी फोटो और अंगूठा लगाकर 'छोटा खाता' खुलवा सकते हैं।"
        ]
    else:
        return [
            "1. Two recent passport-size photographs",
            "2. Any one official identity document (Voter ID, NREGA Job Card, or Aadhaar if available)",
            "3. Address proof (Electricity bill, Ration card, or letter from Gram Panchayat/Pradhan)",
            "4. If you have no documents: You can open a 'Small Account' at the branch using just your photo and thumb impression."
        ]
