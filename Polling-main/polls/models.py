from django.db import models
from django.utils import timezone
import datetime
from django.contrib import admin
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published", null=True, blank=True)
    description = models.TextField(blank=True, default="")
    poll_type = models.CharField(
        max_length=20,
        choices=[('single', 'Single Choice'), ('multiple', 'Multiple Choice')],
        default='single'
    )
    status = models.CharField(
        max_length=20,
        choices=[('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed'), ('archived', 'Archived')],
        default='active'
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    visibility = models.CharField(
        max_length=10,
        choices=[('public', 'Public'), ('private', 'Private')],
        default='public'
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.question_text

    @admin.display(
        boolean=True,
        ordering="pub_date",
        description="Published recently?",
    )
    def was_published_recently(self):
        if not self.pub_date:
            return False
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text


class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')

    def __str__(self):
        return f"{self.user.username} voted on {self.question.question_text}"


# ──────────────────────────────────────────────────────────────
#  USER PROFILE — Role-Based Access Control
# ──────────────────────────────────────────────────────────────

class UserProfile(models.Model):
    """Extends the built-in User model with an explicit role for RBAC.

    Role hierarchy:
        SUPER_ADMIN — Full system control, can manage admins.
        ADMIN       — Poll & user management within scope.
        USER        — Voter; can only browse and cast votes.
    """

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN       = "ADMIN"
    USER        = "USER"

    ROLE_CHOICES = [
        (SUPER_ADMIN, "Super Admin"),
        (ADMIN,       "Admin"),
        (USER,        "User / Voter"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=USER,
        db_index=True,
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    # ── Convenience properties ────────────────────────────────────────

    @property
    def is_super_admin(self):
        return self.role == self.SUPER_ADMIN

    @property
    def is_admin_or_above(self):
        return self.role in (self.ADMIN, self.SUPER_ADMIN)

    @property
    def is_voter(self):
        return self.role == self.USER


# ── Module-level helper used by decorators and views ─────────────────

def get_user_role(user):
    """Return the user's role string.

    Priority:
      1. UserProfile.role  (explicit DB role)
      2. Email-based check (fallback)
      3. 'USER'            (default)
    """
    if not user or not user.is_authenticated:
        return UserProfile.USER
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        pass
    email = (user.email or "").strip().lower()
    if email == "superadmin@gmail.com":
        return UserProfile.SUPER_ADMIN
    if email.endswith("admin@gmail.com"):
        return UserProfile.ADMIN
    return UserProfile.USER

