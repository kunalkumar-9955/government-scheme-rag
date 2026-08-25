"""
apps/schemes/urls.py — URL routing for Government Scheme Data Management System
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StateListView,
    MinistryListView,
    DepartmentListView,
    SchemeCategoryListView,
    GovernmentSchemeViewSet,
    SchemeEligibilityRuleViewSet,
    SchemeBenefitViewSet,
    RequiredDocumentViewSet,
    ApplicationProcedureViewSet,
    SchemeSourceViewSet,
    SchemeVersionViewSet,
)

router = DefaultRouter()
router.register(r"rules", SchemeEligibilityRuleViewSet, basename="scheme-rules")
router.register(r"benefits", SchemeBenefitViewSet, basename="scheme-benefits")
router.register(r"documents", RequiredDocumentViewSet, basename="scheme-documents")
router.register(r"steps", ApplicationProcedureViewSet, basename="scheme-steps")
router.register(r"sources", SchemeSourceViewSet, basename="scheme-sources")
router.register(r"versions", SchemeVersionViewSet, basename="scheme-versions")
router.register(r"", GovernmentSchemeViewSet, basename="schemes")

urlpatterns = [
    path("states/", StateListView.as_view(), name="scheme-states"),
    path("ministries/", MinistryListView.as_view(), name="scheme-ministries"),
    path("departments/", DepartmentListView.as_view(), name="scheme-departments"),
    path("categories/", SchemeCategoryListView.as_view(), name="scheme-categories"),
    path("", include(router.urls)),
]
