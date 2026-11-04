"""
URL configuration for mysite project.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("polls.urls")),
    path("admin/", admin.site.urls),
]