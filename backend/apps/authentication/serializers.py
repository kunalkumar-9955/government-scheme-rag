"""
apps/authentication/serializers.py — Auth API serializers
"""
import random
import string
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, EmailVerificationOTP


class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer with password confirmation."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})

    class Meta:
        model = CustomUser
        fields = ["email", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = CustomUser.objects.create_user(**validated_data)
        # Queue email verification OTP
        self._send_verification_otp(user)
        return user

    def _send_verification_otp(self, user: CustomUser):
        otp_code = "".join(random.choices(string.digits, k=6))
        EmailVerificationOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose="EMAIL_VERIFY",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        from apps.authentication.tasks import send_verification_email
        send_verification_email(str(user.id), otp_code)


class LoginSerializer(serializers.Serializer):
    """Login with email + password, returns JWT pair."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled. Contact support.")

        attrs["user"] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """Response shape for login/refresh endpoints."""
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    expires_in = serializers.IntegerField(help_text="Access token lifetime in seconds")
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        user = obj.get("user")
        if user:
            return {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_email_verified": user.is_email_verified,
            }
        return None


class RefreshTokenSerializer(serializers.Serializer):
    """Refresh access token."""
    refresh_token = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Blacklist refresh token on logout."""
    refresh_token = serializers.CharField(required=True)


class VerifyEmailSerializer(serializers.Serializer):
    """Verify email with 6-digit OTP."""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(min_length=6, max_length=6, required=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        otp_code = attrs["otp_code"]

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        try:
            otp = EmailVerificationOTP.objects.get(
                user=user,
                otp_code=otp_code,
                purpose="EMAIL_VERIFY",
                is_used=False,
            )
        except EmailVerificationOTP.DoesNotExist:
            raise serializers.ValidationError({"otp_code": "Invalid OTP code."})

        if otp.is_expired:
            raise serializers.ValidationError({"otp_code": "OTP has expired. Request a new one."})

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Request a password reset OTP."""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        # Don't reveal whether the email exists (security)
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password using OTP."""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(min_length=6, max_length=6, required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password], write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        email = attrs["email"].lower().strip()
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        try:
            otp = EmailVerificationOTP.objects.get(
                user=user,
                otp_code=attrs["otp_code"],
                purpose="PASSWORD_RESET",
                is_used=False,
            )
        except EmailVerificationOTP.DoesNotExist:
            raise serializers.ValidationError({"otp_code": "Invalid OTP."})

        if otp.is_expired:
            raise serializers.ValidationError({"otp_code": "OTP has expired."})

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Change password for authenticated users."""
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, validators=[validate_password], write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs
