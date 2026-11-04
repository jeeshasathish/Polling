from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages

from .models import Choice, Question, UserProfile, get_user_role, Category, Vote
from .decorators import admin_required, voter_required, super_admin_required
from .forms import QuestionForm, CategoryForm, AdminUserForm



# ──────────────────────────────────────────────────────────────
#  SMART ROLE ROUTER
# ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Smart router: reads UserProfile.role and redirects to correct portal."""
    role = get_user_role(request.user)
    if role == UserProfile.SUPER_ADMIN:
        return redirect("polls:super_admin_dashboard")
    if role == UserProfile.ADMIN:
        return redirect("polls:admin_dashboard")
    return redirect("polls:user_dashboard")


# ──────────────────────────────────────────────────────────────
#  SUPER ADMIN PORTAL
# ──────────────────────────────────────────────────────────────

@super_admin_required
def super_admin_dashboard(request):
    """Super Admin control centre — global stats, all users, all polls."""
    User = get_user_model()
    now     = timezone.now()
    cutoff  = now - timezone.timedelta(days=7)

    total_polls    = Question.objects.count()
    active_polls   = Question.objects.filter(pub_date__gt=cutoff, pub_date__lte=now).count()
    closed_polls   = Question.objects.filter(pub_date__lte=cutoff).count()
    upcoming_polls = Question.objects.filter(pub_date__gt=now).count()
    total_votes    = Choice.objects.aggregate(total=Sum("votes"))["total"] or 0

    total_users       = User.objects.count()
    super_admin_count = UserProfile.objects.filter(role=UserProfile.SUPER_ADMIN).count()
    admin_count       = UserProfile.objects.filter(role=UserProfile.ADMIN).count()
    voter_count       = UserProfile.objects.filter(role=UserProfile.USER).count()

    recent_polls = Question.objects.order_by("-pub_date")[:8]
    recent_users = User.objects.order_by("-date_joined")[:8]

    return render(request, "polls/super_admin_dashboard.html", {
        "total_polls":       total_polls,
        "active_polls":      active_polls,
        "closed_polls":      closed_polls,
        "upcoming_polls":    upcoming_polls,
        "total_votes":       total_votes,
        "total_users":       total_users,
        "super_admin_count": super_admin_count,
        "admin_count":       admin_count,
        "voter_count":       voter_count,
        "recent_polls":      recent_polls,
        "recent_users":      recent_users,
    })


@super_admin_required
def super_admin_users(request):
    """Super Admin — full user & role management panel."""
    User = get_user_model()
    users = User.objects.select_related("profile").order_by("-date_joined")
    voter_count       = UserProfile.objects.filter(role=UserProfile.USER).count()
    admin_count       = UserProfile.objects.filter(role=UserProfile.ADMIN).count()
    super_admin_count = UserProfile.objects.filter(role=UserProfile.SUPER_ADMIN).count()

    return render(request, "polls/super_admin_users.html", {
        "users":             users,
        "voter_count":       voter_count,
        "admin_count":       admin_count,
        "super_admin_count": super_admin_count,
    })


# ──────────────────────────────────────────────────────────────
#  ADMIN PORTAL
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    """Admin portal dashboard — polls overview + recent users."""
    User = get_user_model()
    now    = timezone.now()
    cutoff = now - timezone.timedelta(days=7)

    total_polls    = Question.objects.count()
    active_polls   = Question.objects.filter(pub_date__gt=cutoff, pub_date__lte=now).count()
    closed_polls   = Question.objects.filter(pub_date__lte=cutoff).count()
    upcoming_polls = Question.objects.filter(pub_date__gt=now).count()
    total_users    = User.objects.count()
    total_votes    = Choice.objects.aggregate(total=Sum("votes"))["total"] or 0

    recent_polls = Question.objects.order_by("-pub_date")[:6]
    recent_users = User.objects.order_by("-date_joined")[:6]

    return render(request, "polls/admin_dashboard.html", {
        "total_polls":    total_polls,
        "active_polls":   active_polls,
        "closed_polls":   closed_polls,
        "upcoming_polls": upcoming_polls,
        "total_users":    total_users,
        "total_votes":    total_votes,
        "recent_polls":   recent_polls,
        "recent_users":   recent_users,
    })


