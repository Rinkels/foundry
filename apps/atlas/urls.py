from django.urls import path

from . import views

app_name = "atlas"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Webhook must come before the <slug> routes so it isn't shadowed.
    path("webhook/github/", views.github_webhook, name="github_webhook"),
    path("<slug:slug>/", views.project_detail, name="project_detail"),
    path("<slug:slug>/sync-status/", views.sync_status, name="sync_status"),
    path("<slug:slug>/pull/", views.pull, name="pull"),
    path("<slug:slug>/deploy/", views.deploy, name="deploy"),
    path("<slug:slug>/harden/", views.harden, name="harden"),
    path("<slug:slug>/manage/", views.project_manage, name="project_manage"),
    path("<slug:slug>/rollback/", views.project_rollback, name="project_rollback"),
]
