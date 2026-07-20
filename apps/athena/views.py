# apps/athena/views.py
from __future__ import annotations
from typing import Optional
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.utils.text import slugify
from .models import (
    PromptRun,
    PromptTemplate,
    PromptTestCase,
    PromptVersion,
    PromptStatus,
    RunStatus,
)
from .services.prompt_engine import render_prompt
from .services.checks import check_is_json, check_require_substrings
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

from .models import (
    AthenaThread, AthenaMessage, AthenaMessageRole, AthenaModelSettings,
    AthenaStudioRun, PromptTemplate, PromptVersion, PromptRole,
)
from .services.runtime import get_canonical_version, get_template_by_role
from .services.runner import run_llm, stream_llm
from .services.lint import lint_version
from .services.seeds import ensure_default_prompts
from .services.usage import record_studio_usage, record_studio_usage_from_result

from django.http import StreamingHttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from .models import AppContextSnapshot
from django.contrib import messages


def _looks_like_design_doc(text: str) -> bool:
    t = (text or "").lower()
    if len(t.strip()) < 200:
        return False

    # Existing design doc signals
    strong = [
        "## patch plan",
        "## design / patch plan",
        "## current app summary",
    ]

    # ✅ New App / Blueprint signals
    blueprint = [
        "## app blueprint",
        "## core entities",
        "## workflows",
        "## roles",
        "## ui",
        "## constraints",
        "## non-functional",
    ]

    return any(s in t for s in strong) or (sum(1 for s in blueprint if s in t) >= 3)


def _set_design_doc_cache(request, snapshot_id: Optional[int], design_doc: str):
    cache = request.session.get("athena_design_doc_by_snapshot", {}) or {}
    if snapshot_id:
        cache[str(snapshot_id)] = design_doc
        request.session["athena_design_doc_by_snapshot"] = cache

def _get_design_doc_cache(request, snapshot_id: Optional[int]) -> str:
    cache = request.session.get("athena_design_doc_by_snapshot", {}) or {}
    if snapshot_id and str(snapshot_id) in cache:
        return cache[str(snapshot_id)]
    return ""


@login_required
@require_POST
@transaction.atomic
def studio_rename_thread(request, thread_id: int):
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Title cannot be empty."}, status=400)

    # Keep it simple: truncate to something reasonable
    title = title[:80]

    thread.title = title
    thread.save(update_fields=["title", "updated_at"])
    return JsonResponse({"ok": True, "title": thread.title})

