"""
core/permissions.py — RBAC permission classes
"""
from rest_framework.permissions import BasePermission


class UserRole:
    CITIZEN = "CITIZEN"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

    CHOICES = [
        (CITIZEN, "Citizen"),
        (ADMIN, "Admin"),
        (SUPER_ADMIN, "Super Admin"),
    ]

    # Ordered hierarchy (higher index = more privileges)
    HIERARCHY = [CITIZEN, ADMIN, SUPER_ADMIN]

    @classmethod
    def has_min_role(cls, user_role: str, min_role: str) -> bool:
        """Check if user_role has at least the privileges of min_role."""
        try:
            return cls.HIERARCHY.index(user_role) >= cls.HIERARCHY.index(min_role)
        except ValueError:
            return False


class IsCitizen(BasePermission):
    """Allow any authenticated user (CITIZEN, ADMIN, SUPER_ADMIN)."""
    message = "Authentication required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in [UserRole.CITIZEN, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        )


class IsAdmin(BasePermission):
    """Allow ADMIN and SUPER_ADMIN roles."""
    message = "Admin privileges required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and UserRole.has_min_role(request.user.role, UserRole.ADMIN)
        )


class IsSuperAdmin(BasePermission):
    """Allow only SUPER_ADMIN role."""
    message = "Super admin privileges required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )


class IsOwnerOrAdmin(BasePermission):
    """Allow object owner or admin+."""
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if UserRole.has_min_role(request.user.role, UserRole.ADMIN):
            return True
        # Object must have a user or created_by field
        owner = getattr(obj, "user", None) or getattr(obj, "created_by", None)
        return owner == request.user
