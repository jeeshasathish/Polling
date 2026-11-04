from django.urls import path

from . import views

app_name = "polls"
urlpatterns = [
    # ── Poll browsing / voting (under polls/ prefix) ──────────────────
    path("polls/", views.IndexView.as_view(), name="index"),
    path("polls/<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("polls/<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    path("polls/<int:question_id>/vote/", views.vote, name="vote"),

    # ── Smart role router ────────────────────────────────────────────
    path("polls/dashboard/", views.dashboard, name="dashboard"),

    # ── SUPER ADMIN portal ───────────────────────────────────────────
    path("super-admin/dashboard/", views.super_admin_dashboard, name="super_admin_dashboard"),
    path("super-admin/users/",     views.super_admin_users,     name="super_admin_users"),
    path("super-admin/admins/",    views.super_admin_admins,    name="super_admin_admins"),
    path("super-admin/admins/create/", views.super_admin_admins_create, name="super_admin_admins_create"),
    path("super-admin/admins/<int:pk>/edit/", views.super_admin_admins_edit, name="super_admin_admins_edit"),
    path("super-admin/admins/<int:pk>/delete/", views.super_admin_admins_delete, name="super_admin_admins_delete"),

    # ── ADMIN portal ─────────────────────────────────────────────────
    path("admin/dashboard/",  views.admin_dashboard, name="admin_dashboard"),
    path("admin/users/",       views.manage_users,    name="manage_users"),
    path("admin/analytics/",   views.polls_analytics, name="admin_analytics"),
    path("admin/analytics/download/", views.download_analytics_report, name="download_analytics_report"),
    path("admin/analytics/report/", views.polls_analytics_report, name="admin_analytics_report"),



    # ── ADMIN POLLING module ─────────────────────────────────────────
    path("admin/polls/", views.admin_polls_list, name="admin_polls_list"),
    path("admin/polls/drafts/", views.admin_polls_list, {'status_filter': 'draft'}, name="admin_polls_drafts"),
    path("admin/polls/active/", views.admin_polls_list, {'status_filter': 'active'}, name="admin_polls_active"),
    path("admin/polls/closed/", views.admin_polls_list, {'status_filter': 'closed'}, name="admin_polls_closed"),
    path("admin/polls/create/", views.admin_polls_create, name="admin_polls_create"),
    path("admin/polls/<int:pk>/edit/", views.admin_polls_edit, name="admin_polls_edit"),
    path("admin/polls/<int:pk>/delete/", views.admin_polls_delete, name="admin_polls_delete"),
    path("admin/polls/<int:pk>/publish/", views.admin_polls_publish, name="admin_polls_publish"),
    path("admin/polls/<int:pk>/close/", views.admin_polls_close, name="admin_polls_close"),
    path("admin/polls/<int:pk>/duplicate/", views.admin_polls_duplicate, name="admin_polls_duplicate"),

    # ── POLL CATEGORIES module ───────────────────────────────────────
    path("admin/polls/categories/", views.admin_polls_categories, name="admin_polls_categories"),
    path("admin/polls/categories/create/", views.admin_category_create, name="admin_category_create"),
    path("admin/polls/categories/<int:pk>/edit/", views.admin_category_edit, name="admin_category_edit"),
    path("admin/polls/categories/<int:pk>/delete/", views.admin_category_delete, name="admin_category_delete"),

    # ── USER (Voter) portal ──────────────────────────────────────────
    path("user/dashboard/", views.user_dashboard, name="user_dashboard"),
    path("user/history/", views.user_history, name="user_history"),

    # ── Shared profile / settings (all authenticated roles) ──────
    path("polls/profile/", views.profile, name="profile"),
    path("polls/settings/", views.settings, name="settings"),
]
