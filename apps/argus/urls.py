from django.urls import path

from . import views

app_name = "argus"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("update/", views.log_update, name="log_update"),
    path("digest/", views.digest, name="digest"),
]
