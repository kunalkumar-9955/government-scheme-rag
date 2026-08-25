"""
apps/schemes/admin.py — Django Admin Configuration for Government Schemes
"""
from django.contrib import admin
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


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_union_territory", "official_portal_url"]
    search_fields = ["name", "code"]
    list_filter = ["is_union_territory"]


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1


@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    list_display = ["name", "short_code", "is_central", "state", "website_url"]
    search_fields = ["name", "short_code"]
    list_filter = ["is_central", "state"]
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "ministry", "short_code", "website_url"]
    search_fields = ["name", "ministry__name"]
    list_filter = ["ministry"]


@admin.register(SchemeCategory)
class SchemeCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class SchemeEligibilityRuleInline(admin.TabularInline):
    model = SchemeEligibilityRule
    extra = 1
    fields = [
        "rule_group",
        "criterion_key",
        "operator",
        "value",
        "min_value",
        "max_value",
        "data_type",
        "is_mandatory",
        "disqualification_condition",
        "rule_description",
    ]


class SchemeBenefitInline(admin.TabularInline):
    model = SchemeBenefit
    extra = 1
    fields = ["benefit_type", "title", "amount", "currency", "disbursement_frequency", "order"]


class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 1
    fields = ["document_name", "document_type", "is_mandatory", "issuing_authority", "order"]


class ApplicationProcedureInline(admin.TabularInline):
    model = ApplicationProcedure
    extra = 1
    fields = ["step_number", "mode", "title", "portal_url", "processing_time_days", "fee_inr"]


class SchemeSourceInline(admin.TabularInline):
    model = SchemeSource
    extra = 1
    fields = ["source_type", "title", "url", "document_reference_number", "is_verified"]


@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "short_title",
        "scheme_type",
        "ministry",
        "category",
        "state",
        "status",
        "version",
        "last_updated_at",
    ]
    list_filter = ["status", "scheme_type", "category", "state", "ministry"]
    search_fields = ["name", "short_title", "description", "target_beneficiaries", "tags"]
    prepopulated_fields = {"slug": ("short_title", "name")}
    inlines = [
        SchemeEligibilityRuleInline,
        SchemeBenefitInline,
        RequiredDocumentInline,
        ApplicationProcedureInline,
        SchemeSourceInline,
    ]


@admin.register(SchemeEligibilityRule)
class SchemeEligibilityRuleAdmin(admin.ModelAdmin):
    list_display = ["scheme", "rule_group", "criterion_key", "operator", "value", "is_mandatory", "disqualification_condition"]
    list_filter = ["operator", "is_mandatory", "disqualification_condition", "data_type"]
    search_fields = ["scheme__name", "criterion_key", "rule_description"]


@admin.register(SchemeBenefit)
class SchemeBenefitAdmin(admin.ModelAdmin):
    list_display = ["scheme", "benefit_type", "title", "amount", "disbursement_frequency"]
    list_filter = ["benefit_type", "disbursement_frequency"]
    search_fields = ["scheme__name", "title"]


@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display = ["scheme", "document_name", "document_type", "is_mandatory", "issuing_authority"]
    list_filter = ["document_type", "is_mandatory"]
    search_fields = ["scheme__name", "document_name"]


@admin.register(ApplicationProcedure)
class ApplicationProcedureAdmin(admin.ModelAdmin):
    list_display = ["scheme", "step_number", "mode", "title", "processing_time_days", "fee_inr"]
    list_filter = ["mode"]
    search_fields = ["scheme__name", "title"]


@admin.register(SchemeSource)
class SchemeSourceAdmin(admin.ModelAdmin):
    list_display = ["scheme", "source_type", "title", "is_verified", "retrieved_at"]
    list_filter = ["source_type", "is_verified"]
    search_fields = ["scheme__name", "title", "url"]


@admin.register(SchemeVersion)
class SchemeVersionAdmin(admin.ModelAdmin):
    list_display = ["scheme", "version_number", "effective_from", "effective_to", "created_by", "created_at"]
    search_fields = ["scheme__name", "version_number", "change_summary"]
    list_filter = ["version_number"]
