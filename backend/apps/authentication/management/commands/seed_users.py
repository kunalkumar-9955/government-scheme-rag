"""
apps/authentication/management/commands/seed_users.py
-----------------------------------------------------
Command to seed initial SuperAdmin, Admin, and Citizen test accounts.
"""
from django.core.management.base import BaseCommand
from apps.authentication.models import CustomUser
from apps.users.models import UserProfile
from core.permissions import UserRole


class Command(BaseCommand):
    help = "Seed initial SuperAdmin, Admin, and Citizen test accounts."

    def handle(self, *args, **options):
        # 1. Super Admin
        super_email = "superadmin@govscheme.ai"
        if not CustomUser.objects.filter(email=super_email).exists():
            super_user = CustomUser.objects.create_superuser(
                email=super_email,
                password="SuperAdminPass123!",
                role=UserRole.SUPER_ADMIN,
                is_email_verified=True,
            )
            UserProfile.objects.get_or_create(
                user=super_user,
                defaults={"full_name": "Chief System Administrator", "state": "DL", "district": "New Delhi"},
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Created SuperAdmin: {super_email} / SuperAdminPass123!"))
        else:
            self.stdout.write(f"[INFO] SuperAdmin '{super_email}' already exists.")

        # 2. Scheme Admin
        admin_email = "admin@govscheme.ai"
        if not CustomUser.objects.filter(email=admin_email).exists():
            admin_user = CustomUser.objects.create_user(
                email=admin_email,
                password="AdminPass123!",
                role=UserRole.ADMIN,
                is_staff=True,
                is_email_verified=True,
            )
            UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={"full_name": "Welfare Scheme Officer", "state": "DL", "district": "Central Delhi"},
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Created Admin: {admin_email} / AdminPass123!"))
        else:
            self.stdout.write(f"[INFO] Admin '{admin_email}' already exists.")

        # 3. Sample Citizen User
        citizen_email = "citizen@example.com"
        if not CustomUser.objects.filter(email=citizen_email).exists():
            citizen_user = CustomUser.objects.create_user(
                email=citizen_email,
                password="CitizenPass123!",
                role=UserRole.CITIZEN,
                is_email_verified=True,
            )
            profile, _ = UserProfile.objects.get_or_create(
                user=citizen_user,
                defaults={
                    "full_name": "Ramesh Kumar Sharma",
                    "date_of_birth": "1992-06-10",
                    "gender": "MALE",
                    "state": "UP",
                    "district": "Varanasi",
                    "pincode": "221001",
                    "social_category": "OBC",
                    "annual_income": "180000.00",
                    "occupation": "FARMER",
                    "education_level": "SECONDARY",
                    "is_bpl": True,
                    "family_size": 4,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Created Citizen: {citizen_email} / CitizenPass123! (Profile score: {profile.profile_completion_score}%)"))
        else:
            self.stdout.write(f"[INFO] Citizen '{citizen_email}' already exists.")

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Seed accounts ready for testing!"))
