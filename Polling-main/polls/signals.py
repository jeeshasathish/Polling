"""
Signals for the polls app.

Auto-creates or syncs a UserProfile whenever a User is saved, based on email-based role detection rules.
Super Admin and Admin accounts must use Gmail addresses.
- superadmin@gmail.com  →  SUPER_ADMIN
- xxxxxadmin@gmail.com   →  ADMIN (any Gmail ending with admin@gmail.com)
- All other emails       →  USER
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_sync_user_profile(sender, instance, created, **kwargs):
    """
    Ensure each user has a UserProfile, and automatically assign the correct role
    and user flags (is_staff, is_superuser) based on email rules.
    """
    email = (instance.email or "").strip().lower()
    
    # Auto-populate empty email field from username if username is an email address
    if not email and "@" in instance.username:
        email = instance.username.strip().lower()
        sender.objects.filter(pk=instance.pk).update(email=email)

    if email == "superadmin@gmail.com":

        role = UserProfile.SUPER_ADMIN
        is_staff = True
        is_superuser = True
    elif email.endswith("admin@gmail.com"):
        role = UserProfile.ADMIN
        is_staff = True
        is_superuser = False
    else:
        role = UserProfile.USER
        is_staff = False
        is_superuser = False

    # Get or create profile
    profile, profile_created = UserProfile.objects.get_or_create(
        user=instance, defaults={"role": role}
    )

    # If the user's email changed, update the DB role to match
    if not profile_created and profile.role != role:
        profile.role = role
        profile.save()

    # Sync Django flags (is_staff, is_superuser) to match
    if instance.is_staff != is_staff or instance.is_superuser != is_superuser:
        sender.objects.filter(pk=instance.pk).update(
            is_staff=is_staff,
            is_superuser=is_superuser
        )