@login_required
@require_POST
@transaction.atomic
def studio_run_feature_designer(request, thread_id: int):
    """
    Runs the Feature Designer prompt once for the selected approved App Context (snapshot),
    and stores the resulting design_doc in session cache keyed by snapshot id.
    """
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    snapshot_id = (request.POST.get("snapshot_id") or "").strip()
    if not snapshot_id:
        return JsonResponse({"ok": False, "error": "Select an App Context (approved) first, then run Feature Designer."}, status=400)

    snap = AppContextSnapshot.objects.filter(pk=snapshot_id, is_approved=True).first()
    if not snap:
        return JsonResponse({"ok": False, "error": "Invalid or unapproved App Context snapshot."}, status=400)

    # Find the Feature Designer prompt by its assigned role.
    template = get_template_by_role(PromptRole.FEATURE_DESIGNER)
    if not template:
        return JsonResponse(
            {"ok": False, "error": "No Feature Designer prompt found. Assign a prompt the 'Feature Designer' role (in admin or prompt settings)."},
            status=404,
        )

    approved_only = bool(request.POST.get("approved_only"))
    version = get_canonical_version(template, approved_only=approved_only)
    if not version:
        return JsonResponse({"ok": False, "error": "No canonical Feature Designer prompt version available (approve one)."}, status=400)

    # Inputs
    inputs_raw = (request.POST.get("inputs_json") or "").strip() or "{}"
    try:
        inputs = json.loads(inputs_raw)
        if not isinstance(inputs, dict):
            raise ValueError("inputs_json must be a JSON object")
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Invalid inputs_json: {e}"}, status=400)

    # Always inject app_description from snapshot (authoritative app context)
    if (snap.description_md or "").strip():
        inputs["app_description"] = snap.description_md
    else:
        import json as _json
        inputs["app_description"] = _json.dumps(snap.snapshot_json or {}, indent=2)

    user_text = (request.POST.get("user_message") or "").strip()
    if user_text:
        inputs.setdefault("user_message", user_text)
        AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.USER, content=user_text)

    # Render and run
    rr = render_prompt(version.body, inputs)
    if not rr.ok:
        return JsonResponse({"ok": False, "error": f"Render failed: {rr.error}"}, status=400)

    settings_id = request.POST.get("settings_id")
    model_settings = AthenaModelSettings.objects.filter(pk=settings_id).first() if settings_id else _get_default_settings()

    llm_res = run_llm(rr.rendered, model_settings)
    full_text = llm_res.text if llm_res.ok else (llm_res.error or "")

    # Persist run + assistant message
    run = AthenaStudioRun.objects.create(
        thread=thread,
        template=template,
        version=version,
        model_settings=model_settings,
        inputs_json=inputs,
        rendered_prompt=rr.rendered,
        response_text=full_text,
        ok=llm_res.ok and rr.ok,
        error=(rr.error if not rr.ok else llm_res.error),
        created_by=request.user,
    )
    AthenaMessage.objects.create(
        thread=thread,
        role=AthenaMessageRole.ASSISTANT,
        content=run.response_text if run.ok else f"Run failed: {run.error}",
    )

    if run.ok:
        record_studio_usage_from_result(
            run=run, actor=request.user, llm_result=llm_res, action="athena_feature_designer"
        )

    # Cache design_doc by snapshot
    if run.ok and _looks_like_design_doc(full_text):
        design_cache = request.session.get("athena_design_doc_by_snapshot", {})
        design_cache[str(snapshot_id)] = full_text
        request.session["athena_design_doc_by_snapshot"] = design_cache

        if hasattr(thread, "last_design_doc"):
            thread.last_design_doc = full_text
            thread.save(update_fields=["last_design_doc", "updated_at"])

    return JsonResponse({"ok": True, "run_id": run.id, "template_id": template.id})

