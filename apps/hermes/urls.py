from django.urls import path
from . import views

app_name = "hermes"

urlpatterns = [
    path("", views.newsletters_index, name="index"),
    path("<slug:series_slug>/", views.series_index, name="series"),
    path("<slug:series_slug>/<slug:issue_slug>/", views.issue_detail, name="issue"),
]
