"""
apps/schemes/management/commands/seed_schemes.py
------------------------------------------------
Seeds normalized States, Ministries, Departments, Scheme Categories, and
full-fidelity flagship schemes with structured eligibility rules, benefits,
required documents, application steps, sources, and versions.
"""

from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from apps.schemes.models import (
    State,
    Ministry,
    Department,
    SchemeCategory,
    GovernmentScheme,
    SchemeEligibilityRule,
    SchemeBenefit,
    RequiredDocument,
    ApplicationProcedure,
    SchemeSource,
    SchemeVersion,
    SchemeType,
    SchemeStatus,
    RuleOperator,
    RuleDataType,
    BenefitType,
    DisbursementFrequency,
    DocumentType,
    ApplicationMode,
    SourceType,
)


class Command(BaseCommand):
    help = "Seed normalized States, Ministries, Categories, and flagship Government Schemes."

    def handle(self, *args, **options):
        self.stdout.write("[INFO] Starting Scheme Data Management Seeding...")

        # ── 1. Seed States & Union Territories ──────────────────
        states_data = [
            ("AP", "Andhra Pradesh", False),
            ("AR", "Arunachal Pradesh", False),
            ("AS", "Assam", False),
            ("BR", "Bihar", False),
            ("CT", "Chhattisgarh", False),
            ("GA", "Goa", False),
            ("GJ", "Gujarat", False),
            ("HR", "Haryana", False),
            ("HP", "Himachal Pradesh", False),
            ("JH", "Jharkhand", False),
            ("KA", "Karnataka", False),
            ("KL", "Kerala", False),
            ("MP", "Madhya Pradesh", False),
            ("MH", "Maharashtra", False),
            ("MN", "Manipur", False),
            ("ML", "Meghalaya", False),
            ("MZ", "Mizoram", False),
            ("NL", "Nagaland", False),
            ("OD", "Odisha", False),
            ("PB", "Punjab", False),
            ("RJ", "Rajasthan", False),
            ("SK", "Sikkim", False),
            ("TN", "Tamil Nadu", False),
            ("TG", "Telangana", False),
            ("TR", "Tripura", False),
            ("UP", "Uttar Pradesh", False),
            ("UK", "Uttarakhand", False),
            ("WB", "West Bengal", False),
            ("DL", "Delhi", True),
            ("JK", "Jammu & Kashmir", True),
            ("LA", "Ladakh", True),
            ("CH", "Chandigarh", True),
            ("PY", "Puducherry", True),
            ("AN", "Andaman and Nicobar Islands", True),
            ("DN", "Dadra and Nagar Haveli and Daman and Diu", True),
            ("LD", "Lakshadweep", True),
        ]
        state_objs = {}
        for code, name, is_ut in states_data:
            st, _ = State.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_union_territory": is_ut},
            )
            state_objs[code] = st
        self.stdout.write(f"[OK] Seeded {len(state_objs)} States and UTs.")

        # ── 2. Seed Ministries & Departments ────────────────────
        ministries_data = [
            {
                "name": "Ministry of Agriculture and Farmers Welfare",
                "short_code": "MoA&FW",
                "website_url": "https://agricoop.nic.in",
                "is_central": True,
                "departments": [
                    ("Department of Agriculture and Farmers Welfare", "DA&FW"),
                    ("Department of Agricultural Research and Education", "DARE"),
                ],
            },
            {
                "name": "Ministry of Health and Family Welfare",
                "short_code": "MoHFW",
                "website_url": "https://mohfw.gov.in",
                "is_central": True,
                "departments": [
                    ("Department of Health and Family Welfare", "DOHFW"),
                    ("Department of Health Research", "DHR"),
                ],
            },
            {
                "name": "Ministry of Rural Development",
                "short_code": "MoRD",
                "website_url": "https://rural.nic.in",
                "is_central": True,
                "departments": [
                    ("Department of Rural Development", "DoRD"),
                    ("Department of Land Resources", "DoLR"),
                ],
            },
            {
                "name": "Ministry of Housing and Urban Affairs",
                "short_code": "MoHUA",
                "website_url": "https://mohua.gov.in",
                "is_central": True,
                "departments": [
                    ("Department of Housing and Urban Affairs", "MoHUA"),
                ],
            },
            {
                "name": "Ministry of Social Justice and Empowerment",
                "short_code": "MoSJE",
                "website_url": "https://socialjustice.gov.in",
                "is_central": True,
                "departments": [
                    ("Department of Social Justice and Empowerment", "DoSJE"),
                    ("Department of Empowerment of Persons with Disabilities", "DEPwD"),
                ],
            },
            {
                "name": "Ministry of Education",
                "short_code": "MoE",
                "website_url": "https://education.gov.in",
                "is_central": True,
                "departments": [
                    ("Department of School Education & Literacy", "DoSEL"),
                    ("Department of Higher Education", "DHE"),
                ],
            },
        ]
        ministry_objs = {}
        dept_objs = {}
        for m_data in ministries_data:
            m, _ = Ministry.objects.get_or_create(
                name=m_data["name"],
                defaults={
                    "short_code": m_data["short_code"],
                    "website_url": m_data["website_url"],
                    "is_central": m_data["is_central"],
                },
            )
            ministry_objs[m.short_code] = m
            for d_name, d_code in m_data["departments"]:
                d, _ = Department.objects.get_or_create(
                    ministry=m,
                    name=d_name,
                    defaults={"short_code": d_code},
                )
                dept_objs[d_code] = d
        self.stdout.write(f"[OK] Seeded {len(ministry_objs)} Ministries and {len(dept_objs)} Departments.")

        # ── 3. Seed Scheme Categories ───────────────────────────
        categories_data = [
            ("Agriculture, Rural & Environment", "agriculture-rural-environment", "🌾", "Schemes supporting farmers, agricultural inputs, crop insurance, and rural infrastructure."),
            ("Education & Learning", "education-learning", "🎓", "Scholarships, school education stipends, higher education loans, and fee waivers."),
            ("Healthcare & Wellness", "healthcare-wellness", "🏥", "Health insurance, medical treatments, maternal care, and public healthcare coverage."),
            ("Housing & Shelter", "housing-shelter", "🏠", "Affordable pucca housing grants for rural and urban low-income families."),
            ("Banking, Financial Services & Insurance", "banking-financial-services", "🏦", "Micro-loans, credit collateral guarantees, life insurance, and pension security."),
            ("Social Justice & Empowerment", "social-justice-empowerment", "🤝", "Welfare programs for SC, ST, OBC, EWS, minorities, senior citizens, and persons with disabilities."),
            ("Women & Child Development", "women-child-development", "👩‍👧", "Maternity benefits, girl child education incentives, and women entrepreneurship programs."),
            ("Employment & Skill Development", "employment-skills", "💼", "Vocational training, wage employment guarantees, apprenticeships, and job placement."),
        ]
        cat_objs = {}
        for name, slug, icon, desc in categories_data:
            c, _ = SchemeCategory.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "icon": icon, "description": desc},
            )
            cat_objs[slug] = c
        self.stdout.write(f"[OK] Seeded {len(cat_objs)} Scheme Categories.")

        # ── 4. Seed Flagship Government Schemes ──────────────────

        # Scheme 1: PM-KISAN
        pm_kisan, _ = GovernmentScheme.objects.get_or_create(
            slug="pradhan-mantri-kisan-samman-nidhi-pm-kisan",
            defaults={
                "name": "Pradhan Mantri Kisan Samman Nidhi",
                "short_title": "PM-KISAN",
                "description": (
                    "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a Central Sector Scheme to supplement the financial "
                    "needs of landholding farmers' families in procuring various inputs related to agriculture and allied "
                    "activities as well as domestic needs. Under the Scheme, the entire financial liability toward transfer "
                    "of benefit to beneficiaries is borne by the Government of India."
                ),
                "scheme_type": SchemeType.CENTRAL_SECTOR,
                "ministry": ministry_objs.get("MoA&FW"),
                "department": dept_objs.get("DA&FW"),
                "category": cat_objs.get("agriculture-rural-environment"),
                "target_beneficiaries": "All landholding farmer families with cultivable landholding in their names.",
                "status": SchemeStatus.ACTIVE,
                "version": "2024.1",
                "launch_date": date(2019, 2, 24),
                "important_dates": {
                    "eKYC_deadline": "Ongoing",
                    "installment_1_cycle": "April - July",
                    "installment_2_cycle": "August - November",
                    "installment_3_cycle": "December - March",
                },
                "official_application_url": "https://pmkisan.gov.in/RegistrationFormNew.aspx",
                "official_source_url": "https://pmkisan.gov.in",
                "funding_pattern": "100% Central Government Funded",
                "helpline_number": "155261 / 011-24300606",
                "tags": ["farmer", "agriculture", "dbt", "kisan", "cash support", "landholder"],
            },
        )

        # PM-KISAN Rules
        SchemeEligibilityRule.objects.filter(scheme=pm_kisan).delete()
        SchemeEligibilityRule.objects.bulk_create([
            SchemeEligibilityRule(
                scheme=pm_kisan,
                rule_group=1,
                criterion_key="occupation",
                operator=RuleOperator.EQUALS,
                value="FARMER",
                data_type=RuleDataType.STRING,
                is_mandatory=True,
                rule_description="Beneficiary must be a farmer with agricultural land holding.",
                order=1,
            ),
            SchemeEligibilityRule(
                scheme=pm_kisan,
                rule_group=1,
                criterion_key="land_holding_acres",
                operator=RuleOperator.GREATER_THAN,
                value="0",
                data_type=RuleDataType.DECIMAL,
                is_mandatory=True,
                rule_description="Must have cultivable landholding registered in revenue records.",
                order=2,
            ),
            SchemeEligibilityRule(
                scheme=pm_kisan,
                rule_group=1,
                criterion_key="is_institutional_landholder",
                operator=RuleOperator.BOOLEAN_FALSE,
                value="false",
                data_type=RuleDataType.BOOLEAN,
                is_mandatory=True,
                disqualification_condition=True,
                rule_description="Institutional landholders are not eligible.",
                order=3,
            ),
        ])

        # PM-KISAN Benefits
        SchemeBenefit.objects.filter(scheme=pm_kisan).delete()
        SchemeBenefit.objects.create(
            scheme=pm_kisan,
            benefit_type=BenefitType.DIRECT_BENEFIT_TRANSFER,
            title="Direct Income Support of Rs. 6,000 per Year",
            description="Financial benefit of Rs. 6,000 per year is released directly into Aadhaar-seeded bank accounts of farmer families in three equal 4-monthly installments of Rs. 2,000 each.",
            amount=Decimal("6000.00"),
            currency="INR",
            disbursement_frequency=DisbursementFrequency.TRI_ANNUAL,
            order=1,
        )

        # PM-KISAN Documents
        RequiredDocument.objects.filter(scheme=pm_kisan).delete()
        RequiredDocument.objects.bulk_create([
            RequiredDocument(
                scheme=pm_kisan,
                document_name="Aadhaar Card",
                document_type=DocumentType.IDENTITY_PROOF,
                is_mandatory=True,
                description="Mandatory for biometric/OTP e-KYC and DBT transfer.",
                issuing_authority="UIDAI",
                order=1,
            ),
            RequiredDocument(
                scheme=pm_kisan,
                document_name="Land Ownership Record (Khatauni / Land Mutation Copy)",
                document_type=DocumentType.LAND_RECORD,
                is_mandatory=True,
                description="Land record showing owner's name in state revenue land record database.",
                issuing_authority="State Revenue Department",
                order=2,
            ),
            RequiredDocument(
                scheme=pm_kisan,
                document_name="Aadhaar Seeded Active Bank Account Details",
                document_type=DocumentType.BANK_DETAILS,
                is_mandatory=True,
                description="Bank passbook/account linked with NPCI mapper for Direct Benefit Transfer.",
                issuing_authority="Commercial Bank / Post Office",
                order=3,
            ),
        ])

        # PM-KISAN Application Procedure
        ApplicationProcedure.objects.filter(scheme=pm_kisan).delete()
        ApplicationProcedure.objects.bulk_create([
            ApplicationProcedure(
                scheme=pm_kisan,
                mode=ApplicationMode.ONLINE,
                step_number=1,
                title="Self Registration on PM-Kisan Portal",
                description="Visit the Farmers Corner on pmkisan.gov.in, select 'New Farmer Registration', and enter Aadhaar and Mobile number with State selection.",
                portal_url="https://pmkisan.gov.in/RegistrationFormNew.aspx",
                processing_time_days=15,
                fee_inr=Decimal("0.00"),
            ),
            ApplicationProcedure(
                scheme=pm_kisan,
                mode=ApplicationMode.ONLINE,
                step_number=2,
                title="Enter Land and Bank Account Details",
                description="Input Land Record details (Survey/Khata number, Khasra number, land area in Hectares) and upload land ownership proof.",
                processing_time_days=10,
                fee_inr=Decimal("0.00"),
            ),
            ApplicationProcedure(
                scheme=pm_kisan,
                mode=ApplicationMode.HYBRID,
                step_number=3,
                title="State Revenue Authority Verification & e-KYC",
                description="Application is verified by District Nodal Officer / Tehsildar. Complete OTP-based e-KYC on the portal or biometric e-KYC at CSC centre.",
                office_name="Block Agriculture Office / CSC Centre",
                processing_time_days=20,
                fee_inr=Decimal("0.00"),
            ),
        ])

        # PM-KISAN Sources & Version
        SchemeSource.objects.filter(scheme=pm_kisan).delete()
        SchemeSource.objects.create(
            scheme=pm_kisan,
            source_type=SourceType.MINISTRY_GUIDELINE,
            title="PM-KISAN Operational Guidelines Revised 2024",
            url="https://pmkisan.gov.in/Documents/Guidelines.pdf",
            document_reference_number="F.No. 1-1/2020-Credit-II",
            published_date=date(2024, 1, 15),
            is_verified=True,
        )
        SchemeVersion.objects.filter(scheme=pm_kisan).delete()
        SchemeVersion.objects.create(
            scheme=pm_kisan,
            version_number="2024.1",
            change_summary="Mandatory facial authentication e-KYC and land seeding verification integrated with state land record portals.",
            effective_from=date(2024, 1, 1),
            snapshot_data={
                "annual_amount": 6000,
                "installments": 3,
                "mandatory_ekyc": True,
            },
        )

        # ── Scheme 2: Ayushman Bharat PM-JAY ─────────────────────
        pm_jay, _ = GovernmentScheme.objects.get_or_create(
            slug="ayushman-bharat-pradhan-mantri-jan-arogya-yojana-pm-jay",
            defaults={
                "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
                "short_title": "PM-JAY",
                "description": (
                    "Ayushman Bharat PM-JAY is the world's largest health assurance scheme aimed at providing a health cover "
                    "of Rs. 5 lakhs per family per year for secondary and tertiary care hospitalization to over 12 crore poor "
                    "and vulnerable families (approx 55 crore beneficiaries) that form the bottom 40% of the Indian population."
                ),
                "scheme_type": SchemeType.CENTRALLY_SPONSORED,
                "ministry": ministry_objs.get("MoHFW"),
                "department": dept_objs.get("DOHFW"),
                "category": cat_objs.get("healthcare-wellness"),
                "target_beneficiaries": "Families identified as poor, deprived, or occupational categories based on SECC 2011 data.",
                "status": SchemeStatus.ACTIVE,
                "version": "2024.2",
                "launch_date": date(2018, 9, 23),
                "official_application_url": "https://beneficiary.nha.gov.in",
                "official_source_url": "https://nha.gov.in/PM-JAY",
                "funding_pattern": "60:40 Centre:State (90:10 for NE & Himalayan States)",
                "helpline_number": "14555",
                "tags": ["health", "hospital", "insurance", "cashless", "medical", "ayushman card", "bpl"],
            },
        )

        # PM-JAY Rules
        SchemeEligibilityRule.objects.filter(scheme=pm_jay).delete()
        SchemeEligibilityRule.objects.bulk_create([
            SchemeEligibilityRule(
                scheme=pm_jay,
                rule_group=1,
                criterion_key="is_bpl",
                operator=RuleOperator.BOOLEAN_TRUE,
                value="true",
                data_type=RuleDataType.BOOLEAN,
                is_mandatory=False,
                rule_description="Beneficiary is a BPL / Antyodaya ration card holder.",
                order=1,
            ),
            SchemeEligibilityRule(
                scheme=pm_jay,
                rule_group=1,
                criterion_key="annual_income",
                operator=RuleOperator.LTE,
                value="250000.00",
                data_type=RuleDataType.DECIMAL,
                is_mandatory=False,
                rule_description="Annual household income not exceeding Rs. 2,50,000.",
                order=2,
            ),
        ])

        # PM-JAY Benefits
        SchemeBenefit.objects.filter(scheme=pm_jay).delete()
        SchemeBenefit.objects.create(
            scheme=pm_jay,
            benefit_type=BenefitType.INSURANCE_COVER,
            title="Rs. 5,00,000 Cashless Health Assurance per Family per Year",
            description="Comprehensive coverage for over 1,949 medical procedures including pre- and post-hospitalization expenses, diagnostic tests, surgeries, medicines, and ICU charges across all empaneled public and private hospitals.",
            amount=Decimal("500000.00"),
            currency="INR",
            disbursement_frequency=DisbursementFrequency.EVENT_BASED,
            order=1,
        )

        # PM-JAY Documents
        RequiredDocument.objects.filter(scheme=pm_jay).delete()
        RequiredDocument.objects.bulk_create([
            RequiredDocument(
                scheme=pm_jay,
                document_name="Aadhaar Card",
                document_type=DocumentType.IDENTITY_PROOF,
                is_mandatory=True,
                description="Required for identity and biometric card creation.",
                order=1,
            ),
            RequiredDocument(
                scheme=pm_jay,
                document_name="Ration Card / Family ID",
                document_type=DocumentType.ADDRESS_PROOF,
                is_mandatory=True,
                description="To verify family members included in the NFSA/SECC database.",
                order=2,
            ),
        ])

        # PM-JAY Steps
        ApplicationProcedure.objects.filter(scheme=pm_jay).delete()
        ApplicationProcedure.objects.bulk_create([
            ApplicationProcedure(
                scheme=pm_jay,
                mode=ApplicationMode.ONLINE,
                step_number=1,
                title="Check Eligibility on Beneficiary Portal",
                description="Go to beneficiary.nha.gov.in, enter mobile number, verify OTP, and search by Family ID, Aadhaar, or PMJAY ID.",
                portal_url="https://beneficiary.nha.gov.in",
                fee_inr=Decimal("0.00"),
            ),
            ApplicationProcedure(
                scheme=pm_jay,
                mode=ApplicationMode.ONLINE,
                step_number=2,
                title="Complete e-KYC and Generate Ayushman Card",
                description="Perform Aadhaar OTP or Face Auth verification and download the Ayushman Golden Card instantly.",
                fee_inr=Decimal("0.00"),
            ),
        ])

        # ── Scheme 3: Pradhan Mantri Awas Yojana (Gramin) ─────────
        pmay_g, _ = GovernmentScheme.objects.get_or_create(
            slug="pradhan-mantri-awaas-yojana-gramin-pmay-g",
            defaults={
                "name": "Pradhan Mantri Awaas Yojana - Gramin",
                "short_title": "PMAY-G",
                "description": (
                    "PMAY-G aims to provide a pucca house with basic amenities to all rural houseless households and those "
                    "living in kutcha and dilapidated houses. The unit assistance is provided directly to the beneficiary's "
                    "account in installments linked to construction milestones."
                ),
                "scheme_type": SchemeType.CENTRALLY_SPONSORED,
                "ministry": ministry_objs.get("MoRD"),
                "department": dept_objs.get("DoRD"),
                "category": cat_objs.get("housing-shelter"),
                "target_beneficiaries": "Rural houseless families and families living in zero, one, or two-room kutcha houses.",
                "status": SchemeStatus.ACTIVE,
                "version": "2.0",
                "launch_date": date(2016, 11, 20),
                "official_application_url": "https://pmayg.nic.in",
                "official_source_url": "https://pmayg.nic.in",
                "funding_pattern": "60:40 Plain areas, 90:10 Himalayan/NE States",
                "helpline_number": "1800-11-6446",
                "tags": ["housing", "pucca house", "rural", "shelter", "construction grant", "bpl"],
            },
        )

        # PMAY-G Rules
        SchemeEligibilityRule.objects.filter(scheme=pmay_g).delete()
        SchemeEligibilityRule.objects.bulk_create([
            SchemeEligibilityRule(
                scheme=pmay_g,
                rule_group=1,
                criterion_key="is_urban",
                operator=RuleOperator.BOOLEAN_FALSE,
                value="false",
                data_type=RuleDataType.BOOLEAN,
                is_mandatory=True,
                rule_description="Beneficiary must reside in a rural area.",
                order=1,
            ),
            SchemeEligibilityRule(
                scheme=pmay_g,
                rule_group=1,
                criterion_key="is_bpl",
                operator=RuleOperator.BOOLEAN_TRUE,
                value="true",
                data_type=RuleDataType.BOOLEAN,
                is_mandatory=True,
                rule_description="Must be from BPL / SECC deprived household list.",
                order=2,
            ),
        ])

        # PMAY-G Benefits
        SchemeBenefit.objects.filter(scheme=pmay_g).delete()
        SchemeBenefit.objects.create(
            scheme=pmay_g,
            benefit_type=BenefitType.HOUSING_UNIT,
            title="Grant of Rs. 1,20,000 (Plain areas) / Rs. 1,30,000 (Hilly/Difficult areas)",
            description="Financial grant for construction of minimum 25 sq.m pucca house with dedicated toilet and clean cooking space, disbursed in 3 construction milestones.",
            amount=Decimal("120000.00"),
            currency="INR",
            disbursement_frequency=DisbursementFrequency.MILESTONE_BASED,
            order=1,
        )

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Successfully seeded Government Scheme Data Management System!"))
