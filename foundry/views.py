# fractals/views.py
from django.conf import settings
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
# fractals/views.py
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import Truncator

from apps.common.models import AiUsageEvent  # or wherever you placed it
@login_required
def fractals_home(request):
    now = timezone.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = now - timedelta(days=7)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    qs = AiUsageEvent.objects.all()
    # If tenant-aware, filter qs = qs.filter(organization=current_org)

    def sums(since):
        agg = qs.filter(created_at__gte=since).aggregate(
            tokens=Sum("total_tokens"),
            cost=Sum("cost_usd"),
            tool_cost=Sum("tool_cost_usd"),
            other_cost=Sum("other_cost_usd"),
        )
        # Handle None
        return {
            "tokens": agg["tokens"] or 0,
            "cost": agg["cost"] or 0,
            "tool_cost": agg["tool_cost"] or 0,
            "other_cost": agg["other_cost"] or 0,
        }

    ai_today = sums(start_today)
    ai_7d = sums(start_7d)
    ai_mtd = sums(start_month)

    context = {
        # ... existing context ...
        "ai_today": ai_today,
        "ai_7d": ai_7d,
        "ai_mtd": ai_mtd,
        "cards": getattr(settings, "FOUNDRY_HOME_CARDS", {}),
    }
    return render(request, "foundry/home.html", context)

# Configure what “global search” means here:
GLOBAL_SEARCH_TARGETS = [
    ("janus.TargetCompany", ["name", "short_description", "long_description", "website"], "Companies"),
    ("people.Person", ["first_name", "last_name", "email"], "People"),

    # FIXED: use actual fields on your FileAsset model
    ("mnemos.FileAsset", ["original_name", "mime_type"], "Files"),

    ("okr.Objective", ["title", "description"], "Objectives"),
    ("okr.Task", ["title", "description", "notes"], "Tasks"),
    ("janus.DueDiligenceRun", ["title", "summary"], "Due Diligence Runs"),
]

def _model_or_none(model_label: str):
    try:
        app_label, model_name = model_label.split(".")
        return apps.get_model(app_label, model_name)
    except Exception:
        return None

def _obj_title(obj):
    for attr in ("title", "name", "original_name"):
        val = getattr(obj, attr, "")
        if val:
            return str(val)
    return str(obj)

def _obj_snippet(obj, fields):
    for f in fields:
        val = getattr(obj, f, "")
        if val:
            return Truncator(str(val)).chars(140)
    return ""

def _obj_url(obj):
    # Prefer get_absolute_url if you have it
    if hasattr(obj, "get_absolute_url"):
        try:
            return obj.get_absolute_url()
        except Exception:
            pass
    # Fallback: try admin change page
    try:
        return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    except Exception:
        return None

from django.core.exceptions import FieldDoesNotExist

def _valid_fields(Model, fields):
    ok = []
    for f in fields:
        try:
            Model._meta.get_field(f)
            ok.append(f)
        except FieldDoesNotExist:
            # Allow related lookups like "owner__username" if you want later
            if "__" in f:
                ok.append(f)
    return ok

@login_required
def global_search(request):
    q = (request.GET.get("q") or "").strip()
    results = []

    if q:
        for model_label, fields, label in GLOBAL_SEARCH_TARGETS:
            Model = _model_or_none(model_label)
            if not Model:
                continue

            fields = _valid_fields(Model, fields)
            if not fields:
                continue

            query = Q()
            for f in fields:
                query |= Q(**{f"{f}__icontains": q})

            qs = Model.objects.filter(query)[:15]
            items = []
            for obj in qs:
                items.append({
                    "title": _obj_title(obj),
                    "snippet": _obj_snippet(obj, fields),
                    "url": _obj_url(obj),
                    "meta": f"{obj._meta.app_label}.{obj._meta.model_name} · #{obj.pk}",
                })

            if items:
                results.append({
                    "label": label,
                    "model": model_label,
                    "items": items,
                })

    return render(request, "foundry/search_results.html", {"q": q, "results": results})