@login_required
@require_POST
@transaction.atomic
def studio_run_app_builder(request, thread_id: int):
    """
    Runs the App Builder prompt once for greenfield work.
    Does NOT require snapshot/app_description.
    Stores resulting design_doc onto the thread (last_design_doc) so impl prompts can use it later.
    """
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    # Find the App Builder prompt by its assigned role.
    template = get_template_by_role(PromptRole.APP_BUILDER)
    if not template:
        return JsonResponse(
            {"ok": False, "error": "No App Builder prompt found. Assign a prompt the 'App Builder' role (in admin or prompt settings)."},
            status=404,
        )

    approved_only = request.POST.get("approved_only") in ("1", "true", "True", "on", "yes")
    version = get_canonical_version(template, approved_only=approved_only)
    if not version:
        return JsonResponse({"ok": False, "error": "No canonical App Builder prompt version available (approve one)."}, status=400)

    # Inputs JSON (optional)
    inputs_raw = (request.POST.get("inputs_json") or "").strip() or "{}"
    try:
        inputs = json.loads(inputs_raw)
        if not isinstance(inputs, dict):
            raise ValueError("inputs_json must be a JSON object")
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Invalid inputs_json: {e}"}, status=400)

    # User message is the requirements for the new app
    user_text = (request.POST.get("user_message") or "").strip()
    if not user_text:
        return JsonResponse(
            {"ok": False, "error": "No user request provided. Enter what you want to build (app name + requirements), then run App Builder."},
            status=400,
        )

    inputs.setdefault("user_message", user_text)
    AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.USER, content=user_text)

    # Render and run
    rr = render_prompt(version.body, inputs)
    if not rr.ok:
        return JsonResponse({"ok": False, "error": f"Render failed: {rr.error}"}, status=400)

    settings_id = request.POST.get("settings_id")
    model_settings = AthenaModelSettings.objects.filter(pk=settings_id).first() if settings_id else _get_default_settings()

    llm_res = run_llm(rr.rendered, model_settings)
    full_text = llm_res.text if llm_res.ok else (llm_res.error or "")

    run = AthenaStudioRun.objects.create(
        thread=thread,
        template=template,
        version=version,
        model_settings=model_settings,
        inputs_json=inputs,
        rendered_prompt=rr.rendered,
        response_text=full_text,
        ok=llm_res.ok and rr.ok,
        error=(rr.error if not rr.ok else llm_res.error),
        created_by=request.user,
    )

    AthenaMessage.objects.create(
        thread=thread,
        role=AthenaMessageRole.ASSISTANT,
        content=run.response_text if run.ok else f"Run failed: {run.error}",
    )

    if run.ok:
        record_studio_usage_from_result(
            run=run, actor=request.user, llm_result=llm_res, action="athena_app_builder"
        )

    # Cache as "design doc" for later impl runs (snapshot-less)
    if run.ok:
        thread.last_design_doc = full_text
        if thread.title in ("New Thread", "New App") and user_text:
            thread.title = (user_text[:60] + "…") if len(user_text) > 60 else user_text
        thread.save(update_fields=["last_design_doc", "title", "updated_at"])

    return JsonResponse({"ok": True, "run_id": run.id, "template_id": template.id})

@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    consumer = (request.GET.get("consumer") or "").strip()

    prompts = PromptTemplate.objects.all().annotate(
        versions_count=Count("versions", distinct=True),
        runs_count=Count("runs", distinct=True),
    )

    if q:
        prompts = prompts.filter(name__icontains=q) | prompts.filter(key__icontains=q)

    if status in {PromptStatus.DRAFT, PromptStatus.APPROVED, PromptStatus.DEPRECATED}:
        prompts = prompts.filter(status=status)

    if consumer:
        prompts = prompts.filter(consumer=consumer)

    prompts = prompts.order_by("-updated_at")[:200]

    return render(request, "athena/dashboard.html", {"prompts": prompts, "q": q, "status": status, "consumer": consumer})

@login_required
def prompt_detail(request: HttpRequest, pk: int) -> HttpResponse:
    prompt = get_object_or_404(PromptTemplate, pk=pk)
    versions = prompt.versions.all()
    test_cases = prompt.test_cases.all()
    runs = prompt.runs.select_related("version", "test_case").all()[:25]
    current = prompt.current_version or prompt.versions.order_by("-version").first()
    lint_issues = lint_version(prompt, current) if current else []
    return render(
        request,
        "athena/prompt_detail.html",
        {"prompt": prompt, "versions": versions, "test_cases": test_cases, "runs": runs, "lint_issues": lint_issues},
    )


@login_required
def prompt_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        key = (request.POST.get("key") or "").strip()
        if not key:
            key = slugify(name)[:120]

        prompt = PromptTemplate.objects.create(
            name=name or key,
            key=key,
            owner=request.user,
            status=PromptStatus.DRAFT,
        )

        # Create v1
        v1 = PromptVersion.objects.create(
            template=prompt,
            version=1,
            created_by=request.user,
            body="Goal: {{ goal }}\n\nInstructions:\n{{ instructions }}\n\nOutput:\n{{ output_contract }}",
            changelog="Initial version",
        )
        prompt.current_version = v1
        prompt.save(update_fields=["current_version"])

        return redirect("athena:prompt_detail", pk=prompt.pk)

    return render(request, "athena/prompt_edit.html", {})


