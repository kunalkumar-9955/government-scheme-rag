"""
management/commands/seed_evaluation_dataset.py

Seeds a curated 20-case evaluation dataset for Indian Government Schemes RAG.

Usage:
  python manage.py seed_evaluation_dataset --settings=config.settings.phase1

Each case contains:
  - question:                   Real citizen query
  - expected_evidence:          Verbatim evidence passage (or key phrase) that should be retrieved
  - expected_answer_keywords:   Words/phrases that must appear in a correct answer
  - difficulty:                 EASY / MEDIUM / HARD
  - category:                   ELIGIBILITY / BENEFITS / PROCEDURE / DOCUMENTS / GENERAL
"""
from django.core.management.base import BaseCommand
from apps.evaluation.models import EvaluationDataset, EvaluationCase, CaseDifficulty, CaseCategory

SEED_CASES = [
    # ── ELIGIBILITY ──────────────────────────────────────────
    {
        "question": "Who is eligible for the PM-KISAN scheme?",
        "expected_evidence": "Small and marginal farmers with cultivable landholding up to 2 hectares are eligible for PM-KISAN income support.",
        "expected_answer_keywords": ["farmer", "land", "hectare", "small", "marginal", "cultivable"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.ELIGIBILITY,
        "notes": "Core eligibility rule for PM-KISAN — must retrieve 'small and marginal' definition.",
    },
    {
        "question": "Can a government employee apply for PM-KISAN?",
        "expected_evidence": "Institutional land holders, government employees, income tax payers are excluded from PM-KISAN benefits.",
        "expected_answer_keywords": ["government employee", "excluded", "not eligible", "ineligible"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.ELIGIBILITY,
        "notes": "Tests retrieval of exclusion clauses.",
    },
    {
        "question": "What is the age limit for the Pradhan Mantri Ujjwala Yojana scheme?",
        "expected_evidence": "Women aged 18 years and above who are Below Poverty Line (BPL) household members are eligible.",
        "expected_answer_keywords": ["18", "women", "BPL", "below poverty line"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.ELIGIBILITY,
        "notes": "Age and gender eligibility for PMUY.",
    },
    {
        "question": "Is a person from the General category eligible for Pradhan Mantri Awas Yojana urban?",
        "expected_evidence": "EWS category with annual household income up to Rs 3 lakh and LIG with income up to Rs 6 lakh are primary beneficiaries under PMAY-U.",
        "expected_answer_keywords": ["EWS", "LIG", "income", "general", "annual income"],
        "difficulty": CaseDifficulty.HARD,
        "category": CaseCategory.ELIGIBILITY,
        "notes": "Tests income-based eligibility and category distinctions.",
    },
    {
        "question": "Who qualifies for Atal Pension Yojana?",
        "expected_evidence": "Indian citizens between 18 to 40 years of age with a savings bank or post office savings account are eligible for Atal Pension Yojana.",
        "expected_answer_keywords": ["18", "40", "savings account", "Indian citizen"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.ELIGIBILITY,
        "notes": "Age-range and account requirement for APY.",
    },

    # ── BENEFITS ─────────────────────────────────────────────
    {
        "question": "What is the financial benefit under PM-KISAN?",
        "expected_evidence": "Eligible farmers receive Rs 6,000 per year in three equal installments of Rs 2,000 each directly to their bank account.",
        "expected_answer_keywords": ["6000", "2000", "installment", "bank", "direct benefit transfer"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.BENEFITS,
        "notes": "Core benefit amount for PM-KISAN.",
    },
    {
        "question": "How much subsidy does PM Ujjwala Yojana provide for an LPG cylinder?",
        "expected_evidence": "A one-time financial assistance of Rs 1,600 is provided for release of LPG connection under Pradhan Mantri Ujjwala Yojana.",
        "expected_answer_keywords": ["1600", "LPG", "connection", "subsidy", "assistance"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.BENEFITS,
        "notes": "Financial support amount for PMUY connection.",
    },
    {
        "question": "What pension amount is guaranteed under Atal Pension Yojana?",
        "expected_evidence": "APY provides a guaranteed minimum monthly pension of Rs 1,000 to Rs 5,000 per month from the age of 60 years.",
        "expected_answer_keywords": ["1000", "5000", "pension", "monthly", "60 years"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.BENEFITS,
        "notes": "Pension range under APY.",
    },
    {
        "question": "What is the maximum housing loan subsidy under PMAY for EWS category?",
        "expected_evidence": "Credit Linked Subsidy Scheme under PMAY provides interest subsidy of 6.5% on home loans up to Rs 6 lakh for EWS and LIG beneficiaries.",
        "expected_answer_keywords": ["6.5%", "interest subsidy", "EWS", "home loan", "credit linked"],
        "difficulty": CaseDifficulty.HARD,
        "category": CaseCategory.BENEFITS,
        "notes": "CLSS interest rate for EWS — requires precise numeric retrieval.",
    },
    {
        "question": "What crop insurance cover does PMFBY provide?",
        "expected_evidence": "Pradhan Mantri Fasal Bima Yojana provides comprehensive risk coverage against non-preventable natural risks from pre-sowing to post-harvest losses.",
        "expected_answer_keywords": ["crop", "insurance", "natural risk", "pre-sowing", "harvest", "loss"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.BENEFITS,
        "notes": "Coverage scope for PMFBY.",
    },

    # ── PROCEDURE ────────────────────────────────────────────
    {
        "question": "How do I apply for the PM-KISAN scheme?",
        "expected_evidence": "Farmers can register at PM-KISAN portal pmkisan.gov.in or approach Common Service Centres (CSC) for registration.",
        "expected_answer_keywords": ["pmkisan.gov.in", "CSC", "common service centre", "register", "portal"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.PROCEDURE,
        "notes": "Application URL and offline channel for PM-KISAN.",
    },
    {
        "question": "What is the process to apply for PMAY Urban online?",
        "expected_evidence": "Applicants can apply through the PMAY-U official portal pmaymis.gov.in or through Urban Local Bodies and banks.",
        "expected_answer_keywords": ["pmaymis.gov.in", "urban local body", "bank", "online", "apply"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.PROCEDURE,
        "notes": "Online vs offline application channels for PMAY-U.",
    },
    {
        "question": "How long does it take for PM-KISAN installment to be credited after registration?",
        "expected_evidence": "After successful verification and e-KYC completion, the first PM-KISAN installment is typically credited within 1-2 months.",
        "expected_answer_keywords": ["e-KYC", "verification", "month", "installment", "credited"],
        "difficulty": CaseDifficulty.HARD,
        "category": CaseCategory.PROCEDURE,
        "notes": "Post-registration timeline — tests retrieval of process timelines.",
    },
    {
        "question": "Where can I check my PM-KISAN payment status?",
        "expected_evidence": "Beneficiaries can check their payment status at pmkisan.gov.in under the 'Beneficiary Status' section using Aadhaar number, bank account, or mobile number.",
        "expected_answer_keywords": ["beneficiary status", "pmkisan.gov.in", "aadhaar", "payment"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.PROCEDURE,
        "notes": "Status check URL and identifiers for PM-KISAN.",
    },

    # ── REQUIRED DOCUMENTS ───────────────────────────────────
    {
        "question": "What documents are required to apply for PM-KISAN?",
        "expected_evidence": "Aadhaar card, bank passbook, and land ownership documents are required for PM-KISAN registration.",
        "expected_answer_keywords": ["aadhaar", "bank passbook", "land", "ownership", "document"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.DOCUMENTS,
        "notes": "Required document checklist for PM-KISAN.",
    },
    {
        "question": "What proof is needed for applying for PMUY LPG connection?",
        "expected_evidence": "BPL ration card, Aadhaar card or voter ID as identity proof, and address proof are required for PMUY LPG connection.",
        "expected_answer_keywords": ["BPL", "ration card", "aadhaar", "voter ID", "address proof"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.DOCUMENTS,
        "notes": "PMUY document checklist — BPL ration card is distinctive.",
    },
    {
        "question": "Does PM-KISAN require e-KYC verification?",
        "expected_evidence": "e-KYC is mandatory for PM-KISAN beneficiaries to continue receiving financial benefits.",
        "expected_answer_keywords": ["e-KYC", "mandatory", "verification", "continue", "benefits"],
        "difficulty": CaseDifficulty.MEDIUM,
        "category": CaseCategory.DOCUMENTS,
        "notes": "e-KYC requirement — important compliance document.",
    },

    # ── GENERAL ──────────────────────────────────────────────
    {
        "question": "What is the main objective of the PM-KISAN scheme?",
        "expected_evidence": "PM-KISAN aims to supplement the financial needs of land holding farmers to meet their agricultural input costs and domestic needs.",
        "expected_answer_keywords": ["income support", "farmer", "agricultural", "financial", "supplement"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.GENERAL,
        "notes": "Objective / purpose query for PM-KISAN.",
    },
    {
        "question": "Which ministry runs the Atal Pension Yojana scheme?",
        "expected_evidence": "Atal Pension Yojana is administered by the Pension Fund Regulatory and Development Authority (PFRDA) under the Ministry of Finance.",
        "expected_answer_keywords": ["PFRDA", "Pension Fund", "Ministry of Finance", "regulatory"],
        "difficulty": CaseDifficulty.EASY,
        "category": CaseCategory.GENERAL,
        "notes": "Ministry attribution — tests scheme metadata retrieval.",
    },
    {
        "question": "What is the difference between PM-KISAN and PMFBY?",
        "expected_evidence": "PM-KISAN provides direct income support of Rs 6000 per year to farmers, while PMFBY provides crop insurance against natural calamities and pests.",
        "expected_answer_keywords": ["PM-KISAN", "PMFBY", "income support", "insurance", "difference"],
        "difficulty": CaseDifficulty.HARD,
        "category": CaseCategory.GENERAL,
        "notes": "Comparison query — requires retrieval from two different scheme documents.",
    },
]


class Command(BaseCommand):
    help = "Seed a curated 20-case evaluation dataset for Indian Government Schemes RAG evaluation."

    def handle(self, *args, **options):
        dataset, created = EvaluationDataset.objects.get_or_create(
            name="Indian Government Schemes — Baseline Evaluation v1",
            defaults={
                "description": (
                    "Curated 20-case evaluation dataset covering PM-KISAN, PMUY, APY, PMAY, and PMFBY. "
                    "Tests retrieval relevance, context grounding, answer faithfulness, and citation correctness."
                ),
                "version": "1.0",
                "is_active": True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created dataset: {dataset.name}"))
        else:
            self.stdout.write(f"Dataset already exists: {dataset.name}")

        added = 0
        skipped = 0
        for case_data in SEED_CASES:
            _, was_created = EvaluationCase.objects.get_or_create(
                dataset=dataset,
                question=case_data["question"],
                defaults={
                    "expected_document_ids":      [],  # populated after documents are uploaded
                    "expected_evidence":          case_data["expected_evidence"],
                    "expected_answer_keywords":   case_data["expected_answer_keywords"],
                    "difficulty":                 case_data["difficulty"],
                    "category":                   case_data["category"],
                    "notes":                      case_data.get("notes", ""),
                }
            )
            if was_created:
                added += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Seed complete: {added} cases added, {skipped} already existed. "
            f"Dataset ID: {dataset.id}"
        ))
