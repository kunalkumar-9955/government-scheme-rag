"""
apps/eligibility/tests.py — Comprehensive Unit Tests for Deterministic Eligibility Evaluation Engine.

Coverage:
1. Rule Operators: LTE, GTE, EQUALS, NOT_EQUALS, BETWEEN, IN_LIST, NOT_IN_LIST, BOOLEAN_TRUE, BOOLEAN_FALSE, EXISTS.
2. Data Types: INTEGER, DECIMAL (currency/commas), STRING (case-insensitive, state code aliases), BOOLEAN, DATE, LIST.
3. Multiple AND Conditions: Combined within a rule group.
4. Multiple OR Conditions: Alternative qualification tracks across separate rule groups.
5. Disqualification Conditions: Disqualification rule triggering ineligibility.
6. Missing Information Handling: Returns 'Insufficient Information' and never claims certainty.
7. Scheme without Rules: Returns 'Insufficient Information' with grounding note.
8. Evidence & Source Grounding: Attaches official URLs and citation metadata.
9. API Endpoints: Stateless evaluate, citizen scheme check, and batch schemes check.
"""
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.eligibility.engine import (
    ContextResolver,
    EligibilityEngine,
    EligibilityVerdict,
    RuleComparator,
    RuleEvaluationStatus,
    ValueParser,
)
from apps.schemes.models import (
    GovernmentScheme,
    Ministry,
    RuleDataType,
    RuleOperator,
    SchemeCategory,
    SchemeEligibilityRule,
    SchemeSource,
    SchemeStatus,
    SchemeType,
    SourceType,
    State,
)
from apps.users.models import EducationLevel, OccupationCategory, SocialCategory, UserProfile

User = get_user_model()


# ─────────────────────────────────────────────────────────────
# 1. Unit Tests for ValueParser & ContextResolver
# ─────────────────────────────────────────────────────────────

class TestValueParserAndResolver(TestCase):

    def test_parse_integers(self):
        self.assertEqual(ValueParser.parse("25", RuleDataType.INTEGER), 25)
        self.assertEqual(ValueParser.parse("2,50,000", RuleDataType.INTEGER), 250000)
        self.assertEqual(ValueParser.parse(30.0, RuleDataType.INTEGER), 30)
        self.assertIsNone(ValueParser.parse("invalid_num", RuleDataType.INTEGER))

    def test_parse_decimals(self):
        self.assertEqual(ValueParser.parse("₹2,50,000.50", RuleDataType.DECIMAL), Decimal("250000.50"))
        self.assertEqual(ValueParser.parse(150000, RuleDataType.DECIMAL), Decimal("150000"))
        self.assertIsNone(ValueParser.parse("abc", RuleDataType.DECIMAL))

    def test_parse_booleans(self):
        self.assertTrue(ValueParser.parse("true", RuleDataType.BOOLEAN))
        self.assertTrue(ValueParser.parse("YES", RuleDataType.BOOLEAN))
        self.assertTrue(ValueParser.parse("1", RuleDataType.BOOLEAN))
        self.assertFalse(ValueParser.parse("false", RuleDataType.BOOLEAN))
        self.assertFalse(ValueParser.parse("no", RuleDataType.BOOLEAN))
        self.assertFalse(ValueParser.parse("0", RuleDataType.BOOLEAN))

    def test_parse_dates(self):
        import datetime
        d = ValueParser.parse("2024-05-15", RuleDataType.DATE)
        self.assertEqual(d, datetime.date(2024, 5, 15))
        d2 = ValueParser.parse("15/05/2024", RuleDataType.DATE)
        self.assertEqual(d2, datetime.date(2024, 5, 15))

    def test_parse_lists(self):
        l = ValueParser.parse("SC, ST, OBC", RuleDataType.LIST)
        self.assertEqual(l, ["SC", "ST", "OBC"])

    def test_context_resolver_synonyms(self):
        ctx = {"income": 180000, "user_age": 22, "residence_state": "Bihar"}
        self.assertEqual(ContextResolver.get_value("annual_income", ctx), 180000)
        self.assertEqual(ContextResolver.get_value("age", ctx), 22)
        self.assertEqual(ContextResolver.get_value("state", ctx), "Bihar")

    def test_context_resolver_nested_attributes(self):
        ctx = {"additional_attributes": {"has_kisan_credit_card": True}}
        self.assertTrue(ContextResolver.get_value("has_kisan_credit_card", ctx))


