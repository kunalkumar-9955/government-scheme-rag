"""
apps/schemes/models.py — Government Scheme Data Management System

Models:
1. State
2. Ministry
3. Department
4. SchemeCategory
5. GovernmentScheme
6. SchemeEligibilityRule
7. SchemeBenefit
8. RequiredDocument
9. ApplicationProcedure
10. SchemeSource
11. SchemeVersion
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify


# ─────────────────────────────────────────────────────────────
# 1. State / Union Territory Model
# ─────────────────────────────────────────────────────────────
class State(models.Model):
    """Normalized table for Indian States and Union Territories."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True, db_index=True, help_text="e.g. UP, MH, DL, KA")
    name = models.CharField(max_length=100, unique=True, db_index=True, help_text="e.g. Uttar Pradesh, Delhi")
    is_union_territory = models.BooleanField(default=False)
    official_portal_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheme_states"
        ordering = ["name"]
        verbose_name = "State / UT"
        verbose_name_plural = "States & UTs"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ─────────────────────────────────────────────────────────────
# 2. Ministry Model
# ─────────────────────────────────────────────────────────────
class Ministry(models.Model):
    """Central or State Ministry / Department-level authority."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300, unique=True, db_index=True, help_text="e.g. Ministry of Agriculture and Farmers Welfare")
    short_code = models.CharField(max_length=50, blank=True, help_text="e.g. MoA&FW, MoHFW, MoE")
    website_url = models.URLField(max_length=500, blank=True)
    is_central = models.BooleanField(default=True, help_text="True for Central Ministries, False for State Ministries")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="ministries", help_text="Specified if state-level ministry")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheme_ministries"
        ordering = ["name"]
        verbose_name = "Ministry"
        verbose_name_plural = "Ministries"

    def __str__(self):
        return f"{self.name}{f' ({self.short_code})' if self.short_code else ''}"


# ─────────────────────────────────────────────────────────────
# 3. Department Model
# ─────────────────────────────────────────────────────────────
class Department(models.Model):
    """Department operating under a specific Ministry."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=300, db_index=True, help_text="e.g. Department of Agricultural Research and Education")
    short_code = models.CharField(max_length=50, blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheme_departments"
        ordering = ["ministry", "name"]
        unique_together = [("ministry", "name")]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.name} ({self.ministry.short_code or self.ministry.name})"


# ─────────────────────────────────────────────────────────────
# 4. Scheme Category Model
# ─────────────────────────────────────────────────────────────
class SchemeCategory(models.Model):
    """Categorization for schemes (Agriculture, Education, Healthcare, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True, db_index=True)
    slug = models.SlugField(max_length=150, unique=True, db_index=True)
    icon = models.CharField(max_length=50, blank=True, help_text="e.g. 🌾, 🎓, 🏥, or icon class name")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheme_categories"
        ordering = ["name"]
        verbose_name = "Scheme Category"
        verbose_name_plural = "Scheme Categories"

    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────
# 5. Government Scheme Model
# ─────────────────────────────────────────────────────────────
class SchemeType(models.TextChoices):
    CENTRAL_SECTOR = "CENTRAL_SECTOR", "Central Sector Scheme (100% Central)"
    CENTRALLY_SPONSORED = "CENTRALLY_SPONSORED", "Centrally Sponsored Scheme (Cost Shared)"
    STATE_GOVERNMENT = "STATE_GOVERNMENT", "State Government Scheme"
    UT_ADMINISTRATION = "UT_ADMINISTRATION", "Union Territory Scheme"
    PUBLIC_PRIVATE = "PUBLIC_PRIVATE", "Public-Private Partnership"


class SchemeStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active / Accepting Applications"
    INACTIVE = "INACTIVE", "Temporarily Inactive"
    UPCOMING = "UPCOMING", "Announced / Upcoming"
    DISCONTINUED = "DISCONTINUED", "Discontinued"
    MERGED = "MERGED", "Merged into Another Scheme"


class GovernmentScheme(models.Model):
    """Central master model for all official Government Schemes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500, db_index=True, help_text="Official name of scheme")
    slug = models.SlugField(max_length=500, unique=True, db_index=True)
    short_title = models.CharField(max_length=100, blank=True, db_index=True, help_text="e.g. PM-KISAN, PMAY-G")
    description = models.TextField(help_text="Detailed overview and objectives of the scheme")

    # Classification & Hierarchy
    scheme_type = models.CharField(max_length=30, choices=SchemeType.choices, default=SchemeType.CENTRAL_SECTOR, db_index=True)
    ministry = models.ForeignKey(Ministry, on_delete=models.SET_NULL, null=True, blank=True, related_name="schemes", db_index=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="schemes")
    category = models.ForeignKey(SchemeCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="schemes", db_index=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="schemes", help_text="Specified for state-specific schemes, Null for Pan-India schemes")

    # Beneficiary & Status
    target_beneficiaries = models.TextField(blank=True, help_text="Target group summary (e.g. Small & Marginal farmers, SC/ST students)")
    status = models.CharField(max_length=20, choices=SchemeStatus.choices, default=SchemeStatus.ACTIVE, db_index=True)
    version = models.CharField(max_length=20, default="1.0", help_text="Current scheme version")

    # Key Dates & URLs
    launch_date = models.DateField(null=True, blank=True)
    valid_upto = models.DateField(null=True, blank=True, help_text="Scheme sunset date or fiscal end date")
    important_dates = models.JSONField(default=dict, blank=True, help_text="Dictionary of milestones, deadlines, and cycles")
    official_application_url = models.URLField(max_length=1000, blank=True)
    official_source_url = models.URLField(max_length=1000, blank=True)
    funding_pattern = models.CharField(max_length=200, blank=True, help_text="e.g. 100% Central, 60:40 Centre:State")
    helpline_number = models.CharField(max_length=100, blank=True)

    # Keywords & Metadata
    tags = models.JSONField(default=list, blank=True, help_text="List of keywords for semantic and sparse discovery")
    last_updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "government_schemes"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "scheme_type"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["state", "status"]),
        ]
        verbose_name = "Government Scheme"
        verbose_name_plural = "Government Schemes"

    def __str__(self):
        if self.short_title:
            return f"{self.short_title} — {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.short_title or self.name)[:450]
            unique_slug = base_slug
            counter = 1
            while GovernmentScheme.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────