@login_required
def prompt_new_version(request: HttpRequest, pk: int) -> HttpResponse:
    prompt = get_object_or_404(PromptTemplate, pk=pk)
    latest = prompt.versions.order_by("-version").first()
    next_version = (latest.version + 1) if latest else 1

    if request.method == "POST":
        changelog = (request.POST.get("changelog") or "").strip()

        v = PromptVersion.objects.create(
            template=prompt,
            version=next_version,
            goal=request.POST.get("goal") or "",
            context=request.POST.get("context") or "",
            instructions=request.POST.get("instructions") or "",
            output_contract=request.POST.get("output_contract") or "",
            tone=request.POST.get("tone") or "",
            guardrails=request.POST.get("guardrails") or "",
            auto_compose=True,
            changelog=changelog,
            created_by=request.user,
        )
        prompt.current_version = v
        prompt.save(update_fields=["current_version", "updated_at"])
        return redirect("athena:prompt_detail", pk=prompt.pk)

    return render(
        request,
        "athena/prompt_edit.html",
        {"prompt": prompt, "latest": latest, "next_version": next_version},
    )


@login_required
def run_test_case(request: HttpRequest, pk: int, test_case_id: int) -> HttpResponse:
    prompt = get_object_or_404(PromptTemplate, pk=pk)
    version = prompt.current_version or prompt.versions.order_by("-version").first()
    test_case = get_object_or_404(PromptTestCase, pk=test_case_id, template=prompt)

    rr = render_prompt(version.body, test_case.input_json)

    # Placeholder output: for MVP we’ll treat rendered prompt as “output” until LLM wiring exists.
    # You can later replace output_text with the model response.
    output_text = rr.rendered if rr.ok else rr.error

    checks = {}
    status = RunStatus.PASS

    ok_sub, detail_sub = check_require_substrings(output_text, test_case.require_substrings)
    checks["require_substrings"] = {"pass": ok_sub, "detail": detail_sub}
    if not ok_sub:
        status = RunStatus.FAIL

    if test_case.require_json:
        ok_json, detail_json = check_is_json(output_text)
        checks["require_json"] = {"pass": ok_json, "detail": detail_json}
        if not ok_json:
            status = RunStatus.FAIL

    run = PromptRun.objects.create(
        template=prompt,
        version=version,
        test_case=test_case,
        rendered_prompt=rr.rendered if rr.ok else "",
        output_text=output_text,
        status=status,
        check_results=checks,
        created_by=request.user,
        model_name="(not wired)",
    )

    return redirect("athena:run_detail", pk=run.pk)


@login_required
def run_detail(request: HttpRequest, pk: int) -> HttpResponse:
    run = get_object_or_404(PromptRun.objects.select_related("template", "version", "test_case"), pk=pk)
    return render(request, "athena/run_detail.html", {"run": run})


def _get_default_settings():
    s = AthenaModelSettings.objects.filter(is_default=True).first()
    return s or AthenaModelSettings.objects.order_by("created_at").first()


@login_required
def studio_new_thread(request):
    t = AthenaThread.objects.create(title="New Thread", created_by=request.user)
    return redirect("athena:studio_thread", thread_id=t.id)

@login_required
def studio_new_app_thread(request):
    """
    Create a new thread intended for greenfield app creation.
    (No App Context snapshot required.)
    """
    t = AthenaThread.objects.create(title="New App", created_by=request.user)
    return redirect("athena:studio_thread", thread_id=t.id)

