"""Management command: create default development accounts with email logins.

Usage:
    python manage.py create_default_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from polls.models import UserProfile


class Command(BaseCommand):
    help = "Create default development users (superadmin@gmail.com, admin01admin@gmail.com, user01@gmail.com)"

    def _make_user(self, email, password, role, is_staff=False, is_superuser=False):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=email, defaults={"email": email})

        if created:
            user.set_password(password)
            user.is_staff      = is_staff
            user.is_superuser  = is_superuser
            user.is_active     = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created user:  {email}  ({role})"))
        else:
            if user.email != email:
                user.email = email
                user.save()
            self.stdout.write(self.style.WARNING(f"  [--] Already exists: {email}  ({role})"))

        # Create / update UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        if profile.role != role:
            profile.role = role
            profile.save()
            self.stdout.write(f"     -> Updated role to {role}")

        return user

    def handle(self, *args, **options):
        self.stdout.write("\n" + "-" * 50)
        self.stdout.write("  VoteHub -- Creating default development users")
        self.stdout.write("-" * 50)

        # 1. Super Admin
        self._make_user(
            email        = "superadmin@gmail.com",
            password     = "SuperAdmin@123",
            role         = UserProfile.SUPER_ADMIN,
            is_staff     = True,
            is_superuser = True,
        )

        # 2. Admin
        self._make_user(
            email     = "admin01admin@gmail.com",
            password  = "Admin@123",
            role      = UserProfile.ADMIN,
            is_staff  = True,
        )

        # 3. Voter / Regular User
        self._make_user(
            email    = "user01@gmail.com",
            password = "User@123",
            role     = UserProfile.USER,
        )

        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS("  Done! You can now login with these credentials.\n"))
        self.stdout.write("  superadmin@gmail.com      /  SuperAdmin@123  -> Super Admin portal")
        self.stdout.write("  admin01admin@gmail.com    /  Admin@123       -> Admin portal")
        self.stdout.write("  user01@gmail.com          /  User@123        -> Voter portal\n")