@super_admin_required
def manage_users(request):
    """Redirect to the consolidated super admin user management view."""
    return redirect("polls:super_admin_users")


# ──────────────────────────────────────────────────────────────
#  USER (VOTER) PORTAL
# ──────────────────────────────────────────────────────────────

@login_required
def user_dashboard(request):
    """Voter dashboard — polls grid, ending-soon panel, and profile summary."""
    role = get_user_role(request.user)
    # Staff / Admin visiting voter dashboard → redirect to their portal
    if role == UserProfile.SUPER_ADMIN:
        return redirect("polls:super_admin_dashboard")
    if role == UserProfile.ADMIN:
        return redirect("polls:admin_dashboard")

    now    = timezone.now()
    cutoff = now - timezone.timedelta(days=7)

    available_polls = Question.objects.filter(pub_date__lte=now).order_by("-pub_date")[:9]
    ending_soon     = Question.objects.filter(
        pub_date__gt=cutoff, pub_date__lte=now
    ).order_by("pub_date")[:4]
    total_available = Question.objects.filter(pub_date__lte=now).count()
    active_count    = Question.objects.filter(pub_date__gt=cutoff, pub_date__lte=now).count()
    user_joined     = request.user.date_joined.strftime("%B %d, %Y")

    return render(request, "polls/user_dashboard.html", {
        "available_polls": available_polls,
        "ending_soon":     ending_soon,
        "total_available": total_available,
        "active_count":    active_count,
        "user_joined":     user_joined,
    })


# ──────────────────────────────────────────────────────────────
#  POLLS LIST / DETAIL / RESULTS / VOTE
# ──────────────────────────────────────────────────────────────

@method_decorator(login_required, name="dispatch")
class IndexView(generic.ListView):
    template_name        = "polls/index.html"
    context_object_name  = "latest_question_list"

    def get_queryset(self):
        now = timezone.now()
        queryset = Question.objects.all()

        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(question_text__icontains=search_query)

        status_filter = self.request.GET.get("filter", "").strip()
        if status_filter == "upcoming":
            queryset = queryset.filter(pub_date__gt=now)
        elif status_filter == "closed":
            cutoff = now - timezone.timedelta(days=7)
            queryset = queryset.filter(pub_date__lte=cutoff)
        elif status_filter == "active":
            cutoff = now - timezone.timedelta(days=7)
            queryset = queryset.filter(pub_date__gt=cutoff, pub_date__lte=now)
        else:
            queryset = queryset.filter(pub_date__lte=now)

        sort_by = self.request.GET.get("sort", "").strip()
        if sort_by == "alphabetical":
            queryset = queryset.order_by("question_text")
        elif sort_by == "popular":
            queryset = queryset.annotate(
                total_votes=Sum("choice__votes")
            ).order_by("-total_votes", "-pub_date")
        elif sort_by == "oldest":
            queryset = queryset.order_by("pub_date")
        else:
            queryset = queryset.order_by("-pub_date")

        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_val"] = self.request.GET.get("search", "")
        ctx["filter_val"] = self.request.GET.get("filter", "")
        ctx["sort_val"]   = self.request.GET.get("sort", "")
        return ctx


@method_decorator(login_required, name="dispatch")
class DetailView(generic.DetailView):
    model            = Question
    template_name    = "polls/detail.html"

    def get_queryset(self):
        return Question.objects.filter(pub_date__lte=timezone.now())


@method_decorator(login_required, name="dispatch")
class ResultsView(generic.DetailView):
    model         = Question
    template_name = "polls/results.html"