@login_required
def studio(request, thread_id=None):
    threads = AthenaThread.objects.order_by("-updated_at")[:50]
    thread = None
    messages = []
    prompts = PromptTemplate.objects.order_by("name")[:200]
    settings_list = AthenaModelSettings.objects.order_by("name")
    snapshots = AppContextSnapshot.objects.filter(is_approved=True).order_by("-created_at")[:200]

    # Defaults come from session (fallback only)
    selected_prompt_id = int(request.GET.get("prompt_id") or request.session.get("athena_last_prompt_id") or 0)
    selected_snapshot_id = int(request.GET.get("snapshot_id") or request.session.get("athena_last_snapshot_id") or 0)
    selected_settings_id = int(request.GET.get("settings_id") or request.session.get("athena_last_settings_id") or 0)
    approved_only = bool(request.GET.get("approved_only") or request.session.get("athena_last_approved_only") or True)
    mode = request.GET.get("mode") or request.session.get("athena_last_mode") or AthenaThread.MODE_ENHANCEMENT

    if thread_id:
        thread = AthenaThread.objects.filter(pk=thread_id).first()
        if thread is None:
            # Thread was deleted (or the URL is stale) — don't hard-404 the Studio.
            # Open the most recent thread if one exists, else the empty Studio.
            latest = AthenaThread.objects.order_by("-updated_at").first()
            if latest:
                return redirect("athena:studio_thread", thread_id=latest.id)
            return redirect("athena:studio")
        messages = list(thread.messages.all())

        # ✅ Thread-specific UI state overrides session defaults
        st = thread.ui_state or {}
        selected_prompt_id = int(st.get("prompt_id") or selected_prompt_id or 0)
        selected_snapshot_id = int(st.get("snapshot_id") or selected_snapshot_id or 0)
        selected_settings_id = int(st.get("settings_id") or selected_settings_id or 0)
        approved_only = bool(st.get("approved_only", approved_only))
        mode = st.get("mode") or thread.mode or mode

    active_settings = (
        AthenaModelSettings.objects.filter(pk=selected_settings_id).first()
        if selected_settings_id
        else _get_default_settings()
    )

    return render(request, "athena/studio.html", {
        "threads": threads,
        "thread": thread,
        "messages": messages,
        "prompts": prompts,
        "settings_list": settings_list,
        "active_settings": active_settings,
        "snapshots": snapshots,
        "selected_prompt_id": selected_prompt_id,
        "selected_snapshot_id": selected_snapshot_id,
        "selected_settings_id": selected_settings_id,
        "approved_only": approved_only,
        "mode": mode,
    })



