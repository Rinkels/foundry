from django.urls import path

from . import views

app_name = "aegis"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("p/<slug:slug>/", views.profile_detail, name="profile_detail"),
    path("p/<slug:slug>/scan/", views.scan_now, name="scan_now"),
    path("p/<slug:slug>/report.pdf", views.report_pdf, name="report_pdf"),
    path("p/<slug:slug>/posture/", views.refresh_posture, name="refresh_posture"),
    path("exposure/<int:pk>/status/", views.set_exposure_status, name="set_exposure_status"),
    path("run/<int:pk>/", views.run_log, name="run_log"),
]
