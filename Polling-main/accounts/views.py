import os
import json
import urllib.request
import urllib.parse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages

from polls.models import UserProfile, get_user_role
from .forms import EmailUserCreationForm


def _role_redirect(user):
    """Return the correct named URL for the user's role dashboard."""
    role = get_user_role(user)
    if role == UserProfile.SUPER_ADMIN:
        return "polls:super_admin_dashboard"
    if role == UserProfile.ADMIN:
        return "polls:admin_dashboard"
    return "polls:user_dashboard"


def landing(request):
    """Public landing / hero page. Authenticated users go straight to their dashboard."""
    if request.user.is_authenticated:
        return redirect(_role_redirect(request.user))
    return render(request, "accounts/landing.html")


def register(request):
    """Registration page — creates USER (Voter) accounts only."""
    if request.user.is_authenticated:
        return redirect(_role_redirect(request.user))

    if request.method == "POST":
        form = EmailUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(
                user=user, defaults={"role": UserProfile.USER}
            )
            login(request, user, backend='polls.auth_backends.EmailBackend')
            messages.success(
                request,
                f"Welcome to VoteHub! Your account has been created."
            )
            return redirect("polls:user_dashboard")
    else:
        form = EmailUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Login — validates email + password then redirects to role-specific dashboard."""
    if request.user.is_authenticated:
        return redirect(_role_redirect(request.user))

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back!")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(_role_redirect(user))
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html")


def google_login(request):
    """Redirect to Google's OAuth2 login page."""
    from django.conf import settings
    from django.urls import reverse
    from django.http import HttpResponse

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID', ''))
    if not client_id:
        return HttpResponse(
            "Google SSO is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
            "in your environment variables or settings.py.",
            status=400
        )
    
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'email profile openid',
        'prompt': 'select_account',
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return redirect(google_auth_url)


def google_callback(request):
    """Handle callback from Google, exchange code for user profile."""
    from django.conf import settings
    from django.urls import reverse
    from django.contrib.auth import get_user_model, login

    code = request.GET.get('code')
    if not code:
        return redirect('login')

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID', ''))
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', os.environ.get('GOOGLE_CLIENT_SECRET', ''))
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))

    # Exchange authorization code for access token
    token_url = "https://oauth2.googleapis.com/token"
    post_data = urllib.parse.urlencode({
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(token_url, data=post_data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req) as response:
            token_data = json.loads(response.read().decode('utf-8'))
            
        access_token = token_data.get('access_token')
        if not access_token:
            messages.error(request, "Failed to retrieve access token from Google.")
            return redirect('login')
            
        # Get user info
        user_info_url = "https://openidconnect.googleapis.com/v1/userinfo"
        req_info = urllib.request.Request(user_info_url, method='GET')
        req_info.add_header('Authorization', f'Bearer {access_token}')
        
        with urllib.request.urlopen(req_info) as response_info:
            user_info = json.loads(response_info.read().decode('utf-8'))
            
        email = user_info.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Google login failed: email not provided.")
            return redirect('login')

        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')

        # Get or create user
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=User.objects.make_random_password()
            )

        # Log user in
        login(request, user, backend='polls.auth_backends.EmailBackend')
        messages.success(request, f"Successfully authenticated with Google. Welcome, {user.first_name or user.email}!")
        return redirect(_role_redirect(user))

    except Exception as e:
        messages.error(request, f"Google authentication error: {str(e)}")
        return redirect('login')


# ── Static Pages ─────────────────────────────────────────────────────────────

def about_us(request):
    return render(request, "accounts/about_us.html")

def help_center(request):
    return render(request, "accounts/help_center.html")

def privacy_policy(request):
    return render(request, "accounts/privacy_policy.html")

def terms_of_service(request):
    return render(request, "accounts/terms_of_service.html")

def contact_us(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        email = request.POST.get("email", "")
        message = request.POST.get("message", "")
        if name and email and message:
            messages.success(request, "Your inquiry has been received! Our support team will respond shortly.")
        else:
            messages.error(request, "Please fill in all fields before sending.")
        return redirect("contact_us")
    return render(request, "accounts/contact_us.html")

def faq(request):
    return render(request, "accounts/faq.html")

def feedback(request):
    if request.method == "POST":
        rating = request.POST.get("rating", "")
        comments = request.POST.get("comments", "")
        if rating:
            messages.success(request, "Thank you for your valuable feedback!")
        else:
            messages.error(request, "Please provide a rating before submitting.")
        return redirect("feedback")
    return render(request, "accounts/feedback.html")

