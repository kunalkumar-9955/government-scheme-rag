"""
apps/users/tests.py — Tests for User Profiles & RBAC Authorization
"""
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.authentication.models import CustomUser
from apps.users.models import UserProfile, SocialCategory, OccupationCategory, EducationLevel
from core.permissions import UserRole


class UserProfileAndRBACTests(APITestCase):
    def setUp(self):
        self.profile_url = reverse("my-profile")
        self.users_list_url = reverse("user-list")

        # Create Citizen User
        self.citizen = CustomUser.objects.create_user(
            email="citizen_user@example.com",
            password="CitizenPassword123!",
            role=UserRole.CITIZEN,
        )

        # Create Admin User
        self.admin = CustomUser.objects.create_user(
            email="admin_user@example.com",
            password="AdminPassword123!",
            role=UserRole.ADMIN,
            is_staff=True,
        )

        # Create Super Admin User
        self.superadmin = CustomUser.objects.create_superuser(
            email="superadmin_user@example.com",
            password="SuperPassword123!",
        )

    def test_get_profile_auto_creation(self):
        """Test GET /users/me/profile/ creates a default profile if none exists."""
        self.client.force_authenticate(user=self.citizen)
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        self.assertEqual(res.data["data"]["user_email"], "citizen_user@example.com")
        self.assertEqual(res.data["data"]["user_role"], UserRole.CITIZEN)
        self.assertEqual(res.data["data"]["profile_completion_score"], 0)

    def test_update_profile_demographics_and_completion_score(self):
        """Test PATCH /users/me/profile/ updates demographic data and calculates completion score."""
        self.client.force_authenticate(user=self.citizen)
        update_data = {
            "full_name": "Ramesh Kumar",
            "date_of_birth": "1990-05-15",
            "gender": "MALE",
            "state": "UP",
            "district": "Lucknow",
            "pincode": "226001",
            "is_urban": False,
            "social_category": "OBC",
            "annual_income": "250000.00",
            "occupation": "FARMER",
            "education_level": "SECONDARY",
            "is_bpl": True,
            "family_size": 4,
            "has_disability": False,
        }
        res = self.client.patch(self.profile_url, update_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["full_name"], "Ramesh Kumar")
        self.assertEqual(res.data["data"]["state"], "UP")
        self.assertEqual(res.data["data"]["state_display"], "Uttar Pradesh")
        self.assertGreater(res.data["data"]["profile_completion_score"], 60)
        self.assertIsNotNone(res.data["data"]["age"])

    def test_citizen_cannot_list_all_users(self):
        """Test Citizen cannot access admin endpoint GET /users/."""
        self.client.force_authenticate(user=self.citizen)
        res = self.client.get(self.users_list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_all_users(self):
        """Test Admin can access GET /users/."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(self.users_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        self.assertGreaterEqual(res.data["count"], 3)

    def test_only_superadmin_can_change_role(self):
        """Test only SuperAdmin can change user roles."""
        role_url = reverse("user-change-role", kwargs={"user_id": str(self.citizen.id)})

        # 1. Citizen tries -> 403
        self.client.force_authenticate(user=self.citizen)
        res_citizen = self.client.patch(role_url, {"role": UserRole.ADMIN}, format="json")
        self.assertEqual(res_citizen.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Admin tries -> 403 (needs SuperAdmin)
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.patch(role_url, {"role": UserRole.ADMIN}, format="json")
        self.assertEqual(res_admin.status_code, status.HTTP_403_FORBIDDEN)

        # 3. SuperAdmin tries -> 200
        self.client.force_authenticate(user=self.superadmin)
        res_super = self.client.patch(role_url, {"role": UserRole.ADMIN}, format="json")
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.role, UserRole.ADMIN)

    def test_admin_deactivate_user(self):
        """Test Admin can deactivate a citizen account."""
        deactivate_url = reverse("user-deactivate", kwargs={"user_id": str(self.citizen.id)})

        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(deactivate_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.citizen.refresh_from_db()
        self.assertFalse(self.citizen.is_active)

    def test_admin_cannot_deactivate_self(self):
        """Test Admin cannot deactivate their own account."""
        deactivate_url = reverse("user-deactivate", kwargs={"user_id": str(self.admin.id)})

        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(deactivate_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
