# apps/code_analyzer/urls.py
from django.urls import path
from . import views

app_name = "code_analyzer"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("send-to-athena/", views.send_to_athena, name="send_to_athena"),
    path("run/<int:run_id>/ai-review/", views.ai_review, name="ai_review"),
    path("run/<int:run_id>/ai-verify/", views.ai_verify, name="ai_verify"),
    path("export/sentry/", views.sentry_export, name="sentry_export"),
]
