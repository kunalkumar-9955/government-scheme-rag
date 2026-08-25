"""
apps/authentication/models.py — Custom User with RBAC roles
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from core.permissions import UserRole


class CustomUserManager(BaseUserManager):
    """Manager for email-based authentication."""

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.CITIZEN)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with UUID primary key, email login, and RBAC role.
    Replaces Django's default User entirely.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True, max_length=255)
    role = models.CharField(
        max_length=20,
        choices=UserRole.CHOICES,
        default=UserRole.CITIZEN,
        db_index=True,
    )

    # Status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)           # Django admin access
    is_email_verified = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "auth_users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_citizen(self) -> bool:
        return self.role == UserRole.CITIZEN

    @property
    def is_admin(self) -> bool:
        return UserRole.has_min_role(self.role, UserRole.ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN


class EmailVerificationOTP(models.Model):
    """OTP for email verification and password reset."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=20,
        choices=[("EMAIL_VERIFY", "Email Verify"), ("PASSWORD_RESET", "Password Reset")],
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "auth_email_otps"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP({self.purpose}) for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() > self.expires_at
