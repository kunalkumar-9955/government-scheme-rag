"""
apps/schemes/tests.py — Comprehensive Unit Tests for Government Scheme Data Management
"""
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import CustomUser
from core.permissions import UserRole
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


class GovernmentSchemeAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.citizen = CustomUser.objects.create_user(
            email="citizen_tester@example.com",
            password="CitizenPassword123!",
            role=UserRole.CITIZEN,
        )
        self.admin = CustomUser.objects.create_user(
            email="admin_tester@example.com",
            password="AdminPassword123!",
            role=UserRole.ADMIN,
            is_staff=True,
        )

        # 1. State
        self.state_up = State.objects.create(code="UP", name="Uttar Pradesh", is_union_territory=False)
        self.state_dl = State.objects.create(code="DL", name="Delhi", is_union_territory=True)

        # 2. Ministry & Department
        self.ministry = Ministry.objects.create(
            name="Ministry of Agriculture and Farmers Welfare",
            short_code="MoA&FW",
            website_url="https://agricoop.nic.in",
            is_central=True,
        )
        self.department = Department.objects.create(
            ministry=self.ministry,
            name="Department of Agriculture and Farmers Welfare",
            short_code="DA&FW",
        )

        # 3. Category
        self.category = SchemeCategory.objects.create(
            name="Agriculture & Rural",
            slug="agriculture-rural",
            icon="🌾",
            description="Agricultural schemes",
        )

        # 4. Government Scheme
        self.scheme = GovernmentScheme.objects.create(
            name="Pradhan Mantri Kisan Samman Nidhi",
            slug="pradhan-mantri-kisan-samman-nidhi",
            short_title="PM-KISAN",
            description="Direct income support of Rs. 6000/year to all landholding farmer families.",
            scheme_type=SchemeType.CENTRAL_SECTOR,
            ministry=self.ministry,
            department=self.department,
            category=self.category,
            target_beneficiaries="Landholding farmer families",
            status=SchemeStatus.ACTIVE,
            version="1.0",
            launch_date=date(2019, 2, 24),
            official_application_url="https://pmkisan.gov.in",
            tags=["farmer", "agriculture", "dbt"],
        )

        # 5. Eligibility Rule
        self.rule = SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            criterion_key="occupation",
            operator=RuleOperator.EQUALS,
            value="FARMER",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Beneficiary must be a farmer.",
            order=1,
        )

        # 6. Benefit
        self.benefit = SchemeBenefit.objects.create(
            scheme=self.scheme,
            benefit_type=BenefitType.DIRECT_BENEFIT_TRANSFER,
            title="Rs. 6,000 per year",
            amount=Decimal("6000.00"),
            currency="INR",
            disbursement_frequency=DisbursementFrequency.TRI_ANNUAL,
            order=1,
        )

        # 7. Required Document
        self.document = RequiredDocument.objects.create(
            scheme=self.scheme,
            document_name="Aadhaar Card",
            document_type=DocumentType.IDENTITY_PROOF,
            is_mandatory=True,
            order=1,
        )

        # 8. Application Step
        self.step = ApplicationProcedure.objects.create(
            scheme=self.scheme,
            mode=ApplicationMode.ONLINE,
            step_number=1,
            title="Register on Portal",
            description="Submit Aadhaar details on pmkisan.gov.in",
        )

        # 9. Source
        self.source = SchemeSource.objects.create(
            scheme=self.scheme,
            source_type=SourceType.MINISTRY_GUIDELINE,
            title="PM-Kisan Operational Guidelines",
            url="https://pmkisan.gov.in/guidelines.pdf",
            is_verified=True,
        )

        # URLs
        self.schemes_list_url = reverse("schemes-list")
        self.schemes_detail_url = reverse("schemes-detail", kwargs={"id": str(self.scheme.id)})
        self.states_list_url = reverse("scheme-states")
        self.ministries_list_url = reverse("scheme-ministries")
        self.categories_list_url = reverse("scheme-categories")

    def test_list_states_public(self):
        """Test GET /schemes/states/ returns list of states."""
        res = self.client.get(self.states_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 2)
        codes = [s["code"] for s in res.data]
        self.assertIn("UP", codes)
        self.assertIn("DL", codes)

    def test_list_categories_with_count(self):
        """Test GET /schemes/categories/ returns active schemes count."""
        res = self.client.get(self.categories_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)
        cat = next(c for c in res.data if c["slug"] == "agriculture-rural")
        self.assertEqual(cat["schemes_count"], 1)

    def test_list_ministries_with_departments(self):
        """Test GET /schemes/ministries/ pre-fetches departments."""
        res = self.client.get(self.ministries_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)
        m = res.data[0]
        self.assertEqual(m["short_code"], "MoA&FW")
        self.assertGreaterEqual(len(m["departments"]), 1)

    def test_list_schemes_filtering_and_search(self):
        """Test GET /schemes/ with category filter and search query."""
        # 1. Search by keyword
        res = self.client.get(self.schemes_list_url, {"search": "kisan"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["short_title"], "PM-KISAN")

        # 2. Filter by category UUID
        res_cat = self.client.get(self.schemes_list_url, {"category": str(self.category.id)})
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(res_cat.data["count"], 1)

        # 3. Filter by status
        res_active = self.client.get(self.schemes_list_url, {"status": "ACTIVE"})
        self.assertEqual(res_active.status_code, status.HTTP_200_OK)
        self.assertEqual(res_active.data["count"], 1)

    def test_retrieve_scheme_detail_with_nested_objects(self):
        """Test GET /schemes/{id}/ returns fully nested rules, benefits, documents, steps, and sources."""
        res = self.client.get(self.schemes_detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data["data"]
        self.assertEqual(data["name"], "Pradhan Mantri Kisan Samman Nidhi")
        self.assertEqual(data["short_title"], "PM-KISAN")
        self.assertEqual(len(data["eligibility_rules"]), 1)
        self.assertEqual(data["eligibility_rules"][0]["criterion_key"], "occupation")
        self.assertEqual(len(data["benefits"]), 1)
        self.assertEqual(float(data["benefits"][0]["amount"]), 6000.0)
        self.assertEqual(len(data["required_documents"]), 1)
        self.assertEqual(data["required_documents"][0]["document_name"], "Aadhaar Card")
        self.assertEqual(len(data["application_steps"]), 1)
        self.assertEqual(len(data["sources"]), 1)

    def test_retrieve_scheme_by_slug(self):
        """Test GET /schemes/by-slug/{slug}/ returns full scheme detail."""
        slug_url = reverse("schemes-get-by-slug", kwargs={"slug": self.scheme.slug})
        res = self.client.get(slug_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["short_title"], "PM-KISAN")

    def test_schemes_summary_stats(self):
        """Test GET /schemes/stats/ returns summary counts."""
        stats_url = reverse("schemes-summary-stats")
        res = self.client.get(stats_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["total_schemes"], 1)
        self.assertEqual(res.data["data"]["active_schemes"], 1)

    def test_citizen_cannot_create_scheme(self):
        """Test Citizen role gets 403 Forbidden when attempting to create a scheme."""
        self.client.force_authenticate(user=self.citizen)
        create_data = {
            "name": "New Unauthorized Scheme",
            "description": "Unauthorized attempt",
            "scheme_type": SchemeType.CENTRAL_SECTOR,
            "status": SchemeStatus.ACTIVE,
        }
        res = self.client.post(self.schemes_list_url, create_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_scheme(self):
        """Test Admin role can create a new scheme."""
        self.client.force_authenticate(user=self.admin)
        create_data = {
            "name": "Pradhan Mantri Matru Vandana Yojana",
            "short_title": "PMMVY",
            "description": "Maternity benefit cash incentive program.",
            "scheme_type": SchemeType.CENTRALLY_SPONSORED,
            "ministry": self.ministry.id,
            "category": self.category.id,
            "status": SchemeStatus.ACTIVE,
        }
        res = self.client.post(self.schemes_list_url, create_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GovernmentScheme.objects.filter(short_title="PMMVY").exists())

    def test_admin_create_eligibility_rule_and_benefit(self):
        """Test Admin can create structured eligibility rules and benefits via API."""
        self.client.force_authenticate(user=self.admin)

        # 1. Create Rule
        rules_url = reverse("scheme-rules-list")
        rule_data = {
            "scheme": str(self.scheme.id),
            "rule_group": 1,
            "criterion_key": "age",
            "operator": RuleOperator.BETWEEN,
            "min_value": "18",
            "max_value": "40",
            "data_type": RuleDataType.INTEGER,
            "is_mandatory": True,
            "rule_description": "Age between 18 and 40",
            "order": 2,
        }
        res_rule = self.client.post(rules_url, rule_data, format="json")
        self.assertEqual(res_rule.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_rule.data["criterion_key"], "age")

        # 2. Create Benefit
        benefits_url = reverse("scheme-benefits-list")
        benefit_data = {
            "scheme": str(self.scheme.id),
            "benefit_type": BenefitType.SUBSIDY,
            "title": "50% Seed Subsidy",
            "description": "Subsidy on certified seeds up to Rs. 2,000",
            "amount": "2000.00",
            "currency": "INR",
            "disbursement_frequency": DisbursementFrequency.ONE_TIME,
            "order": 2,
        }
        res_ben = self.client.post(benefits_url, benefit_data, format="json")
        self.assertEqual(res_ben.status_code, status.HTTP_201_CREATED)

    def test_scheme_version_audit_creation(self):
        """Test creating a SchemeVersion snapshot record."""
        self.client.force_authenticate(user=self.admin)
        versions_url = reverse("scheme-versions-list")
        ver_data = {
            "scheme": str(self.scheme.id),
            "version_number": "2.0",
            "change_summary": "Revised eKYC rules",
            "effective_from": "2025-01-01",
            "snapshot_data": {"amount": 6000, "rules_count": 2},
        }
        res = self.client.post(versions_url, ver_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["created_by_email"], self.admin.email)
