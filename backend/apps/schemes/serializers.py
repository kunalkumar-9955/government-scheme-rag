"""
apps/schemes/serializers.py — Serializers for Government Scheme Data Management System
"""
from rest_framework import serializers
from .models import (
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
)


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "code", "name", "is_union_territory", "official_portal_url"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "ministry", "name", "short_code", "website_url"]


class MinistrySerializer(serializers.ModelSerializer):
    departments = DepartmentSerializer(many=True, read_only=True)
    state_code = serializers.CharField(source="state.code", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)

    class Meta:
        model = Ministry
        fields = [
            "id",
            "name",
            "short_code",
            "website_url",
            "is_central",
            "state",
            "state_code",
            "state_name",
            "departments",
        ]


class SchemeCategorySerializer(serializers.ModelSerializer):
    schemes_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = SchemeCategory
        fields = ["id", "name", "slug", "icon", "description", "schemes_count"]


class SchemeEligibilityRuleSerializer(serializers.ModelSerializer):
    operator_display = serializers.CharField(source="get_operator_display", read_only=True)
    data_type_display = serializers.CharField(source="get_data_type_display", read_only=True)

    class Meta:
        model = SchemeEligibilityRule
        fields = [
            "id",
            "scheme",
            "rule_group",
            "criterion_key",
            "operator",
            "operator_display",
            "value",
            "min_value",
            "max_value",
            "data_type",
            "data_type_display",
            "is_mandatory",
            "disqualification_condition",
            "rule_description",
            "order",
        ]
        read_only_fields = ["id"]


class SchemeBenefitSerializer(serializers.ModelSerializer):
    benefit_type_display = serializers.CharField(source="get_benefit_type_display", read_only=True)
    disbursement_frequency_display = serializers.CharField(source="get_disbursement_frequency_display", read_only=True)

    class Meta:
        model = SchemeBenefit
        fields = [
            "id",
            "scheme",
            "benefit_type",
            "benefit_type_display",
            "title",
            "description",
            "amount",
            "currency",
            "disbursement_frequency",
            "disbursement_frequency_display",
            "order",
        ]
        read_only_fields = ["id"]


class RequiredDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = RequiredDocument
        fields = [
            "id",
            "scheme",
            "document_name",
            "document_type",
            "document_type_display",
            "is_mandatory",
            "description",
            "issuing_authority",
            "accepted_formats",
            "order",
        ]
        read_only_fields = ["id"]


class ApplicationProcedureSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)

    class Meta:
        model = ApplicationProcedure
        fields = [
            "id",
            "scheme",
            "mode",
            "mode_display",
            "step_number",
            "title",
            "description",
            "portal_url",
            "office_name",
            "processing_time_days",
            "fee_inr",
        ]
        read_only_fields = ["id"]


class SchemeSourceSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = SchemeSource
        fields = [
            "id",
            "scheme",
            "source_type",
            "source_type_display",
            "title",
            "url",
            "document_reference_number",
            "published_date",
            "is_verified",
            "retrieved_at",
        ]
        read_only_fields = ["id", "retrieved_at"]


class SchemeVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = SchemeVersion
        fields = [
            "id",
            "scheme",
            "version_number",
            "change_summary",
            "effective_from",
            "effective_to",
            "snapshot_data",
            "created_by",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ─────────────────────────────────────────────────────────────
# Scheme List Serializer (Lightweight for Discovery / Search)
# ─────────────────────────────────────────────────────────────
class GovernmentSchemeListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_icon = serializers.CharField(source="category.icon", read_only=True)
    ministry_name = serializers.CharField(source="ministry.name", read_only=True)
    ministry_code = serializers.CharField(source="ministry.short_code", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    state_code = serializers.CharField(source="state.code", read_only=True)
    scheme_type_display = serializers.CharField(source="get_scheme_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # Counts
    eligibility_rules_count = serializers.IntegerField(source="eligibility_rules.count", read_only=True)
    benefits_count = serializers.IntegerField(source="benefits.count", read_only=True)
    required_documents_count = serializers.IntegerField(source="required_documents.count", read_only=True)

    class Meta:
        model = GovernmentScheme
        fields = [
            "id",
            "name",
            "slug",
            "short_title",
            "description",
            "scheme_type",
            "scheme_type_display",
            "ministry",
            "ministry_name",
            "ministry_code",
            "category",
            "category_name",
            "category_icon",
            "state",
            "state_name",
            "state_code",
            "target_beneficiaries",
            "status",
            "status_display",
            "version",
            "launch_date",
            "official_application_url",
            "official_source_url",
            "tags",
            "eligibility_rules_count",
            "benefits_count",
            "required_documents_count",
            "last_updated_at",
            "created_at",
        ]


# ─────────────────────────────────────────────────────────────
# Scheme Detail Serializer (Comprehensive Nested View)
# ─────────────────────────────────────────────────────────────
class GovernmentSchemeDetailSerializer(serializers.ModelSerializer):
    ministry_details = MinistrySerializer(source="ministry", read_only=True)
    department_details = DepartmentSerializer(source="department", read_only=True)
    category_details = SchemeCategorySerializer(source="category", read_only=True)
    state_details = StateSerializer(source="state", read_only=True)
    scheme_type_display = serializers.CharField(source="get_scheme_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    # Nested related models
    eligibility_rules = SchemeEligibilityRuleSerializer(many=True, read_only=True)
    benefits = SchemeBenefitSerializer(many=True, read_only=True)
    required_documents = RequiredDocumentSerializer(many=True, read_only=True)
    application_steps = ApplicationProcedureSerializer(many=True, read_only=True)
    sources = SchemeSourceSerializer(many=True, read_only=True)
    versions = SchemeVersionSerializer(many=True, read_only=True)

    class Meta:
        model = GovernmentScheme
        fields = [
            "id",
            "name",
            "slug",
            "short_title",
            "description",
            "scheme_type",
            "scheme_type_display",
            "ministry",
            "ministry_details",
            "department",
            "department_details",
            "category",
            "category_details",
            "state",
            "state_details",
            "target_beneficiaries",
            "status",
            "status_display",
            "version",
            "launch_date",
            "valid_upto",
            "important_dates",
            "official_application_url",
            "official_source_url",
            "funding_pattern",
            "helpline_number",
            "tags",
            "eligibility_rules",
            "benefits",
            "required_documents",
            "application_steps",
            "sources",
            "versions",
            "last_updated_at",
            "created_at",
        ]


# ─────────────────────────────────────────────────────────────
# Scheme Create / Update Serializer
# ─────────────────────────────────────────────────────────────
class GovernmentSchemeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentScheme
        fields = [
            "id",
            "name",
            "slug",
            "short_title",
            "description",
            "scheme_type",
            "ministry",
            "department",
            "category",
            "state",
            "target_beneficiaries",
            "status",
            "version",
            "launch_date",
            "valid_upto",
            "important_dates",
            "official_application_url",
            "official_source_url",
            "funding_pattern",
            "helpline_number",
            "tags",
        ]
        read_only_fields = ["id", "slug"]
