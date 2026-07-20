# apps/code_analyzer/urls.py
from django.urls import path
from . import views

app_name = "code_analyzer"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("send-to-athena/", views.send_to_athena, name="send_to_athena")
]