@voter_required
def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    
    # Check if user has already voted
    if Vote.objects.filter(user=request.user, question=question).exists():
        messages.error(request, "You have already voted on this poll.")
        return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))

    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        return render(
            request,
            "polls/detail.html",
            {
                "question":      question,
                "error_message": "You didn't select a choice.",
            },
        )
    
    # Record Vote and increment counter within a transaction block for database integrity
    with transaction.atomic():
        Vote.objects.create(user=request.user, question=question, choice=selected_choice)
        selected_choice.votes = F("votes") + 1
        selected_choice.save()
    
    messages.success(request, "Your vote has been recorded successfully.")
    return HttpResponseRedirect(reverse("polls:results", args=(question.id,)))


# ──────────────────────────────────────────────────────────────
#  SHARED — PROFILE / SETTINGS
# ──────────────────────────────────────────────────────────────

@login_required
def profile(request):
    user_joined = request.user.date_joined.strftime("%B %d, %Y")
    role        = get_user_role(request.user)
    return render(request, "polls/profile.html", {
        "user_joined": user_joined,
        "user_role":   role,
    })


@super_admin_required
def settings(request):
    role = get_user_role(request.user)
    return render(request, "polls/settings.html", {"user_role": role})


# ──────────────────────────────────────────────────────────────
#  POLLING MODULE — ADMIN & SUPER ADMIN MANAGEMENT
# ──────────────────────────────────────────────────────────────

def _get_base_template(request):
    role = get_user_role(request.user)
    return "polls/base_super_admin.html" if role == UserProfile.SUPER_ADMIN else "polls/base_admin.html"


@admin_required
def admin_polls_list(request, status_filter=None):
    """List all polls with search, category filtering, and status filtering."""
    polls = Question.objects.all().select_related('category').order_by('-pub_date')

    # Get search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        polls = polls.filter(question_text__icontains=search_query)

    # Get status filter from url default args or GET param
    active_filter = status_filter or request.GET.get('status', '').strip().lower()
    if active_filter in ['draft', 'active', 'closed', 'archived']:
        polls = polls.filter(status=active_filter)

    # Get category filter
    cat_filter = request.GET.get('category', '').strip()
    if cat_filter:
        polls = polls.filter(category_id=cat_filter)

    categories = Category.objects.all()

    # Dynamic counts for summary cards
    draft_count = Question.objects.filter(status='draft').count()
    active_count = Question.objects.filter(status='active').count()
    closed_count = Question.objects.filter(status='closed').count()
    total_count = Question.objects.count()

    return render(request, "polls/admin_polls_list.html", {
        "polls": polls,
        "categories": categories,
        "search_val": search_query,
        "status_val": active_filter,
        "cat_val": cat_filter,
        "draft_count": draft_count,
        "active_count": active_count,
        "closed_count": closed_count,
        "total_count": total_count,
        "base_template": _get_base_template(request),
    })


@admin_required
def admin_polls_create(request):
    """Create a new poll with choices."""
    if request.method == "POST":
        form = QuestionForm(request.POST)
        choices = request.POST.getlist('choices')
        
        # Clean choices list (remove empty options)
        choices = [c.strip() for c in choices if c.strip()]

        if form.is_valid():
            if not choices:
                form.add_error(None, "You must provide at least one answer option.")
            else:
                poll = form.save(commit=False)
                
                # If publishing, set pub_date
                if poll.status == 'active' and not poll.pub_date:
                    poll.pub_date = timezone.now()
                    poll.start_date = timezone.now()
                elif poll.status == 'closed' and not poll.end_date:
                    poll.end_date = timezone.now()

                poll.save()

                # Save choices
                for choice_text in choices:
                    Choice.objects.create(question=poll, choice_text=choice_text)

                messages.success(request, f"Poll '{poll.question_text}' created successfully.")
                return redirect("polls:admin_polls_list")
    else:
        form = QuestionForm(initial={'status': 'draft', 'visibility': 'public'})
        choices = []

    categories = Category.objects.all()
    return render(request, "polls/admin_polls_create.html", {
        "form": form,
        "choices": choices,
        "categories": categories,
        "base_template": _get_base_template(request),
    })


