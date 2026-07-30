from django.urls import path

from . import views

app_name = "codex"

urlpatterns = [
    path("", views.DocListView.as_view(), name="list"),
    path("rescan/", views.rescan, name="rescan"),
    path("doc/<int:pk>/", views.doc_detail, name="detail"),
    path("doc/<int:pk>/toggle/", views.toggle, name="toggle"),
]
