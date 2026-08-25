"""
apps/eligibility/views.py — Deterministic Eligibility Evaluation APIs.

Endpoints:
- POST /api/v1/eligibility/check/ — Check user profile against all active schemes
- GET  /api/v1/eligibility/schemes/<uuid:scheme_id>/ — Check eligibility for a specific scheme
- POST /api/v1/eligibility/evaluate/ — Stateless evaluation against arbitrary citizen payload
"""
import logging
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.eligibility.engine import EligibilityEngine, EligibilityVerdict
from apps.schemes.models import GovernmentScheme, SchemeStatus
from apps.users.models import UserProfile
from core.permissions import IsCitizen
from core.utils import error_response, success_response

logger = logging.getLogger(__name__)


class EligibilityCheckView(APIView):
    """
    POST /api/v1/eligibility/check/
    Evaluates the authenticated citizen's UserProfile against all active government schemes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                error_response(
                    code="PROFILE_NOT_FOUND",
                    message="Please complete your profile before checking eligibility.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional filters from query or body: category, state
        category_slug = request.data.get("category")
        state_code = request.data.get("state")

        schemes_qs = GovernmentScheme.objects.filter(status=SchemeStatus.ACTIVE).prefetch_related(
            "eligibility_rules",
            "sources",
        )

        if category_slug:
            schemes_qs = schemes_qs.filter(category__slug=category_slug)
        if state_code:
            # Match central schemes (state=None) or schemes specific to this state
            schemes_qs = schemes_qs.filter(state__code=state_code) | schemes_qs.filter(state__isnull=True)

        engine = EligibilityEngine()
        user_context = profile.to_eligibility_context()
        results = engine.evaluate_multiple_schemes(user_context, list(schemes_qs))

        results_data = [r.to_dict() for r in results]

        summary_counts = {
            "total_schemes_evaluated": len(results_data),
            "eligible_count": sum(1 for r in results if r.verdict == EligibilityVerdict.ELIGIBLE),
            "possibly_eligible_count": sum(1 for r in results if r.verdict == EligibilityVerdict.POSSIBLY_ELIGIBLE),
            "insufficient_info_count": sum(1 for r in results if r.verdict == EligibilityVerdict.INSUFFICIENT_INFORMATION),
            "not_eligible_count": sum(1 for r in results if r.verdict == EligibilityVerdict.NOT_ELIGIBLE),
        }

        return Response(
            success_response(
                data={
                    "summary": summary_counts,
                    "profile_completion_score": profile.profile_completion_score,
                    "results": results_data,
                }
            )
        )


class SchemeEligibilityView(APIView):
    """
    GET /api/v1/eligibility/schemes/<uuid:scheme_id>/
    Evaluates the authenticated citizen's UserProfile against a single target scheme.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, scheme_id):
        try:
            scheme = GovernmentScheme.objects.prefetch_related(
                "eligibility_rules",
                "sources",
            ).get(id=scheme_id)
        except GovernmentScheme.DoesNotExist:
            return Response(
                error_response(
                    code="SCHEME_NOT_FOUND",
                    message=f"Government scheme with ID '{scheme_id}' was not found.",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            profile = UserProfile.objects.get(user=request.user)
            user_context = profile.to_eligibility_context()
        except UserProfile.DoesNotExist:
            return Response(
                error_response(
                    code="PROFILE_NOT_FOUND",
                    message="Please complete your profile before checking eligibility.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = EligibilityEngine()
        result = engine.evaluate_scheme(user_context, scheme)

        return Response(
            success_response(
                data=result.to_dict()
            )
        )


class StatelessEligibilityEvaluateView(APIView):
    """
    POST /api/v1/eligibility/evaluate/
    Evaluates a specific scheme (or all active schemes) against an arbitrary citizen context dictionary.
    No authentication required (useful for chatbots, what-if simulators, and unauthenticated users).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_context = request.data.get("profile", {})
        scheme_id = request.data.get("scheme_id")

        if not isinstance(user_context, dict):
            return Response(
                error_response(
                    code="INVALID_PAYLOAD",
                    message="'profile' must be a JSON dictionary containing user attributes.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = EligibilityEngine()

        if scheme_id:
            try:
                scheme = GovernmentScheme.objects.prefetch_related(
                    "eligibility_rules",
                    "sources",
                ).get(id=scheme_id)
            except GovernmentScheme.DoesNotExist:
                return Response(
                    error_response(
                        code="SCHEME_NOT_FOUND",
                        message=f"Scheme with ID '{scheme_id}' does not exist.",
                    ),
                    status=status.HTTP_404_NOT_FOUND,
                )
            result = engine.evaluate_scheme(user_context, scheme)
            return Response(success_response(data=result.to_dict()))

        # If no scheme_id provided, evaluate all active schemes
        schemes = list(GovernmentScheme.objects.filter(status=SchemeStatus.ACTIVE).prefetch_related(
            "eligibility_rules",
            "sources",
        ))
        results = engine.evaluate_multiple_schemes(user_context, schemes)
        results_data = [r.to_dict() for r in results]

        return Response(
            success_response(
                data={
                    "total_evaluated": len(results_data),
                    "results": results_data,
                }
            )
        )