@admin_required
def admin_polls_edit(request, pk):
    """Edit an existing poll and its choices."""
    poll = get_object_or_404(Question, pk=pk)
    
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=poll)
        choices = request.POST.getlist('choices')
        choices = [c.strip() for c in choices if c.strip()]

        if form.is_valid():
            if not choices:
                form.add_error(None, "You must provide at least one answer option.")
            else:
                updated_poll = form.save(commit=False)
                
                # Update pub_date/start_date if status changes to active
                if updated_poll.status == 'active' and not updated_poll.pub_date:
                    updated_poll.pub_date = timezone.now()
                    updated_poll.start_date = timezone.now()
                elif updated_poll.status == 'closed' and not updated_poll.end_date:
                    updated_poll.end_date = timezone.now()

                updated_poll.save()

                # Sync choices
                existing_choices = {c.choice_text: c.votes for c in poll.choice_set.all()}
                poll.choice_set.all().delete()
                
                for choice_text in choices:
                    votes = existing_choices.get(choice_text, 0)
                    Choice.objects.create(question=poll, choice_text=choice_text, votes=votes)

                messages.success(request, f"Poll '{updated_poll.question_text}' updated successfully.")
                return redirect("polls:admin_polls_list")
    else:
        form = QuestionForm(instance=poll)
        choices = [c.choice_text for c in poll.choice_set.all()]

    categories = Category.objects.all()
    return render(request, "polls/admin_polls_edit.html", {
        "poll": poll,
        "form": form,
        "choices": choices,
        "categories": categories,
        "base_template": _get_base_template(request),
    })


@admin_required
def admin_polls_delete(request, pk):
    """Delete a poll."""
    poll = get_object_or_404(Question, pk=pk)
    title = poll.question_text
    poll.delete()
    messages.success(request, f"Poll '{title}' deleted successfully.")
    return redirect("polls:admin_polls_list")


@admin_required
def admin_polls_publish(request, pk):
    """Change a draft poll status to active."""
    poll = get_object_or_404(Question, pk=pk)
    poll.status = 'active'
    poll.pub_date = timezone.now()
    poll.start_date = timezone.now()
    poll.save()
    messages.success(request, f"Poll '{poll.question_text}' is now active/published.")
    return redirect("polls:admin_polls_list")


@admin_required
def admin_polls_close(request, pk):
    """Close an active poll."""
    poll = get_object_or_404(Question, pk=pk)
    poll.status = 'closed'
    poll.end_date = timezone.now()
    poll.save()
    messages.success(request, f"Poll '{poll.question_text}' is now closed.")
    return redirect("polls:admin_polls_list")


@admin_required
def admin_polls_duplicate(request, pk):
    """Duplicate a poll as a draft."""
    poll = get_object_or_404(Question, pk=pk)
    
    # Create new question
    new_poll = Question.objects.create(
        question_text=f"Copy of {poll.question_text}",
        description=poll.description,
        poll_type=poll.poll_type,
        status='draft',
        visibility=poll.visibility,
        category=poll.category,
    )
    
    # Duplicate choices
    for choice in poll.choice_set.all():
        Choice.objects.create(question=new_poll, choice_text=choice.choice_text, votes=0)

    messages.success(request, f"Poll duplicated as '{new_poll.question_text}'.")
    return redirect("polls:admin_polls_list")


# ──────────────────────────────────────────────────────────────
#  POLL CATEGORIES CRUD
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_polls_categories(request):
    """Manage categories."""
    categories = Category.objects.all().order_by('name')
    form = CategoryForm()
    
    return render(request, "polls/admin_polls_categories.html", {
        "categories": categories,
        "form": form,
        "base_template": _get_base_template(request),
    })


@admin_required
def admin_category_create(request):
    """Create a new category."""
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created.")
        else:
            messages.error(request, "Failed to create category. Ensure the name is unique.")
    return redirect("polls:admin_polls_categories")


@admin_required
def admin_category_edit(request, pk):
    """Edit a category."""
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{cat.name}' updated.")
        else:
            messages.error(request, "Failed to update category.")
    return redirect("polls:admin_polls_categories")


