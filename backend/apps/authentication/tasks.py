"""
apps/authentication/tasks.py — Email notifications
Phase 1: Direct send_mail (no Celery needed).
Phase 2+: Wrap with @shared_task for async delivery.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_verification_email(user_id: str, otp_code: str):
    """Send email verification OTP to user."""
    from .models import CustomUser
    try:
        user = CustomUser.objects.get(id=user_id)
        subject = "Verify your Government Scheme AI Account"
        message = (
            f"Hello,\n\n"
            f"Your email verification code is: {otp_code}\n\n"
            f"This code is valid for 15 minutes.\n\n"
            f"If you did not create an account, please ignore this email.\n\n"
            f"— Government Scheme AI Assistant Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Verification email sent to: %s", user.email)
    except Exception as exc:
        logger.error("Failed to send verification email to user %s: %s", user_id, exc)


def send_password_reset_email(user_id: str, otp_code: str):
    """Send password reset OTP to user."""
    from .models import CustomUser
    try:
        user = CustomUser.objects.get(id=user_id)
        subject = "Password Reset — Government Scheme AI"
        message = (
            f"Hello,\n\n"
            f"You requested a password reset. Your OTP code is: {otp_code}\n\n"
            f"This code is valid for 15 minutes. If you did not request this, please ignore.\n\n"
            f"— Government Scheme AI Assistant Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Password reset email sent to: %s", user.email)
    except Exception as exc:
        logger.error("Failed to send password reset email to user %s: %s", user_id, exc)
