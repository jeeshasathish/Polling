from functools import wraps
from django.shortcuts import redirect, render
from django.conf import settings as django_settings

from .models import UserProfile, get_user_role


def super_admin_required(view_func):
    """Restrict view to SUPER_ADMIN only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{django_settings.LOGIN_URL}?next={request.path}")
        role = get_user_role(request.user)
        if role != UserProfile.SUPER_ADMIN:
            return render(
                request,
                "polls/403.html",
                {
                    "required_role": "Super Admin",
                    "redirect_url":  "/super-admin/dashboard/",
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Restrict view to ADMIN or SUPER_ADMIN."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{django_settings.LOGIN_URL}?next={request.path}")
        role = get_user_role(request.user)
        if role not in (UserProfile.ADMIN, UserProfile.SUPER_ADMIN):
            return render(
                request,
                "polls/403.html",
                {
                    "required_role": "Admin",
                    "redirect_url":  "/admin/dashboard/",
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def voter_required(view_func):
    """Restrict view to USER (Voter) only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{django_settings.LOGIN_URL}?next={request.path}")
        role = get_user_role(request.user)
        if role != UserProfile.USER:
            return render(
                request,
                "polls/403.html",
                {
                    "required_role": "Voter",
                    "redirect_url":  "/user/dashboard/",
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper
