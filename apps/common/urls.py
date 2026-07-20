from django.urls import path
from . import views_ai

app_name = "common"
urlpatterns = [
    path("ai-usage/", views_ai.ai_usage_dashboard, name="ai-usage"),
]