"""
apps/authentication/admin.py — Django admin for auth models
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, EmailVerificationOTP


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ["email", "role", "is_active", "is_email_verified", "date_joined"]
    list_filter = ["role", "is_active", "is_email_verified"]
    search_fields = ["email"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_login"]

    fieldsets = (
        ("Account", {"fields": ("id", "email", "password")}),
        ("Role & Status", {"fields": ("role", "is_active", "is_email_verified", "is_staff", "is_superuser")}),
        ("Timestamps", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role"),
        }),
    )

    # Required for AbstractBaseUser
    filter_horizontal = ("groups", "user_permissions")


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "is_used", "created_at", "expires_at"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "created_at"]