@login_required
@transaction.atomic
def studio_run(request, thread_id: int):
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    prompt_id = int(request.POST.get("prompt_id") or 0)
    template = get_object_or_404(PromptTemplate, pk=prompt_id)

    approved_only = request.POST.get("approved_only") in ("1", "true", "True", "on", "yes")

    version = get_canonical_version(template, approved_only=approved_only)
    if not version:
        # no canonical version available
        AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.ASSISTANT,
                                    content=f"No version available for '{template.key}'. Approve one or set a current version.")
        return redirect("athena:studio_thread", thread_id=thread.id)

    # Inputs JSON
    inputs_raw = (request.POST.get("inputs_json") or "").strip() or "{}"
    try:
        inputs = json.loads(inputs_raw)
        if not isinstance(inputs, dict):
            raise ValueError("inputs_json must be a JSON object")
    except Exception as e:
        AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.ASSISTANT,
                                     content=f"Invalid inputs_json: {e}")
        return redirect("athena:studio_thread", thread_id=thread.id)

    # Optional user message
    user_text = (request.POST.get("user_message") or "").strip()
    if user_text and "user_message" not in inputs:
        inputs["user_message"] = user_text
    if user_text:
        AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.USER, content=user_text)

    # ✅ Inject App Context snapshot BEFORE render
    snapshot_id = request.POST.get("snapshot_id") or ""
    design_cache = request.session.get("athena_design_doc_by_snapshot", {})

    if snapshot_id and "app_description" not in inputs:
        snap = AppContextSnapshot.objects.filter(pk=snapshot_id, is_approved=True).first()
        if snap:
            if (snap.description_md or "").strip():
                inputs["app_description"] = snap.description_md
            else:
                import json as _json
                inputs["app_description"] = _json.dumps(snap.snapshot_json or {}, indent=2)

    # Auto-fill design_doc from thread if prompt expects it
    if "{{ design_doc }}" in (version.body or "") and "design_doc" not in inputs:
        # Prefer design_doc that matches the selected snapshot
        if snapshot_id and str(snapshot_id) in design_cache:
            inputs["design_doc"] = design_cache[str(snapshot_id)]
        elif getattr(thread, "last_design_doc", ""):
            # fallback for older threads
            inputs["design_doc"] = thread.last_design_doc

    # Render prompt from version.body using inputs
    rr = render_prompt(version.body, inputs)
    rendered_prompt = rr.rendered if rr.ok else rr.error

    # Model settings
    settings_id = request.POST.get("settings_id")
    request.session["athena_last_prompt_id"] = prompt_id
    if snapshot_id:
        request.session["athena_last_snapshot_id"] = int(snapshot_id)
    if settings_id:
        request.session["athena_last_settings_id"] = int(settings_id)

    model_settings = AthenaModelSettings.objects.filter(pk=settings_id).first() if settings_id else _get_default_settings()

    # Run LLM (currently Echo unless you plug in provider)
    llm_res = run_llm(rendered_prompt, model_settings)

    if _looks_like_design_doc(llm_res.text):
        sid = int(snapshot_id) if snapshot_id else None
        _set_design_doc_cache(request, sid, llm_res.text)
        if hasattr(thread, "last_design_doc"):
            thread.last_design_doc = llm_res.text
            thread.save(update_fields=["last_design_doc", "updated_at"])

    # Persist run
    run = AthenaStudioRun.objects.create(
        thread=thread,
        template=template,
        version=version,
        model_settings=model_settings,
        inputs_json=inputs,
        rendered_prompt=rendered_prompt if rr.ok else "",
        response_text=llm_res.text if llm_res.ok else "",
        ok=llm_res.ok and rr.ok,
        error=(rr.error if not rr.ok else llm_res.error),
        created_by=request.user,
    )

    # Add assistant message
    AthenaMessage.objects.create(
        thread=thread,
        role=AthenaMessageRole.ASSISTANT,
        content=run.response_text if run.ok else f"Run failed: {run.error}",
    )

    if run.ok:
        record_studio_usage_from_result(
            run=run, actor=request.user, llm_result=llm_res, action="athena_studio_run"
        )

    # Update thread title lightly if still default
    if thread.title == "New Thread" and user_text:
        thread.title = (user_text[:60] + "…") if len(user_text) > 60 else user_text
        thread.save(update_fields=["title", "updated_at"])

    return redirect("athena:studio_thread", thread_id=thread.id)