# 6. Scheme Eligibility Rule Model (Structured for Programmatic Eval)
# ─────────────────────────────────────────────────────────────
class RuleOperator(models.TextChoices):
    EQUALS = "EQUALS", "Equals (==)"
    NOT_EQUALS = "NOT_EQUALS", "Not Equals (!=)"
    GREATER_THAN = "GREATER_THAN", "Greater Than (>)"
    LESS_THAN = "LESS_THAN", "Less Than (<)"
    GTE = "GTE", "Greater Than or Equal (>=)"
    LTE = "LTE", "Less Than or Equal (<=)"
    IN_LIST = "IN_LIST", "In List (Any of)"
    NOT_IN_LIST = "NOT_IN_LIST", "Not In List"
    CONTAINS = "CONTAINS", "Contains Substring"
    BOOLEAN_TRUE = "BOOLEAN_TRUE", "Must Be True"
    BOOLEAN_FALSE = "BOOLEAN_FALSE", "Must Be False"
    BETWEEN = "BETWEEN", "Between Min and Max"
    EXISTS = "EXISTS", "Field Must Exist / Be Provided"


class RuleDataType(models.TextChoices):
    INTEGER = "INTEGER", "Integer Number"
    DECIMAL = "DECIMAL", "Decimal / Currency"
    STRING = "STRING", "Text String / Code"
    BOOLEAN = "BOOLEAN", "Boolean (True/False)"
    DATE = "DATE", "Date (YYYY-MM-DD)"
    LIST = "LIST", "List / Array of Values"


