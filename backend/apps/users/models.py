"""
apps/users/models.py — User profile with demographic data for eligibility evaluation
"""
import uuid
from django.db import models
from django.conf import settings
from core.utils import indian_states


class EducationLevel(models.TextChoices):
    NO_FORMAL = "NO_FORMAL", "No Formal Education"
    PRIMARY = "PRIMARY", "Primary (Class 1-5)"
    MIDDLE = "MIDDLE", "Middle (Class 6-8)"
    SECONDARY = "SECONDARY", "Secondary (Class 9-10)"
    HIGHER_SECONDARY = "HIGHER_SECONDARY", "Higher Secondary (Class 11-12)"
    DIPLOMA = "DIPLOMA", "Diploma / ITI"
    GRADUATE = "GRADUATE", "Graduate (UG)"
    POST_GRADUATE = "POST_GRADUATE", "Post Graduate (PG)"
    DOCTORATE = "DOCTORATE", "Doctorate / PhD"


class OccupationCategory(models.TextChoices):
    FARMER = "FARMER", "Farmer / Agricultural Worker"
    AGRICULTURAL_LABORER = "AGRICULTURAL_LABORER", "Agricultural Laborer"
    SELF_EMPLOYED = "SELF_EMPLOYED", "Self-Employed / Business"
    PRIVATE_EMPLOYEE = "PRIVATE_EMPLOYEE", "Private Sector Employee"
    GOVERNMENT_EMPLOYEE = "GOVERNMENT_EMPLOYEE", "Government Employee"
    UNEMPLOYED = "UNEMPLOYED", "Unemployed"
    STUDENT = "STUDENT", "Student"
    HOMEMAKER = "HOMEMAKER", "Homemaker"
    DAILY_WAGER = "DAILY_WAGER", "Daily Wager"
    ARTISAN = "ARTISAN", "Artisan / Craftsperson"
    RETIRED = "RETIRED", "Retired"
    OTHER = "OTHER", "Other"


class SocialCategory(models.TextChoices):
    GENERAL = "GENERAL", "General"
    OBC = "OBC", "Other Backward Class (OBC)"
    SC = "SC", "Scheduled Caste (SC)"
    ST = "ST", "Scheduled Tribe (ST)"
    EWS = "EWS", "Economically Weaker Section (EWS)"


class UserProfile(models.Model):
    """
    Detailed user profile for eligibility matching against government schemes.
    Every field maps to potential eligibility criteria in scheme documents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # ── Personal Information ──
    full_name = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other / Prefer not to say")],
        blank=True,
    )

    # ── Location ──
    state = models.CharField(
        max_length=3,
        choices=indian_states(),
        blank=True,
        db_index=True,
    )
    district = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    is_urban = models.BooleanField(null=True, blank=True, help_text="True = Urban, False = Rural")

    # ── Social / Economic Status ──
    social_category = models.CharField(
        max_length=10,
        choices=SocialCategory.choices,
        blank=True,
        db_index=True,
    )
    annual_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual household income in INR",
    )
    is_bpl = models.BooleanField(
        default=False,
        verbose_name="Below Poverty Line",
        help_text="Is the user a BPL cardholder?",
    )
    has_ration_card = models.BooleanField(default=False)
    ration_card_type = models.CharField(
        max_length=10,
        choices=[("APL", "APL"), ("BPL", "BPL"), ("AAY", "AAY (Antyodaya)")],
        blank=True,
    )

    # ── Occupation & Education ──
    occupation = models.CharField(
        max_length=30,
        choices=OccupationCategory.choices,
        blank=True,
        db_index=True,
    )
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        blank=True,
    )
    is_student = models.BooleanField(default=False)
    institution_name = models.CharField(max_length=255, blank=True)

    # ── Special Categories ──
    has_disability = models.BooleanField(default=False)
    disability_percentage = models.IntegerField(
        null=True, blank=True, help_text="Disability percentage (0-100)"
    )
    is_ex_serviceman = models.BooleanField(default=False)
    is_minority = models.BooleanField(default=False)
    is_widow = models.BooleanField(default=False)
    is_single_girl_child = models.BooleanField(default=False)

    # ── Agriculture (if farmer) ──
    land_holding_acres = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Agricultural land holding in acres",
    )
    is_marginal_farmer = models.BooleanField(default=False, help_text="< 1 hectare")
    is_small_farmer = models.BooleanField(default=False, help_text="1–2 hectares")

    # ── Family ──
    family_size = models.IntegerField(null=True, blank=True)
    number_of_children = models.IntegerField(null=True, blank=True)
    is_female_headed_household = models.BooleanField(default=False)

    # ── Flexible extension field ──
    additional_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible JSON for any scheme-specific attributes",
    )

    # ── Profile Completion ──
    profile_completion_score = models.IntegerField(default=0, help_text="0–100 completion score")

    # ── Timestamps ──
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile of {self.user.email}"

    def calculate_completion_score(self) -> int:
        """
        Calculate profile completion score (0–100).
        Higher score = better eligibility matching accuracy.
        """
        fields_and_weights = [
            ("full_name", 5),
            ("date_of_birth", 10),
            ("gender", 5),
            ("state", 10),
            ("district", 5),
            ("social_category", 10),
            ("annual_income", 15),
            ("occupation", 10),
            ("education_level", 5),
            ("family_size", 5),
            ("is_bpl", 10),
            ("pincode", 5),
            ("is_urban", 5),
        ]
        score = 0
        for field, weight in fields_and_weights:
            val = getattr(self, field)
            if val not in [None, "", False, 0]:
                score += weight
        return min(score, 100)

    def save(self, *args, **kwargs):
        self.profile_completion_score = self.calculate_completion_score()
        super().save(*args, **kwargs)

    def to_eligibility_context(self) -> dict:
        """
        Return profile as a structured dict for injecting into RAG prompts
        and eligibility evaluation.
        """
        from datetime import date
        age = None
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )

        state_display = dict(indian_states()).get(self.state, self.state)

        return {
            "full_name": self.full_name or "Not provided",
            "age": age,
            "gender": self.gender,
            "state": state_display,
            "state_code": self.state,
            "district": self.district,
            "is_urban": self.is_urban,
            "social_category": self.social_category,
            "annual_income_inr": float(self.annual_income) if self.annual_income else None,
            "is_bpl": self.is_bpl,
            "ration_card_type": self.ration_card_type,
            "occupation": self.occupation,
            "education_level": self.education_level,
            "is_student": self.is_student,
            "has_disability": self.has_disability,
            "disability_percentage": self.disability_percentage,
            "is_ex_serviceman": self.is_ex_serviceman,
            "is_minority": self.is_minority,
            "is_widow": self.is_widow,
            "land_holding_acres": float(self.land_holding_acres) if self.land_holding_acres else None,
            "is_marginal_farmer": self.is_marginal_farmer,
            "is_small_farmer": self.is_small_farmer,
            "family_size": self.family_size,
            "number_of_children": self.number_of_children,
            "profile_completion_score": self.profile_completion_score,
            "additional_attributes": self.additional_attributes,
        }