@admin_required
def admin_category_delete(request, pk):
    """Delete a category."""
    cat = get_object_or_404(Category, pk=pk)
    name = cat.name
    cat.delete()
    messages.success(request, f"Category '{name}' deleted.")
    return redirect("polls:admin_polls_categories")


# ──────────────────────────────────────────────────────────────
#  VOTING HISTORY — USER PORTAL
# ──────────────────────────────────────────────────────────────

@voter_required
def user_history(request):
    """Display user's voting history."""
    votes = Vote.objects.filter(user=request.user).select_related('question', 'choice').order_by('-voted_at')
    return render(request, "polls/user_history.html", {
        "votes": votes,
    })


# ──────────────────────────────────────────────────────────────
#  POLL ANALYTICS — ADMIN & SUPER ADMIN
# ──────────────────────────────────────────────────────────────

@admin_required
def polls_analytics(request):
    """Display global analytics summary."""
    total_polls = Question.objects.count()
    total_votes = Vote.objects.count()
    
    # Calculate votes per category
    categories = Category.objects.all()
    cat_analytics = []
    for cat in categories:
        votes_count = Vote.objects.filter(question__category=cat).count()
        cat_analytics.append({
            "name": cat.name,
            "votes": votes_count,
        })
    
    # Top polls by response count
    top_polls = Question.objects.all().order_by('-pub_date')[:5]
    top_polls_list = []
    for poll in top_polls:
        poll_votes = Vote.objects.filter(question=poll).count()
        top_polls_list.append({
            "question_text": poll.question_text,
            "status": poll.status,
            "votes": poll_votes,
        })
        
    # Sort top_polls_list by votes desc
    top_polls_list = sorted(top_polls_list, key=lambda x: x['votes'], reverse=True)

    return render(request, "polls/admin_analytics.html", {
        "total_polls": total_polls,
        "total_votes": total_votes,
        "cat_analytics": cat_analytics,
        "top_polls": top_polls_list,
        "base_template": _get_base_template(request),
    })