class SchemeEligibilityRule(models.Model):
    """Structured eligibility condition for programmatic evaluation against User Profile."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="eligibility_rules")
    rule_group = models.PositiveIntegerField(
        default=1,
        help_text="Rules within the same group are combined with AND. Separate groups are combined with OR.",
    )
    criterion_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Maps to UserProfile fields (e.g. age, annual_income, state, social_category, is_bpl, occupation, land_holding_acres, has_disability, gender, education_level, is_student)",
    )
    operator = models.CharField(max_length=25, choices=RuleOperator.choices, default=RuleOperator.EQUALS)
    value = models.CharField(max_length=500, blank=True, help_text="Target value for single-value comparisons or comma-separated list")
    min_value = models.CharField(max_length=100, null=True, blank=True, help_text="Lower bound for BETWEEN operator")
    max_value = models.CharField(max_length=100, null=True, blank=True, help_text="Upper bound for BETWEEN operator")
    data_type = models.CharField(max_length=15, choices=RuleDataType.choices, default=RuleDataType.STRING)
    is_mandatory = models.BooleanField(default=True, help_text="If mandatory, failing this rule disqualifies the applicant")
    disqualification_condition = models.BooleanField(
        default=False,
        help_text="If True, matching this condition DISQUALIFIES the applicant (e.g. Income tax payers ineligible)",
    )
    rule_description = models.TextField(help_text="Human-readable explanation of this criteria")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "scheme_eligibility_rules"
        ordering = ["rule_group", "order"]
        verbose_name = "Eligibility Rule"
        verbose_name_plural = "Eligibility Rules"

    def __str__(self):
        op_str = f"BETWEEN {self.min_value} AND {self.max_value}" if self.operator == RuleOperator.BETWEEN else f"{self.operator} {self.value}"
        return f"{self.scheme.short_title or self.scheme.name}: {self.criterion_key} {op_str}"


# ─────────────────────────────────────────────────────────────
# 7. Scheme Benefit Model
# ─────────────────────────────────────────────────────────────
class BenefitType(models.TextChoices):
    DIRECT_BENEFIT_TRANSFER = "DIRECT_BENEFIT_TRANSFER", "Direct Benefit Transfer (DBT Cash)"
    SUBSIDY = "SUBSIDY", "Financial Subsidy / Grant"
    LOAN_CREDIT = "LOAN_CREDIT", "Concessional Loan / Credit Support"
    INSURANCE_COVER = "INSURANCE_COVER", "Health / Life / Crop Insurance"
    SCHOLARSHIP = "SCHOLARSHIP", "Educational Scholarship / Stipend"
    IN_KIND_GOODS = "IN_KIND_GOODS", "In-Kind Goods / Equipment / Ration"
    PENSION = "PENSION", "Monthly Social Security Pension"
    TRAINING_SKILL = "TRAINING_SKILL", "Skill Training & Certification"
    TAX_EXEMPTION = "TAX_EXEMPTION", "Tax Exemption / Rebate"
    HOUSING_UNIT = "HOUSING_UNIT", "Pucca House / Shelter Construction"
    OTHER = "OTHER", "Other Non-Financial / Advisory Benefit"


class DisbursementFrequency(models.TextChoices):
    ONE_TIME = "ONE_TIME", "One-Time Grant"
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly (4 installments/year)"
    TRI_ANNUAL = "TRI_ANNUAL", "Every 4 Months (3 installments/year e.g. PM-Kisan)"
    ANNUAL = "ANNUAL", "Annual"
    MILESTONE_BASED = "MILESTONE_BASED", "Linked to Construction / Course Milestones"
    EVENT_BASED = "EVENT_BASED", "Upon Occurrence of Event (e.g. Hospitalization, Calamity)"


class SchemeBenefit(models.Model):
    """Tangible financial or service benefit provided under a scheme."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="benefits")
    benefit_type = models.CharField(max_length=30, choices=BenefitType.choices, default=BenefitType.DIRECT_BENEFIT_TRANSFER)
    title = models.CharField(max_length=300, help_text="e.g. ₹6,000 per year in 3 equal installments of ₹2,000")
    description = models.TextField(blank=True, help_text="Detailed coverage, terms, and caps")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Direct monetary amount in INR (if applicable)")
    currency = models.CharField(max_length=10, default="INR")
    disbursement_frequency = models.CharField(max_length=20, choices=DisbursementFrequency.choices, default=DisbursementFrequency.ONE_TIME)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "scheme_benefits"
        ordering = ["order"]
        verbose_name = "Scheme Benefit"
        verbose_name_plural = "Scheme Benefits"

    def __str__(self):
        return f"{self.scheme.short_title or self.scheme.name}: {self.title}"


# ─────────────────────────────────────────────────────────────
# 8. Required Document Model
# ─────────────────────────────────────────────────────────────
class DocumentType(models.TextChoices):
    IDENTITY_PROOF = "IDENTITY_PROOF", "Identity Proof (Aadhaar, Voter ID, Passport)"
    ADDRESS_PROOF = "ADDRESS_PROOF", "Proof of Address (Electricity Bill, Ration Card)"
    INCOME_PROOF = "INCOME_PROOF", "Income Certificate / Salary Slip"
    CASTE_PROOF = "CASTE_PROOF", "Caste / Category Certificate (SC/ST/OBC/EWS)"
    LAND_RECORD = "LAND_RECORD", "Land Ownership Record / Khasra-Khatauni"
    BANK_DETAILS = "BANK_DETAILS", "Bank Account Passbook / Cancelled Cheque (Aadhaar Seeded)"
    EDUCATIONAL_CERTIFICATE = "EDUCATIONAL_CERTIFICATE", "Marksheet / Degree / Enrollment Proof"
    DISABILITY_CERTIFICATE = "DISABILITY_CERTIFICATE", "UDID / Disability Medical Certificate"
    AGE_PROOF = "AGE_PROOF", "Birth Certificate / 10th Certificate"
    PASSPORT_PHOTO = "PASSPORT_PHOTO", "Passport Size Photographs"
    OTHER = "OTHER", "Other Scheme Specific Affidavit / Undertaking"