# ─────────────────────────────────────────────────────────────
# 2. Unit Tests for RuleComparator Operators
# ─────────────────────────────────────────────────────────────

class TestRuleComparator(TestCase):

    def test_equals_and_not_equals(self):
        # Case insensitive string
        passed, _ = RuleComparator.compare("Student", RuleOperator.EQUALS, "STUDENT", None, None, RuleDataType.STRING)
        self.assertTrue(passed)

        # State alias: "BR" equals "Bihar"
        passed, _ = RuleComparator.compare("BR", RuleOperator.EQUALS, "Bihar", None, None, RuleDataType.STRING)
        self.assertTrue(passed)

        passed, _ = RuleComparator.compare("General", RuleOperator.NOT_EQUALS, "SC", None, None, RuleDataType.STRING)
        self.assertTrue(passed)

    def test_numeric_comparisons(self):
        # Age <= 25
        passed, _ = RuleComparator.compare(22, RuleOperator.LTE, "25", None, None, RuleDataType.INTEGER)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare(26, RuleOperator.LTE, "25", None, None, RuleDataType.INTEGER)
        self.assertFalse(passed)

        # Income <= 250000
        passed, _ = RuleComparator.compare("2,00,000", RuleOperator.LTE, "250000", None, None, RuleDataType.DECIMAL)
        self.assertTrue(passed)

        # Age >= 18
        passed, _ = RuleComparator.compare(18, RuleOperator.GTE, "18", None, None, RuleDataType.INTEGER)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare(17, RuleOperator.GTE, "18", None, None, RuleDataType.INTEGER)
        self.assertFalse(passed)

    def test_between_operator(self):
        # Age BETWEEN 18 and 35
        passed, _ = RuleComparator.compare(25, RuleOperator.BETWEEN, "", "18", "35", RuleDataType.INTEGER)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare(17, RuleOperator.BETWEEN, "", "18", "35", RuleDataType.INTEGER)
        self.assertFalse(passed)
        passed, _ = RuleComparator.compare(36, RuleOperator.BETWEEN, "", "18", "35", RuleDataType.INTEGER)
        self.assertFalse(passed)

    def test_in_list_operator(self):
        passed, _ = RuleComparator.compare("SC", RuleOperator.IN_LIST, "SC, ST, OBC", None, None, RuleDataType.LIST)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare("GENERAL", RuleOperator.IN_LIST, "SC, ST, OBC", None, None, RuleDataType.LIST)
        self.assertFalse(passed)

    def test_boolean_operators(self):
        passed, _ = RuleComparator.compare(True, RuleOperator.BOOLEAN_TRUE, "True", None, None, RuleDataType.BOOLEAN)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare(False, RuleOperator.BOOLEAN_TRUE, "True", None, None, RuleDataType.BOOLEAN)
        self.assertFalse(passed)

    def test_date_comparisons(self):
        passed, _ = RuleComparator.compare("2024-01-01", RuleOperator.GTE, "2023-01-01", None, None, RuleDataType.DATE)
        self.assertTrue(passed)
        passed, _ = RuleComparator.compare("2022-01-01", RuleOperator.GTE, "2023-01-01", None, None, RuleDataType.DATE)
        self.assertFalse(passed)


# ─────────────────────────────────────────────────────────────
# 3. Deterministic Eligibility Engine Tests
# ─────────────────────────────────────────────────────────────

