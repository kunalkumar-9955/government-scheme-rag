"""
apps/authentication/urls.py — Auth URL patterns
"""
from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    RefreshTokenView,
    LogoutView,
    VerifyEmailView,
    ResendVerificationView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    MeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]
