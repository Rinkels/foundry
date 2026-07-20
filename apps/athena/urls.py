# apps/athena/urls.py
from django.urls import path
from . import views

app_name = "athena"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("prompts/<int:pk>/", views.prompt_detail, name="prompt_detail"),
    path("prompts/new/", views.prompt_create, name="prompt_create"),
    path("prompts/<int:pk>/new-version/", views.prompt_new_version, name="prompt_new_version"),
    path("runs/<int:pk>/", views.run_detail, name="run_detail"),
    path("prompts/<int:pk>/run-test/<int:test_case_id>/", views.run_test_case, name="run_test_case"),

    path("studio/", views.studio, name="studio"),
    path("studio/new-thread/", views.studio_new_thread, name="studio_new_thread"),
    path("studio/<int:thread_id>/", views.studio, name="studio_thread"),
    path("studio/<int:thread_id>/run/", views.studio_run, name="studio_run"),
    path("studio/<int:thread_id>/run-stream/", views.studio_run_stream, name="studio_run_stream"),

    # ✅ NEW: Run Feature Designer once per app context (snapshot)
    path(
        "studio/<int:thread_id>/run-feature-designer/",
        views.studio_run_feature_designer,
        name="studio_run_feature_designer",
    ),
    # ✅ NEW: greenfield thread creation
    path("studio/new-app-thread/", views.studio_new_app_thread, name="studio_new_app_thread"),

    # ✅ NEW: app builder (does NOT require snapshot)
    path("studio/<int:thread_id>/run-app-builder/", views.studio_run_app_builder, name="studio_run_app_builder"),

    # ✅ Existing: one-click Implementation Generator creation
    path("studio/<int:thread_id>/create-impl-prompt/", views.studio_create_impl_prompt, name="studio_create_impl_prompt"),

    # ✅ NEW: per-thread UI state + rename
    path("thread/<int:thread_id>/ui-state/", views.thread_ui_state, name="thread_ui_state"),
    path("thread/<int:thread_id>/rename/", views.thread_rename, name="thread_rename"),

    # ✅ NEW: rename thread
    path("studio/<int:thread_id>/rename/", views.studio_rename_thread, name="studio_rename_thread"),

    path("api/snapshots/ingest/", views.ingest_snapshot, name="ingest_snapshot"),
]