@login_required
@transaction.atomic
def studio_run_stream(request, thread_id: int):
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    prompt_id = int(request.POST.get("prompt_id") or 0)
    template = get_object_or_404(PromptTemplate, pk=prompt_id)

    approved_only = request.POST.get("approved_only") in ("1", "true", "True", "on", "yes")

    version = get_canonical_version(template, approved_only=approved_only)
    if not version:
        return StreamingHttpResponse(["No canonical version available.\n"], content_type="text/plain")

    inputs_raw = (request.POST.get("inputs_json") or "").strip() or "{}"
    try:
        inputs = json.loads(inputs_raw)
        if not isinstance(inputs, dict):
            raise ValueError("inputs_json must be a JSON object")
    except Exception as e:
        return StreamingHttpResponse([f"Invalid inputs_json: {e}\n"], content_type="text/plain")

    user_text = (request.POST.get("user_message") or "").strip()
    if user_text and "user_message" not in inputs:
        inputs["user_message"] = user_text
    if user_text:
        AthenaMessage.objects.create(thread=thread, role=AthenaMessageRole.USER, content=user_text)
    snapshot_id = request.POST.get("snapshot_id") or ""
    design_cache = request.session.get("athena_design_doc_by_snapshot", {})
    if snapshot_id:
        snap = AppContextSnapshot.objects.filter(pk=snapshot_id, is_approved=True).first()
        if snap:
            # Prefer human-readable markdown if available; otherwise JSON pretty
            md = (snap.description_md or "").strip()
            if md:
                inputs.setdefault("app_description", md)
            else:
                inputs.setdefault("app_description", json.dumps(snap.snapshot_json, indent=2))

    # --- Inject design_doc if the prompt needs it and user didn't provide it ---
    if "{{ design_doc }}" in (version.body or "") and "design_doc" not in inputs:
        cached = _get_design_doc_cache(request, int(snapshot_id) if snapshot_id else None)
        if cached:
            inputs["design_doc"] = cached
        elif getattr(thread, "last_design_doc", ""):
            inputs["design_doc"] = thread.last_design_doc


    rr = render_prompt(version.body, inputs)
    if not rr.ok:
        return StreamingHttpResponse([f"Render failed: {rr.error}\n"], content_type="text/plain")
    settings_id = request.POST.get("settings_id")
    model_settings = AthenaModelSettings.objects.filter(pk=settings_id).first() if settings_id else _get_default_settings()
    request.session["athena_last_prompt_id"] = prompt_id
    if snapshot_id:
        request.session["athena_last_snapshot_id"] = int(snapshot_id)
    if settings_id:
        request.session["athena_last_settings_id"] = int(settings_id)

    chunks = []
    usage_holder = {}

    def gen():
        nonlocal chunks
        try:
            for delta in stream_llm(rr.rendered, model_settings, on_usage=usage_holder.update):
                chunks.append(delta)
                yield delta
        except Exception as e:
            yield f"\n[STREAM_ERROR] {e}\n"
        finally:
            full_text = "".join(chunks)

            def _is_feature_designer(template: PromptTemplate) -> bool:
                k = (template.key or "").lower()
                n = (template.name or "").lower()
                return ("feature-designer" in k) or ("feature designer" in n)

            if _looks_like_design_doc(full_text):
                sid = int(snapshot_id) if snapshot_id else None
                _set_design_doc_cache(request, sid, full_text)
                if hasattr(thread, "last_design_doc"):
                    thread.last_design_doc = full_text
                    thread.save(update_fields=["last_design_doc", "updated_at"])


            run = AthenaStudioRun.objects.create(
                thread=thread,
                template=template,
                version=version,
                model_settings=model_settings,
                inputs_json=inputs,
                rendered_prompt=rr.rendered,
                response_text=full_text,
                ok=True,
                created_by=request.user,
            )
            AthenaMessage.objects.create(
                thread=thread,
                role=AthenaMessageRole.ASSISTANT,
                content=full_text if full_text else "(no output)",
            )

            if usage_holder:
                record_studio_usage(
                    run=run,
                    actor=request.user,
                    action="athena_studio_run_stream",
                    **usage_holder,
                )

            yield "\n[[ATHENA_DONE]]\n"

    return StreamingHttpResponse(gen(), content_type="text/plain; charset=utf-8")

