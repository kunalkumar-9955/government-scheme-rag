"""
apps/eligibility/urls.py — URL routing for the Eligibility Evaluation Engine.
"""
from django.urls import path
from apps.eligibility.views import (
    EligibilityCheckView,
    SchemeEligibilityView,
    StatelessEligibilityEvaluateView,
)

app_name = "eligibility"

urlpatterns = [
    path("check/", EligibilityCheckView.as_view(), name="eligibility-check"),
    path("evaluate/", StatelessEligibilityEvaluateView.as_view(), name="eligibility-evaluate"),
    path("schemes/<uuid:scheme_id>/", SchemeEligibilityView.as_view(), name="scheme-eligibility"),
]