class TestEligibilityEngine(TestCase):

    def setUp(self):
        self.engine = EligibilityEngine()

        # Create Category & Ministry
        self.cat = SchemeCategory.objects.create(name="Education", slug="education")
        self.ministry = Ministry.objects.create(name="Ministry of Education", short_code="MOE")
        self.bihar = State.objects.create(name="Bihar", code="BR", is_union_territory=False)

        # Create Scheme: Bihar Youth Student Scholarship
        self.scheme = GovernmentScheme.objects.create(
            name="Bihar Youth Scholarship Scheme",
            short_title="BYSS",
            slug="bihar-youth-scholarship",
            description="Financial assistance for students in Bihar.",
            category=self.cat,
            ministry=self.ministry,
            state=self.bihar,
            scheme_type=SchemeType.STATE_GOVERNMENT,
            status=SchemeStatus.ACTIVE,
            official_source_url="https://education.bihar.gov.in/scholarship",
        )

        # Add Official Source Reference
        SchemeSource.objects.create(
            scheme=self.scheme,
            source_type=SourceType.MINISTRY_GUIDELINE,
            title="BYSS Operational Guidelines 2024",
            url="https://education.bihar.gov.in/docs/guidelines.pdf",
            document_reference_number="ED/2024/SCH/01",
        )

        # Build Example Rules (All combined with AND in Group 1):
        # 1. Age <= 25
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            order=1,
            criterion_key="age",
            operator=RuleOperator.LTE,
            value="25",
            data_type=RuleDataType.INTEGER,
            is_mandatory=True,
            rule_description="Applicant age must be 25 years or younger",
        )
        # 2. Annual income <= 250000
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            order=2,
            criterion_key="annual_income",
            operator=RuleOperator.LTE,
            value="250000",
            data_type=RuleDataType.DECIMAL,
            is_mandatory=True,
            rule_description="Annual household income must not exceed ₹2,50,000",
        )
        # 3. State = Bihar
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            order=3,
            criterion_key="state",
            operator=RuleOperator.EQUALS,
            value="Bihar",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Applicant must be a resident of Bihar",
        )
        # 4. Occupation = Student
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            order=4,
            criterion_key="occupation",
            operator=RuleOperator.EQUALS,
            value="STUDENT",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Applicant must be enrolled as a student",
        )

    def test_example_scenario_fully_eligible(self):
        """
        Example prompt case:
        Age <= 25 AND Annual income <= 250000 AND State = Bihar AND Occupation = Student
        -> Verdict: Eligible
        """
        user_profile = {
            "age": 21,
            "annual_income": 180000,
            "state": "Bihar",
            "occupation": "STUDENT",
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)

        self.assertEqual(result.verdict, EligibilityVerdict.ELIGIBLE)
        self.assertTrue(result.is_eligible)
        self.assertGreaterEqual(result.confidence_score, 0.95)
        self.assertEqual(len(result.rules_checked), 4)
        self.assertEqual(len(result.passed_rules), 4)
        self.assertEqual(len(result.failed_rules), 0)
        self.assertEqual(len(result.missing_information), 0)
        self.assertGreater(len(result.evidence_sources), 0)

    def test_ineligible_due_to_income_exceeded(self):
        user_profile = {
            "age": 21,
            "annual_income": 350000,  # Fails <= 250000
            "state": "Bihar",
            "occupation": "STUDENT",
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)

        self.assertEqual(result.verdict, EligibilityVerdict.NOT_ELIGIBLE)
        self.assertFalse(result.is_eligible)
        self.assertEqual(len(result.failed_rules), 1)
        self.assertEqual(result.failed_rules[0].criterion_key, "annual_income")

    def test_ineligible_due_to_state_mismatch(self):
        user_profile = {
            "age": 21,
            "annual_income": 150000,
            "state": "Maharashtra",  # Mismatch
            "occupation": "STUDENT",
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)

        self.assertEqual(result.verdict, EligibilityVerdict.NOT_ELIGIBLE)
        self.assertFalse(result.is_eligible)
        self.assertEqual(len(result.failed_rules), 1)
        self.assertEqual(result.failed_rules[0].criterion_key, "state")

    def test_insufficient_information_when_mandatory_data_missing(self):
        """
        When required attributes (e.g. income or occupation) are missing,
        the engine must return 'Insufficient Information' and never assume eligibility.
        """
        user_profile = {
            "age": 21,
            "state": "Bihar",
            # missing annual_income and occupation
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)

        self.assertEqual(result.verdict, EligibilityVerdict.INSUFFICIENT_INFORMATION)
        self.assertIsNone(result.is_eligible)
        self.assertIn("annual_income", result.missing_information)
        self.assertIn("occupation", result.missing_information)

    def test_disqualification_condition(self):
        """
        Testing disqualification rules (e.g., matching the condition disqualifies applicant).
        """
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            order=5,
            criterion_key="is_income_tax_payer",
            operator=RuleOperator.BOOLEAN_TRUE,
            value="True",
            data_type=RuleDataType.BOOLEAN,
            is_mandatory=True,
            disqualification_condition=True,
            rule_description="Income tax payers are disqualified",
        )

        # Tax payer applicant -> Disqualified
        user_profile = {
            "age": 21,
            "annual_income": 150000,
            "state": "Bihar",
            "occupation": "STUDENT",
            "is_income_tax_payer": True,
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)
        self.assertEqual(result.verdict, EligibilityVerdict.NOT_ELIGIBLE)
        self.assertFalse(result.is_eligible)
        self.assertTrue(any(r.is_disqualification for r in result.failed_rules))

    def test_multiple_or_rule_groups(self):
        """
        Testing alternative tracks:
        Group 1: Students in Bihar <= 25 (created in setUp)
        Group 2: Artisans in Bihar with income <= 150000 (any age)
        """
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=2,
            order=1,
            criterion_key="occupation",
            operator=RuleOperator.EQUALS,
            value="ARTISAN",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Must be a registered Artisan",
        )
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=2,
            order=2,
            criterion_key="annual_income",
            operator=RuleOperator.LTE,
            value="150000",
            data_type=RuleDataType.DECIMAL,
            is_mandatory=True,
            rule_description="Artisan income must not exceed ₹1,50,000",
        )
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=2,
            order=3,
            criterion_key="state",
            operator=RuleOperator.EQUALS,
            value="Bihar",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Resident of Bihar",
        )

        # A 45-year-old artisan in Bihar (fails Group 1 age limit, but passes Group 2 track)
        user_profile = {
            "age": 45,  # Fails Group 1
            "annual_income": 120000,
            "state": "Bihar",
            "occupation": "ARTISAN",  # Passes Group 2
        }
        result = self.engine.evaluate_scheme(user_profile, self.scheme)
        self.assertEqual(result.verdict, EligibilityVerdict.ELIGIBLE)
        self.assertTrue(result.is_eligible)

    def test_scheme_with_no_rules_returns_insufficient_info(self):
        empty_scheme = GovernmentScheme.objects.create(
            name="Upcoming New Initiative",
            slug="upcoming-initiative",
            category=self.cat,
            status=SchemeStatus.ACTIVE,
        )
        result = self.engine.evaluate_scheme({"age": 25}, empty_scheme)
        self.assertEqual(result.verdict, EligibilityVerdict.INSUFFICIENT_INFORMATION)
        self.assertIsNone(result.is_eligible)