@admin_required
def download_analytics_report(request):
    """Generate and download a CSV report of platform analytics."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="votehub_platform_analytics.csv"'

    writer = csv.writer(response)
    
    # Header Section
    writer.writerow(["VOTEHUB PLATFORM ANALYTICS REPORT"])
    writer.writerow(["Generated On", timezone.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # Global Metrics
    writer.writerow(["GLOBAL METRICS"])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Survey Programs", Question.objects.count()])
    writer.writerow(["Total Responses Cast", Vote.objects.count()])
    writer.writerow([])
    
    # Responses by Category
    writer.writerow(["RESPONSES BY CATEGORY"])
    writer.writerow(["Category Name", "Total Votes"])
    categories = Category.objects.all()
    for cat in categories:
        votes_count = Vote.objects.filter(question__category=cat).count()
        writer.writerow([cat.name, votes_count])
    writer.writerow([])
    
    # Popular Polls Details
    writer.writerow(["MOST POPULAR SURVEYS"])
    writer.writerow(["Question Text", "Status", "Total Votes", "Created Date"])
    polls = Question.objects.all().order_by('-pub_date')
    polls_list = []
    for poll in polls:
        poll_votes = Vote.objects.filter(question=poll).count()
        polls_list.append({
            "question_text": poll.question_text,
            "status": poll.status,
            "votes": poll_votes,
            "pub_date": poll.pub_date.strftime("%Y-%m-%d %H:%M:%S") if poll.pub_date else "Not Published"
        })
    # Sort by votes desc
    polls_list = sorted(polls_list, key=lambda x: x['votes'], reverse=True)
    for p in polls_list:
        writer.writerow([p["question_text"], p["status"], p["votes"], p["pub_date"]])
        
    return response


@admin_required
def polls_analytics_report(request):
    """Generate a printable/PDF report for platform analytics."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    total_polls = Question.objects.count()
    total_votes = Vote.objects.count()
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    draft_polls = Question.objects.filter(status="draft").count()
    active_polls = Question.objects.filter(status="active").count()
    closed_polls = Question.objects.filter(status="closed").count()
    
    # Category votes
    categories = Category.objects.all()
    cat_analytics = []
    for cat in categories:
        votes_count = Vote.objects.filter(question__category=cat).count()
        polls_count = Question.objects.filter(category=cat).count()
        cat_analytics.append({
            "name": cat.name,
            "votes": votes_count,
            "polls": polls_count,
        })
    
    # Top polls
    top_polls = Question.objects.all().order_by('-pub_date')
    top_polls_list = []
    for poll in top_polls:
        poll_votes = Vote.objects.filter(question=poll).count()
        top_polls_list.append({
            "question_text": poll.question_text,
            "status": poll.status,
            "votes": poll_votes,
            "pub_date": poll.pub_date,
        })
    top_polls_list = sorted(top_polls_list, key=lambda x: x['votes'], reverse=True)
    
    # User roles details
    user_list = []
    for u in User.objects.all().order_by('-date_joined')[:10]:
        role = "Super Admin" if u.is_superuser else ("Admin" if u.is_staff else "Voter")
        user_list.append({
            "email": u.email or u.username,
            "role": role,
            "is_active": u.is_active,
            "date_joined": u.date_joined,
        })

    # Calculations for summary metrics
    # Productivity percentage = (closed_polls + active_polls) / total_polls * 100
    prod_percent = round((closed_polls + active_polls) / total_polls * 100, 1) if total_polls > 0 else 0.0

    return render(request, "polls/admin_analytics_report.html", {
        "total_polls": total_polls,
        "total_votes": total_votes,
        "total_users": total_users,
        "active_users": active_users,
        "draft_polls": draft_polls,
        "active_polls": active_polls,
        "closed_polls": closed_polls,
        "cat_analytics": cat_analytics,
        "top_polls": top_polls_list,
        "user_list": user_list,
        "prod_percent": prod_percent,
        "generation_time": timezone.now(),
        "generated_by": request.user.email or request.user.username,
    })




# ──────────────────────────────────────────────────────────────
#  ADMIN MANAGEMENT — SUPER ADMIN ONLY
# ──────────────────────────────────────────────────────────────

@super_admin_required
def super_admin_admins(request):
    """List all administrators."""
    admins = get_user_model().objects.filter(profile__role=UserProfile.ADMIN).order_by('-date_joined')
    return render(request, "polls/super_admin_admins.html", {
        "admins": admins,
    })


@super_admin_required
def super_admin_admins_create(request):
    """Create a new Admin user."""
    if request.method == "POST":
        form = AdminUserForm(request.POST)
        if form.is_valid():
            admin_user = form.save()
            messages.success(request, f"Admin account '{admin_user.email}' created successfully.")
            return redirect("polls:super_admin_admins")
    else:
        form = AdminUserForm()

    return render(request, "polls/super_admin_admins_form.html", {
        "form": form,
        "title": "Create Admin Account",
    })


@super_admin_required
def super_admin_admins_edit(request, pk):
    """Edit an Admin user's details."""
    admin_user = get_object_or_404(get_user_model(), pk=pk, profile__role=UserProfile.ADMIN)
    if request.method == "POST":
        form = AdminUserForm(request.POST, instance=admin_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Admin account '{admin_user.email}' updated.")
            return redirect("polls:super_admin_admins")
    else:
        form = AdminUserForm(instance=admin_user)

    return render(request, "polls/super_admin_admins_form.html", {
        "form": form,
        "title": "Edit Admin Account",
    })


@super_admin_required
def super_admin_admins_delete(request, pk):
    """Delete an Admin user."""
    admin_user = get_object_or_404(get_user_model(), pk=pk, profile__role=UserProfile.ADMIN)
    email = admin_user.email
    admin_user.delete()
    messages.success(request, f"Admin account '{email}' deleted.")
    return redirect("polls:super_admin_admins")