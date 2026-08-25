"""
apps/schemes/views.py — APIs for Government Scheme Data Management System
"""

import logging
from django.db.models import Count, Q
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdmin, IsCitizen
from core.pagination import StandardResultsPagination
from core.utils import success_response
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
    SchemeStatus,
)
from .serializers import (
    StateSerializer,
    MinistrySerializer,
    DepartmentSerializer,
    SchemeCategorySerializer,
    GovernmentSchemeListSerializer,
    GovernmentSchemeDetailSerializer,
    GovernmentSchemeCreateUpdateSerializer,
    SchemeEligibilityRuleSerializer,
    SchemeBenefitSerializer,
    RequiredDocumentSerializer,
    ApplicationProcedureSerializer,
    SchemeSourceSerializer,
    SchemeVersionSerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 1. State & Location Endpoints
# ─────────────────────────────────────────────────────────────
class StateListView(ListAPIView):
    """GET /schemes/states/ — List all States and Union Territories."""
    permission_classes = [AllowAny]
    queryset = State.objects.all().order_by("name")
    serializer_class = StateSerializer
    pagination_class = None


# ─────────────────────────────────────────────────────────────
# 2. Ministry & Department Endpoints
# ─────────────────────────────────────────────────────────────
class MinistryListView(ListAPIView):
    """GET /schemes/ministries/ — List all Ministries with nested Departments."""
    permission_classes = [AllowAny]
    queryset = Ministry.objects.prefetch_related("departments").order_by("name")
    serializer_class = MinistrySerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["is_central", "state"]
    search_fields = ["name", "short_code"]


class DepartmentListView(ListAPIView):
    """GET /schemes/departments/ — List Departments."""
    permission_classes = [AllowAny]
    queryset = Department.objects.select_related("ministry").order_by("name")
    serializer_class = DepartmentSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["ministry"]


# ─────────────────────────────────────────────────────────────
# 3. Category Endpoints
# ─────────────────────────────────────────────────────────────
class SchemeCategoryListView(ListAPIView):
    """GET /schemes/categories/ — List all Scheme Categories with active scheme count."""
    permission_classes = [AllowAny]
    serializer_class = SchemeCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return SchemeCategory.objects.annotate(
            schemes_count=Count("schemes", filter=Q(schemes__status=SchemeStatus.ACTIVE))
        ).order_by("name")


# ─────────────────────────────────────────────────────────────
# 4. Government Scheme Core CRUD & Discovery ViewSet
# ─────────────────────────────────────────────────────────────
class GovernmentSchemeViewSet(viewsets.ModelViewSet):
    """
    Core CRUD and search API for Government Schemes.
    - Public: GET list, GET retrieve (by UUID or slug)
    - Admin: POST create, PUT/PATCH update, DELETE destroy
    """
    lookup_field = "id"
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "ministry", "state", "scheme_type", "status"]
    search_fields = ["name", "short_title", "description", "target_beneficiaries", "tags"]
    ordering_fields = ["name", "created_at", "last_updated_at", "launch_date"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_by_slug", "summary_stats"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = GovernmentScheme.objects.select_related("ministry", "department", "category", "state")
        if self.action == "retrieve" or self.action == "get_by_slug":
            return qs.prefetch_related(
                "eligibility_rules",
                "benefits",
                "required_documents",
                "application_steps",
                "sources",
                "versions",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return GovernmentSchemeListSerializer
        elif self.action in ["retrieve", "get_by_slug"]:
            return GovernmentSchemeDetailSerializer
        return GovernmentSchemeCreateUpdateSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(data=serializer.data))

    @action(detail=False, methods=["get"], url_path="by-slug/(?P<slug>[-\\w]+)")
    def get_by_slug(self, request, slug=None):
        """GET /schemes/by-slug/{slug}/ — Retrieve scheme details by friendly URL slug."""
        try:
            scheme = self.get_queryset().get(slug=slug)
            serializer = GovernmentSchemeDetailSerializer(scheme)
            return Response(success_response(data=serializer.data))
        except GovernmentScheme.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": f"Scheme with slug '{slug}' not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["get"], url_path="stats")
    def summary_stats(self, request):
        """GET /schemes/stats/ — High level scheme metrics."""
        total = GovernmentScheme.objects.count()
        active = GovernmentScheme.objects.filter(status=SchemeStatus.ACTIVE).count()
        central = GovernmentScheme.objects.filter(scheme_type__in=["CENTRAL_SECTOR", "CENTRALLY_SPONSORED"]).count()
        state_count = GovernmentScheme.objects.filter(scheme_type="STATE_GOVERNMENT").count()
        categories = SchemeCategory.objects.count()
        ministries = Ministry.objects.count()

        return Response(
            success_response(
                data={
                    "total_schemes": total,
                    "active_schemes": active,
                    "central_schemes": central,
                    "state_schemes": state_count,
                    "total_categories": categories,
                    "total_ministries": ministries,
                }
            )
        )


# ─────────────────────────────────────────────────────────────
# 5. Eligibility Rules Management ViewSet (Admin)
# ─────────────────────────────────────────────────────────────
class SchemeEligibilityRuleViewSet(viewsets.ModelViewSet):
    """CRUD API for structured Scheme Eligibility Rules."""
    serializer_class = SchemeEligibilityRuleSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "criterion_key", "is_mandatory", "rule_group"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return SchemeEligibilityRule.objects.select_related("scheme").order_by("rule_group", "order")


# ─────────────────────────────────────────────────────────────
# 6. Scheme Benefits Management ViewSet
# ─────────────────────────────────────────────────────────────
class SchemeBenefitViewSet(viewsets.ModelViewSet):
    """CRUD API for Scheme Benefits."""
    serializer_class = SchemeBenefitSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "benefit_type", "disbursement_frequency"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return SchemeBenefit.objects.select_related("scheme").order_by("order")


# ─────────────────────────────────────────────────────────────
# 7. Required Documents Management ViewSet
# ─────────────────────────────────────────────────────────────
class RequiredDocumentViewSet(viewsets.ModelViewSet):
    """CRUD API for Required Documents."""
    serializer_class = RequiredDocumentSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "document_type", "is_mandatory"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return RequiredDocument.objects.select_related("scheme").order_by("order")


# ─────────────────────────────────────────────────────────────
# 8. Application Procedure Steps ViewSet
# ─────────────────────────────────────────────────────────────
class ApplicationProcedureViewSet(viewsets.ModelViewSet):
    """CRUD API for Application Procedure Steps."""
    serializer_class = ApplicationProcedureSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "mode"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return ApplicationProcedure.objects.select_related("scheme").order_by("step_number")


# ─────────────────────────────────────────────────────────────
# 9. Scheme Sources ViewSet
# ─────────────────────────────────────────────────────────────
class SchemeSourceViewSet(viewsets.ModelViewSet):
    """CRUD API for Scheme Official Source Grounding."""
    serializer_class = SchemeSourceSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "source_type", "is_verified"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return SchemeSource.objects.select_related("scheme").order_by("-retrieved_at")


# ─────────────────────────────────────────────────────────────
# 10. Scheme Version History ViewSet
# ─────────────────────────────────────────────────────────────
class SchemeVersionViewSet(viewsets.ModelViewSet):
    """Audit and version history for government scheme modifications."""
    serializer_class = SchemeVersionSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scheme", "version_number"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        return SchemeVersion.objects.select_related("scheme", "created_by").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