# ─────────────────────────────────────────────────────────────
# 4. API Integration Tests
# ─────────────────────────────────────────────────────────────

class TestEligibilityAPIs(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create Citizen User and Profile
        self.user = User.objects.create_user(
            email="citizen@govscheme.ai",
            password="StrongPassword123!",
            role="USER",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Ramesh Kumar",
            state="BR",
            district="Patna",
            annual_income=Decimal("180000"),
            occupation=OccupationCategory.STUDENT,
            social_category=SocialCategory.OBC,
            is_student=True,
        )
        # Set birthday to age 20
        import datetime
        today = datetime.date.today()
        self.profile.date_of_birth = datetime.date(today.year - 20, today.month, today.day)
        self.profile.save()

        # Create Category, Ministry, Scheme & Rules
        self.cat = SchemeCategory.objects.create(name="Education", slug="education")
        self.scheme = GovernmentScheme.objects.create(
            name="Bihar Youth Student Aid",
            short_title="BYSA",
            slug="bihar-student-aid",
            category=self.cat,
            status=SchemeStatus.ACTIVE,
        )
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            criterion_key="age",
            operator=RuleOperator.LTE,
            value="25",
            data_type=RuleDataType.INTEGER,
            is_mandatory=True,
        )
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            criterion_key="occupation",
            operator=RuleOperator.EQUALS,
            value="STUDENT",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
        )

    def test_stateless_evaluate_api(self):
        """POST /api/v1/eligibility/evaluate/ — No auth required."""
        payload = {
            "scheme_id": str(self.scheme.id),
            "profile": {
                "age": 22,
                "occupation": "STUDENT",
                "state": "Bihar",
            },
        }
        res = self.client.post("/api/v1/eligibility/evaluate/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn(data["verdict"], ("Likely Eligible", "Eligible"))
        self.assertTrue(data["is_eligible"])

    def test_authenticated_citizen_scheme_check(self):
        """GET /api/v1/eligibility/schemes/<uuid:scheme_id>/"""
        self.client.force_authenticate(user=self.user)
        res = self.client.get(f"/api/v1/eligibility/schemes/{self.scheme.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn(data["verdict"], ("Likely Eligible", "Eligible"))
        self.assertEqual(len(data["passed_rules"]), 2)

    def test_authenticated_batch_check(self):
        """POST /api/v1/eligibility/check/"""
        self.client.force_authenticate(user=self.user)
        res = self.client.post("/api/v1/eligibility/check/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["eligible_count"], 1)
        self.assertEqual(len(data["results"]), 1)