@login_required
@require_POST
@transaction.atomic
def ingest_snapshot(request):
    """
    Ingest a snapshot from Code Analyzer (server-side POST).
    Payload must include: key, title, app_path, snapshot_json
    Optional: description_md
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    key = (payload.get("key") or "").strip()
    title = (payload.get("title") or "").strip()
    app_path = (payload.get("app_path") or "").strip()
    snapshot_json = payload.get("snapshot_json") or {}
    description_md = payload.get("description_md") or ""

    if not key or not title or not app_path:
        return HttpResponseBadRequest("Missing key/title/app_path")
    if not isinstance(snapshot_json, dict):
        return HttpResponseBadRequest("snapshot_json must be an object")

    latest = AppContextSnapshot.objects.filter(key=key).order_by("-version").first()
    next_version = (latest.version + 1) if latest else 1

    snap = AppContextSnapshot.objects.create(
        key=key,
        title=title,
        app_path=app_path,
        version=next_version,
        snapshot_json=snapshot_json,
        description_md=description_md,
        created_by=request.user,
        source="code_analyzer",
    )
    auto_ok = bool(description_md and len(description_md) > 800 and "Key file excerpts" in description_md)
    if auto_ok:
        snap.is_approved = True
        snap.save(update_fields=["is_approved"])

    return JsonResponse({
        "ok": True,
        "id": snap.id,
        "key": snap.key,
        "version": snap.version,
        "is_approved": snap.is_approved,
    })

@login_required
@transaction.atomic
def studio_create_impl_prompt(request, thread_id: int):
    """
    One-click selection of the canonical Implementation Generator prompt.

    The prompt body lives in apps/athena/services/seeds.py and is materialised by
    a data migration, so this view no longer clones a per-source prompt from a
    hardcoded string. It just ensures the canonical impl-generator prompt exists
    and preselects it in Studio.
    """
    if request.method != "POST":
        return redirect("athena:studio_thread", thread_id=thread_id)

    get_object_or_404(AthenaThread, pk=thread_id)

    # Idempotently ensure the canonical impl-generator template exists, then use it.
    ensure_default_prompts(PromptTemplate, PromptVersion)
    impl_tpl = get_template_by_role(PromptRole.IMPL_GENERATOR)
    if not impl_tpl:
        messages.error(request, "Implementation Generator prompt is not available.")
        return redirect("athena:studio_thread", thread_id=thread_id)

    messages.success(request, f"Using implementation prompt: {impl_tpl.name}")

    # Keep the currently selected snapshot in the redirect so the user doesn't lose it.
    snapshot_id = request.POST.get("snapshot_id") or ""
    url = f"/athena/studio/{thread_id}/?prompt_id={impl_tpl.id}"
    if snapshot_id:
        url += f"&snapshot_id={snapshot_id}"
    return redirect(url)


@login_required
@require_POST
def thread_ui_state(request, thread_id: int):
    """
    Saves per-thread Studio selections so switching threads pre-selects the correct prompt/context/mode.
    """
    thread = get_object_or_404(AthenaThread, pk=thread_id)

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Payload must be JSON object")
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Invalid JSON: {e}"}, status=400)

    st = thread.ui_state or {}
    # Whitelist keys we allow from UI
    for k in ["prompt_id", "snapshot_id", "settings_id", "approved_only", "mode"]:
        if k in payload:
            st[k] = payload[k]

    # Keep thread.mode in sync for easy filtering
    if st.get("mode") in dict(AthenaThread.MODE_CHOICES):
        thread.mode = st["mode"]

    thread.ui_state = st
    thread.save(update_fields=["ui_state", "mode", "updated_at"])

    # Also keep session as a fallback when thread is None
    request.session["athena_last_prompt_id"] = int(st.get("prompt_id") or 0)
    request.session["athena_last_snapshot_id"] = int(st.get("snapshot_id") or 0)
    request.session["athena_last_settings_id"] = int(st.get("settings_id") or 0)
    request.session["athena_last_approved_only"] = bool(st.get("approved_only", True))
    request.session["athena_last_mode"] = st.get("mode") or AthenaThread.MODE_ENHANCEMENT

    return JsonResponse({"ok": True, "ui_state": st})


@login_required
@require_POST
def thread_rename(request, thread_id: int):
    thread = get_object_or_404(AthenaThread, pk=thread_id)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Missing title"}, status=400)
    if len(title) > 200:
        return JsonResponse({"ok": False, "error": "Title too long"}, status=400)

    thread.title = title
    thread.save(update_fields=["title", "updated_at"])
    return JsonResponse({"ok": True, "title": thread.title})
