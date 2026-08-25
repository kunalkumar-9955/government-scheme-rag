"""
apps/users/views.py — User profile API endpoints
"""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView

from core.permissions import IsAdmin, IsSuperAdmin, UserRole
from core.utils import success_response
from core.pagination import LargeResultsPagination
from apps.authentication.models import CustomUser
from .models import UserProfile
from .serializers import UserProfileSerializer, UserProfileUpdateSerializer

logger = logging.getLogger(__name__)


class MyProfileView(APIView):
    """
    GET  /users/me/profile/  → Get own profile
    PUT  /users/me/profile/  → Full profile update
    PATCH /users/me/profile/ → Partial profile update
    """

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(success_response(data=serializer.data), status=status.HTTP_200_OK)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial: bool):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        full_serializer = UserProfileSerializer(profile)
        return Response(
            success_response(data=full_serializer.data, message="Profile updated successfully."),
            status=status.HTTP_200_OK,
        )


class UserListView(ListAPIView):
    """
    GET /users/ — Admin: list all users with profiles.
    """
    permission_classes = [IsAdmin]
    pagination_class = LargeResultsPagination

    def get_queryset(self):
        return CustomUser.objects.select_related("profile").order_by("-date_joined")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        data = [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "is_email_verified": u.is_email_verified,
                "date_joined": u.date_joined,
                "profile": UserProfileSerializer(u.profile).data if hasattr(u, "profile") else None,
            }
            for u in (page or queryset)
        ]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(success_response(data=data))


class UserDetailView(APIView):
    """
    GET   /users/{id}/       — Admin: user detail
    PATCH /users/{id}/role/  — SuperAdmin: change user role
    """
    permission_classes = [IsAdmin]

    def get_object(self, user_id):
        try:
            return CustomUser.objects.select_related("profile").get(id=user_id)
        except CustomUser.DoesNotExist:
            return None

    def get(self, request, user_id):
        user = self.get_object(user_id)
        if not user:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "profile": UserProfileSerializer(user.profile).data if hasattr(user, "profile") else None,
        }
        return Response(success_response(data=data))


class ChangeUserRoleView(APIView):
    """PATCH /users/{id}/role/ — SuperAdmin only: change user role."""
    permission_classes = [IsSuperAdmin]

    def patch(self, request, user_id):
        new_role = request.data.get("role")
        if new_role not in [r[0] for r in UserRole.CHOICES]:
            return Response(
                {"success": False, "error": {"code": "INVALID_ROLE", "message": f"Invalid role: {new_role}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_role = user.role
        user.role = new_role
        user.save(update_fields=["role"])
        logger.info("User %s role changed from %s to %s by %s", user.email, old_role, new_role, request.user.email)

        return Response(
            success_response(
                data={"id": str(user.id), "email": user.email, "role": user.role},
                message=f"User role updated to {new_role}.",
            ),
            status=status.HTTP_200_OK,
        )


class DeactivateUserView(APIView):
    """PATCH /users/{id}/deactivate/ — Admin: deactivate user account."""
    permission_classes = [IsAdmin]

    def patch(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user == request.user:
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "You cannot deactivate your own account."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(success_response(message="User deactivated."), status=status.HTTP_200_OK)
