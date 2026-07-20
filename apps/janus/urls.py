from django.urls import path
from . import views, views_pdf

app_name = "janus"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("idea/new/", views.idea_create, name="idea_create"),
    path("idea/<int:pk>/", views.idea_detail, name="idea_detail"),
    path("idea/<int:pk>/sprint/new/", views.sprint_create, name="sprint_create"),
    path("sprint/<int:sprint_id>/evidence/new/", views.evidence_create, name="evidence_create"),
    # ✅ NEW
    path("idea/<int:pk>/evaluate-gate/customer-pain/", views.evaluate_gate_customer_pain,
         name="evaluate_gate_customer_pain"),
    path("dd/", views.dd_cockpit, name="dd-cockpit"),
    path("dd/compare/", views.dd_compare, name="dd-compare"),
    path("dd/run/<int:run_id>/", views.dd_run_detail, name="dd-run-detail"),
    path("dd/run/<int:run_id>/promote/", views.dd_run_promote, name="dd-run-promote"),
    path("dd/run/<int:run_id>/responses/", views.dd_run_responses, name="dd-run-responses"),
    path("dd/response/<int:response_id>/quick-update/", views.dd_response_quick_update, name="dd-response-quick-update"),
    path("dd/run/<int:run_id>/snapshot/quick-update/", views.dd_snapshot_quick_update, name="dd-snapshot-quick-update"),
    path("dd/run/<int:run_id>/questions.pdf", views_pdf.dd_run_questions_pdf, name="dd-run-questions-pdf"),
    path("dd/run/<int:run_id>/qna.pdf", views_pdf.dd_run_qna_pdf, name="dd-run-qna-pdf"),
    path("dd/run/<int:run_id>/detail.pdf", views_pdf.dd_run_detail_pdf, name="dd-run-detail-pdf"),
]
