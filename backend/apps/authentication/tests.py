"""
apps/authentication/tests.py — Comprehensive tests for authentication APIs
"""
import json
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.authentication.models import CustomUser, EmailVerificationOTP
from core.permissions import UserRole


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth-register")
        self.login_url = reverse("auth-login")
        self.refresh_url = reverse("auth-refresh")
        self.logout_url = reverse("auth-logout")
        self.me_url = reverse("auth-me")
        self.verify_email_url = reverse("auth-verify-email")
        self.forgot_password_url = reverse("auth-forgot-password")
        self.reset_password_url = reverse("auth-reset-password")
        self.change_password_url = reverse("auth-change-password")

        self.user_email = "citizen@example.com"
        self.user_password = "SecurePassword123!"
        self.user = CustomUser.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            role=UserRole.CITIZEN,
        )

    def test_register_success(self):
        """Test registering a new citizen account."""
        data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("access_token", response.data["data"])
        self.assertIn("refresh_token", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], "newuser@example.com")
        self.assertEqual(response.data["data"]["user"]["role"], UserRole.CITIZEN)
        # Verify OTP was generated in DB
        self.assertTrue(EmailVerificationOTP.objects.filter(user__email="newuser@example.com").exists())

    def test_register_password_mismatch(self):
        """Test registration fails when password and confirmation don't match."""
        data = {
            "email": "mismatch@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_register_weak_password(self):
        """Test registration fails with weak password."""
        data = {
            "email": "weak@example.com",
            "password": "123",
            "password_confirm": "123",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Test registration fails with existing email."""
        data = {
            "email": self.user_email,
            "password": "NewStrongPassword123!",
            "password_confirm": "NewStrongPassword123!",
        }
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        """Test logging in with valid credentials returns JWT tokens."""
        data = {"email": self.user_email, "password": self.user_password}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access_token", response.data["data"])
        self.assertIn("refresh_token", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], self.user_email)

    def test_login_invalid_password(self):
        """Test login fails with incorrect password."""
        data = {"email": self.user_email, "password": "WrongPassword!"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Test login fails with non-existent email."""
        data = {"email": "nobody@example.com", "password": "AnyPassword123!"}
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh_and_rotation(self):
        """Test refreshing token returns a new access & refresh token, and blacklists old refresh token."""
        # 1. Login to get tokens
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": self.user_password}, format="json")
        refresh_token = login_res.data["data"]["refresh_token"]

        # 2. Refresh tokens
        refresh_res = self.client.post(self.refresh_url, {"refresh_token": refresh_token}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        new_access = refresh_res.data["data"]["access_token"]
        new_refresh = refresh_res.data["data"]["refresh_token"]
        self.assertTrue(new_access)
        self.assertTrue(new_refresh)
        self.assertNotEqual(refresh_token, new_refresh)

        # 3. Old refresh token should now be blacklisted
        failed_res = self.client.post(self.refresh_url, {"refresh_token": refresh_token}, format="json")
        self.assertEqual(failed_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_token(self):
        """Test logout blacklists the provided refresh token."""
        # Login
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": self.user_password}, format="json")
        access_token = login_res.data["data"]["access_token"]
        refresh_token = login_res.data["data"]["refresh_token"]

        # Logout with auth header
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_res = self.client.post(self.logout_url, {"refresh_token": refresh_token}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Try to refresh with blacklisted token
        self.client.credentials()
        failed_res = self.client.post(self.refresh_url, {"refresh_token": refresh_token}, format="json")
        self.assertEqual(failed_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_authenticated(self):
        """Test GET /auth/me/ returns current user details."""
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": self.user_password}, format="json")
        access_token = login_res.data["data"]["access_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["email"], self.user_email)
        self.assertEqual(res.data["data"]["role"], UserRole.CITIZEN)

    def test_me_endpoint_unauthenticated(self):
        """Test GET /auth/me/ without token fails with 401."""
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_success(self):
        """Test changing password with valid current password."""
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": self.user_password}, format="json")
        access_token = login_res.data["data"]["access_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        change_res = self.client.post(
            self.change_password_url,
            {
                "current_password": self.user_password,
                "new_password": "NewStrongPassword456!",
                "new_password_confirm": "NewStrongPassword456!",
            },
            format="json",
        )
        self.assertEqual(change_res.status_code, status.HTTP_200_OK)

        # Test logging in with new password
        self.client.credentials()
        login_new = self.client.post(self.login_url, {"email": self.user_email, "password": "NewStrongPassword456!"}, format="json")
        self.assertEqual(login_new.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_current(self):
        """Test changing password fails when current password is wrong."""
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": self.user_password}, format="json")
        access_token = login_res.data["data"]["access_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        change_res = self.client.post(
            self.change_password_url,
            {
                "current_password": "IncorrectPassword!",
                "new_password": "NewStrongPassword456!",
                "new_password_confirm": "NewStrongPassword456!",
            },
            format="json",
        )
        self.assertEqual(change_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_with_otp(self):
        """Test verifying email with 6-digit OTP code."""
        otp = EmailVerificationOTP.objects.create(
            user=self.user,
            otp_code="654321",
            purpose="EMAIL_VERIFY",
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        res = self.client.post(
            self.verify_email_url,
            {"email": self.user_email, "otp_code": "654321"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_forgot_and_reset_password_flow(self):
        """Test complete forgot-password OTP generation and reset password flow."""
        # 1. Forgot password request
        forgot_res = self.client.post(self.forgot_password_url, {"email": self.user_email}, format="json")
        self.assertEqual(forgot_res.status_code, status.HTTP_200_OK)

        # Get generated OTP from DB
        otp = EmailVerificationOTP.objects.filter(user=self.user, purpose="PASSWORD_RESET").first()
        self.assertIsNotNone(otp)

        # 2. Reset password using OTP
        reset_res = self.client.post(
            self.reset_password_url,
            {
                "email": self.user_email,
                "otp_code": otp.otp_code,
                "new_password": "BrandNewPassword789!",
                "new_password_confirm": "BrandNewPassword789!",
            },
            format="json",
        )
        self.assertEqual(reset_res.status_code, status.HTTP_200_OK)

        # 3. Login with newly reset password
        login_res = self.client.post(self.login_url, {"email": self.user_email, "password": "BrandNewPassword789!"}, format="json")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
