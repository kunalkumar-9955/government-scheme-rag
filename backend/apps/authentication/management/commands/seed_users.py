"""
apps/authentication/management/commands/seed_users.py
-----------------------------------------------------
Command to seed initial SuperAdmin, Admin, and Citizen test/demo accounts.
"""
from django.core.management.base import BaseCommand
from apps.authentication.models import CustomUser
from apps.users.models import UserProfile
from core.permissions import UserRole


class Command(BaseCommand):
    help = "Seed initial SuperAdmin, Admin, and Citizen demo accounts."

    def handle(self, *args, **options):
        # 1. Super Admin
        super_email = "superadmin@govscheme.ai"
        super_user, created = CustomUser.objects.get_or_create(
            email=super_email,
            defaults={
                "role": UserRole.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        super_user.set_password("SuperAdminPass123!")
        super_user.role = UserRole.SUPER_ADMIN
        super_user.is_staff = True
        super_user.is_superuser = True
        super_user.is_active = True
        super_user.is_email_verified = True
        super_user.save()

        UserProfile.objects.get_or_create(
            user=super_user,
            defaults={"full_name": "Chief System Administrator", "state": "DL", "district": "New Delhi"},
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Ready SuperAdmin: {super_email} / SuperAdminPass123!"))

        # 2. Scheme Admin
        admin_email = "admin@govscheme.ai"
        admin_user, created = CustomUser.objects.get_or_create(
            email=admin_email,
            defaults={
                "role": UserRole.ADMIN,
                "is_staff": True,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        admin_user.set_password("AdminPass123!")
        admin_user.role = UserRole.ADMIN
        admin_user.is_staff = True
        admin_user.is_active = True
        admin_user.is_email_verified = True
        admin_user.save()

        UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={"full_name": "Welfare Scheme Officer", "state": "DL", "district": "Central Delhi"},
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Ready Admin: {admin_email} / AdminPass123!"))

        # 3. Main Demo Citizen (demo@govscheme.ai)
        demo_email = "demo@govscheme.ai"
        demo_user, created = CustomUser.objects.get_or_create(
            email=demo_email,
            defaults={
                "role": UserRole.CITIZEN,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        demo_user.set_password("DemoPass123!")
        demo_user.role = UserRole.CITIZEN
        demo_user.is_active = True
        demo_user.is_email_verified = True
        demo_user.save()

        profile, _ = UserProfile.objects.get_or_create(
            user=demo_user,
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
        self.stdout.write(self.style.SUCCESS(f"[OK] Ready Demo Citizen: {demo_email} / DemoPass123!"))

        # 4. Alternative Citizen (citizen@example.com)
        citizen_email = "citizen@example.com"
        citizen_user, created = CustomUser.objects.get_or_create(
            email=citizen_email,
            defaults={
                "role": UserRole.CITIZEN,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        citizen_user.set_password("CitizenPass123!")
        citizen_user.role = UserRole.CITIZEN
        citizen_user.is_active = True
        citizen_user.is_email_verified = True
        citizen_user.save()

        UserProfile.objects.get_or_create(
            user=citizen_user,
            defaults={
                "full_name": "Pooja Verma",
                "date_of_birth": "1998-03-15",
                "gender": "FEMALE",
                "state": "BR",
                "district": "Patna",
                "pincode": "800001",
                "social_category": "GENERAL",
                "annual_income": "120000.00",
                "occupation": "STUDENT",
                "education_level": "GRADUATE",
                "is_bpl": False,
                "family_size": 3,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Ready Citizen: {citizen_email} / CitizenPass123!"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] All Demo accounts configured and verified successfully!"))