class RequiredDocument(models.Model):
    """Mandatory or optional documentation needed to apply for a scheme."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="required_documents")
    document_name = models.CharField(max_length=300, help_text="e.g. Aadhaar Card (Mobile Linked)")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.IDENTITY_PROOF)
    is_mandatory = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text="Details such as self-attestation, validity period, or issuing department")
    issuing_authority = models.CharField(max_length=200, blank=True, help_text="e.g. UIDAI, Revenue Department / Tehsildar, Commercial Bank")
    accepted_formats = models.CharField(max_length=100, default="PDF, JPG, PNG", blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "scheme_required_documents"
        ordering = ["order"]
        verbose_name = "Required Document"
        verbose_name_plural = "Required Documents"

    def __str__(self):
        return f"{self.scheme.short_title or self.scheme.name}: {self.document_name}"


# ─────────────────────────────────────────────────────────────
# 9. Application Procedure Model
# ─────────────────────────────────────────────────────────────
class ApplicationMode(models.TextChoices):
    ONLINE = "ONLINE", "Online Application Portal"
    OFFLINE = "OFFLINE", "Offline Submission at Government Office"
    HYBRID = "HYBRID", "Online Registration + Physical Document Verification"
    CSC_PORTAL = "CSC_PORTAL", "Common Service Centre (CSC) / Village Level Entrepreneur"


class ApplicationProcedure(models.Model):
    """Step-by-step procedural guideline for scheme application submission."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="application_steps")
    mode = models.CharField(max_length=20, choices=ApplicationMode.choices, default=ApplicationMode.ONLINE)
    step_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=300, help_text="e.g. Step 1: Online Farmer Registration")
    description = models.TextField(help_text="Clear action steps to complete this stage")
    portal_url = models.URLField(max_length=1000, blank=True, help_text="Direct link for this application stage")
    office_name = models.CharField(max_length=300, blank=True, help_text="Designated office if offline (e.g. Block Agriculture Office, District Welfare Officer)")
    processing_time_days = models.PositiveIntegerField(null=True, blank=True, help_text="Expected processing & approval turnaround in days")
    fee_inr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Application / Processing fee (0 if free)")

    class Meta:
        db_table = "scheme_application_steps"
        ordering = ["step_number"]
        unique_together = [("scheme", "step_number")]
        verbose_name = "Application Step"
        verbose_name_plural = "Application Steps"

    def __str__(self):
        return f"{self.scheme.short_title or self.scheme.name} — Step {self.step_number}: {self.title}"


# ─────────────────────────────────────────────────────────────
# 10. Scheme Source / Citation Reference Model
# ─────────────────────────────────────────────────────────────
class SourceType(models.TextChoices):
    OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE", "Official Gazette Notification"
    MINISTRY_GUIDELINE = "MINISTRY_GUIDELINE", "Ministry Operational Guidelines"
    PORTAL_WEBPAGE = "PORTAL_WEBPAGE", "Official Government Portal Webpage"
    PRESS_RELEASE = "PRESS_RELEASE", "PIB / Official Press Release"
    ACT_ORDINANCE = "ACT_ORDINANCE", "Parliamentary / State Legislative Act"
    SCHEME_BROCHURE = "SCHEME_BROCHURE", "Official Citizen Brochure / FAQ"


class SchemeSource(models.Model):
    """Source grounding reference verifying official authenticity of the scheme data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=30, choices=SourceType.choices, default=SourceType.MINISTRY_GUIDELINE)
    title = models.CharField(max_length=300, help_text="e.g. Operational Guidelines of PM-KISAN Scheme (Revised 2024)")
    url = models.URLField(max_length=1000, help_text="Official direct document link or portal URL")
    document_reference_number = models.CharField(max_length=200, blank=True, help_text="e.g. F.No. 1-1/2020-Credit-II")
    published_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scheme_sources"
        ordering = ["-retrieved_at"]
        verbose_name = "Scheme Source / Citation"
        verbose_name_plural = "Scheme Sources / Citations"

    def __str__(self):
        return f"{self.scheme.short_title or self.scheme.name} source: {self.title}"


# ─────────────────────────────────────────────────────────────
# 11. Scheme Version Tracking Model
# ─────────────────────────────────────────────────────────────
class SchemeVersion(models.Model):
    """Audit and version history tracking amendments to scheme criteria and benefits over time."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.CASCADE, related_name="versions")
    version_number = models.CharField(max_length=50, help_text="e.g. 1.0, 2.0, 2024-R1")
    change_summary = models.TextField(help_text="Key changes introduced in this revision")
    effective_from = models.DateField(help_text="Start date of this revision")
    effective_to = models.DateField(null=True, blank=True, help_text="End date (null if current active version)")
    snapshot_data = models.JSONField(
        default=dict,
        help_text="Complete structured snapshot (rules, benefits, documents, application steps) at this version",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheme_version_edits",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scheme_versions"
        ordering = ["-created_at"]
        unique_together = [("scheme", "version_number")]
        verbose_name = "Scheme Version"
        verbose_name_plural = "Scheme Versions"

    def __str__(self):
        return f"{self.scheme.short_title or self.scheme.name} v{self.version_number}"
