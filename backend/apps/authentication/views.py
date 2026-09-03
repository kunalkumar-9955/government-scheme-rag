"""
apps/authentication/views.py — Auth API endpoints
"""
import logging
import random
import string
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from core.utils import success_response
from .models import CustomUser, EmailVerificationOTP
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    VerifyEmailSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
)
from .tasks import send_password_reset_email

logger = logging.getLogger(__name__)


def _get_tokens_for_user(user: CustomUser) -> dict:
    """Generate JWT access + refresh token pair for a user."""
    try:
        refresh = RefreshToken.for_user(user)
        access_token_str = str(refresh.access_token)
        refresh_token_str = str(refresh)
        expires_in_sec = int(refresh.access_token.lifetime.total_seconds())
    except Exception as exc:
        logger.exception("Token generation fallback triggered: %s", exc)
        refresh = RefreshToken()
        refresh["user_id"] = str(user.id)
        refresh["email"] = user.email
        refresh["role"] = getattr(user, "role", "CITIZEN")
        access_token_str = str(refresh.access_token)
        refresh_token_str = str(refresh)
        expires_in_sec = 3600

    return {
        "access_token": access_token_str,
        "refresh_token": refresh_token_str,
        "token_type": "Bearer",
        "expires_in": expires_in_sec,
        "user": user,
    }


class RegisterView(APIView):
    """POST /auth/register/ — Create new citizen account."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _get_tokens_for_user(user)
        logger.info("New user registered: %s", user.email)
        return Response(
            success_response(
                data={
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": tokens["token_type"],
                    "expires_in": tokens["expires_in"],
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "role": user.role,
                        "is_email_verified": user.is_email_verified,
                    },
                },
                message="Registration successful. Please verify your email.",
            ),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /auth/login/ — Authenticate and get JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens_for_user(user)
        logger.info("User logged in: %s", user.email)
        return Response(
            success_response(
                data={
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": tokens["token_type"],
                    "expires_in": tokens["expires_in"],
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "role": user.role,
                        "is_email_verified": user.is_email_verified,
                    },
                },
                message="Login successful.",
            ),
            status=status.HTTP_200_OK,
        )


class RefreshTokenView(APIView):
    """POST /auth/refresh/ — Rotate refresh token and get new access token."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            old_refresh = RefreshToken(serializer.validated_data["refresh_token"])
            # Blacklist old token (rotation)
            old_refresh.blacklist()
            # Get user and generate new pair
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            user_id = old_refresh.get("user_id")
            user = CustomUser.objects.get(id=user_id)
            tokens = _get_tokens_for_user(user)
        except (TokenError, InvalidToken, CustomUser.DoesNotExist) as e:
            return Response(
                {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Refresh token is invalid or expired."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            success_response(
                data={
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": tokens["token_type"],
                    "expires_in": tokens["expires_in"],
                },
                message="Token refreshed successfully.",
            ),
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /auth/logout/ — Blacklist refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = RefreshToken(serializer.validated_data["refresh_token"])
            refresh_token.blacklist()
        except (TokenError, InvalidToken):
            pass  # Already blacklisted or invalid — still return success

        logger.info("User logged out: %s", request.user.email)
        return Response(success_response(message="Logged out successfully."), status=status.HTTP_200_OK)


class VerifyEmailView(APIView):
    """POST /auth/verify-email/ — Verify email with 6-digit OTP."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: CustomUser = serializer.validated_data["user"]
        otp: EmailVerificationOTP = serializer.validated_data["otp"]

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        return Response(success_response(message="Email verified successfully."), status=status.HTTP_200_OK)


class ResendVerificationView(APIView):
    """POST /auth/resend-verification/ — Resend OTP email."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower().strip()
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Don't reveal existence
            return Response(
                success_response(message="If this email is registered, a new OTP has been sent."),
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {"success": False, "error": {"code": "ALREADY_VERIFIED", "message": "Email already verified."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_code = "".join(random.choices(string.digits, k=6))
        EmailVerificationOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose="EMAIL_VERIFY",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        from .tasks import send_verification_email
        send_verification_email(str(user.id), otp_code)

        return Response(
            success_response(message="Verification OTP sent. Please check your email."),
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """POST /auth/forgot-password/ — Send password reset OTP."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = CustomUser.objects.get(email=email)
            otp_code = "".join(random.choices(string.digits, k=6))
            EmailVerificationOTP.objects.create(
                user=user,
                otp_code=otp_code,
                purpose="PASSWORD_RESET",
                expires_at=timezone.now() + timedelta(minutes=15),
            )
            send_password_reset_email(str(user.id), otp_code)
        except CustomUser.DoesNotExist:
            pass  # Security: don't reveal if email exists

        return Response(
            success_response(message="If this email is registered, a password reset OTP has been sent."),
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """POST /auth/reset-password/ — Reset password with OTP."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: CustomUser = serializer.validated_data["user"]
        otp: EmailVerificationOTP = serializer.validated_data["otp"]

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        logger.info("Password reset for: %s", user.email)
        return Response(success_response(message="Password reset successfully."), status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """POST /auth/change-password/ — Change password (authenticated)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        return Response(success_response(message="Password changed successfully."), status=status.HTTP_200_OK)


class MeView(APIView):
    """GET /auth/me/ — Get current user info."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            success_response(data={
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
            }),
            status=status.HTTP_200_OK,
        )
