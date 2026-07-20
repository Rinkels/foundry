from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from .models import (
    DueDiligenceRun,
    DDResponse,
    DDCriterion,
    DDRisk,
    DDCondition,
    DDEvidence,
)

def response_completion_for_run(run: DueDiligenceRun) -> dict:
    """
    Completion heuristic:
      A response counts as "complete" if it has commentary OR confidence != 'med' OR score_value != 0.
    This avoids treating seeded 0/default rows as completed.
    """
    qs = DDResponse.objects.filter(run=run)

    total = qs.count()
    if total == 0:
        return {"total": 0, "completed": 0, "pct": 0}

    completed = qs.filter(
        Q(score_value__gt=0) |
        Q(confidence__in=["low", "high"]) |
        ~Q(commentary="")
    ).count()

    pct = int(round((completed / total) * 100))
    return {"total": total, "completed": completed, "pct": pct}

def _normalize_score(score_value: int, min_v: int, max_v: int) -> float:
    denom = max(max_v - min_v, 1)
    return ((score_value - min_v) / denom) * 100.0


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def compute_section_scores(run: DueDiligenceRun) -> List[Dict[str, Any]]:
    """
    Returns list of:
      {section_id, section_title, section_weight, section_score_0_100, responded, total_criteria}
    Based on responses + criterion weights, normalized to 0..100 per section.
    """
    # Pull template structure
    sections = list(
        run.template.sections.prefetch_related("criteria").all().order_by("order_index", "id")
    )

    # Map responses by criterion_id for quick lookup
    responses = (
        DDResponse.objects
        .filter(run=run)
        .select_related("criterion", "criterion__scoring_scale", "criterion__section")
    )
    resp_by_crit = {r.criterion_id: r for r in responses}

    out: List[Dict[str, Any]] = []

    for sec in sections:
        criteria = list(sec.criteria.all().order_by("order_index", "id"))
        total = len(criteria)
        responded = 0

        weight_sum = 0.0
        weighted_sum = 0.0

        for c in criteria:
            r = resp_by_crit.get(c.id)
            if not r:
                continue
            responded += 1
            scale = c.scoring_scale
            normalized = _normalize_score(r.score_value, scale.min_value, scale.max_value)  # 0..100
            cw = float(c.weight)
            weight_sum += cw
            weighted_sum += normalized * cw

        section_score = 0.0 if weight_sum <= 0 else (weighted_sum / weight_sum)
        out.append(
            dict(
                section_id=sec.id,
                section_title=sec.title,
                section_weight=int(sec.weight),
                section_score_0_100=round(_clamp(section_score), 2),
                responded=responded,
                total_criteria=total,
            )
        )

    return out


def compute_failed_non_negotiables(run: DueDiligenceRun) -> List[Dict[str, Any]]:
    """
    Returns list of non-negotiable criteria with status and score, including "unknown".
    Fail rule:
      - If pass_threshold is set, fail if score < pass_threshold.
      - Else fail if score is below midpoint-ish (we'll use >=3/5 behavior only if threshold absent).
    """
    # Pull all non-negotiable criteria for template
    crits = (
        DDCriterion.objects
        .filter(section__template=run.template, non_negotiable=True)
        .select_related("section", "scoring_scale")
        .order_by("section__order_index", "order_index", "id")
    )

    resp_map = {
        r.criterion_id: r
        for r in DDResponse.objects.filter(run=run).only("criterion_id", "score_value")
    }

    out: List[Dict[str, Any]] = []

    for c in crits:
        r = resp_map.get(c.id)
        if not r:
            out.append(
                dict(
                    criterion_id=c.id,
                    section_title=c.section.title,
                    title=c.title,
                    score_value=None,
                    threshold=c.pass_threshold,
                    status="unknown",
                )
            )
            continue

        threshold = c.pass_threshold
        if threshold is None:
            # Default heuristic: pass if score is at least 60% of scale range
            scale = c.scoring_scale
            threshold = int(round(scale.min_value + 0.6 * (scale.max_value - scale.min_value)))

        status = "pass" if r.score_value >= threshold else "fail"

        out.append(
            dict(
                criterion_id=c.id,
                section_title=c.section.title,
                title=c.title,
                score_value=r.score_value,
                threshold=threshold,
                status=status,
            )
        )

    return out


def get_dd_cockpit() -> List[Dict[str, Any]]:
    """
    Returns targets with their latest run (if any).
    """
    # Latest run per target: easiest portable approach is ordering and grouping in python.
    runs = (
        DueDiligenceRun.objects
        .select_related("target_company", "template")
        .order_by("target_company_id", "-round_number", "-created_at")
    )
    by_target: Dict[int, DueDiligenceRun] = {}
    for r in runs:
        if r.target_company_id not in by_target:
            by_target[r.target_company_id] = r

    cards: List[Dict[str, Any]] = []
    for target_id, run in by_target.items():
        # quick rollups
        snap = getattr(run, "snapshot", None)
        snapshot_customers = getattr(snap, "total_customers", None) if snap else None
        snapshot_arr = getattr(snap, "arr", None) if snap else None
        snapshot_gm = getattr(snap, "gross_margin_pct", None) if snap else None

        blockers = run.risks.filter(blocking=True, status__in=["open", "mitigating"]).count()
        risks_open = run.risks.filter(status__in=["open", "mitigating"]).count()
        evidence_count = run.evidence.count()

        # non-negotiable fails count
        nn = compute_failed_non_negotiables(run)
        nn_fail = sum(1 for x in nn if x["status"] == "fail")
        nn_unknown = sum(1 for x in nn if x["status"] == "unknown")
        completion = response_completion_for_run(run)
        for c in cards:
            if not c.get("run_id"):
                print("BAD CARD:", c)

        cards.append(
            dict(
                run_id=run.id,
                target_name=run.target_company.name,
                target_website=run.target_company.website,
                deal_stage=run.target_company.deal_stage,
                status=run.status,
                template=str(run.template),
                overall_score=float(run.overall_score or 0),
                verdict=run.verdict or "",
                due_date=run.due_date,
                updated_at=run.updated_at,
                blockers=blockers + nn_fail,
                risks_open=risks_open,
                evidence_count=evidence_count,
                nonneg_fail=nn_fail,
                nonneg_unknown=nn_unknown,
                promoted=run.promoted_to_execution,
                response_total = completion["total"],
                response_completed = completion["completed"],
                response_pct = completion["pct"],
                snapshot_customers=snapshot_customers,
                snapshot_arr=snapshot_arr,
                snapshot_gm=snapshot_gm,

            )
        )

    # Sort by "most urgent": blocked first, then due date, then updated_at desc
    def urgency_key(c: Dict[str, Any]):
        status_rank = {"blocked": 0, "in_progress": 1, "draft": 2, "complete": 3}
        due = c["due_date"] or timezone.now().date()
        return (status_rank.get(c["status"], 9), due, -c["updated_at"].timestamp())

    return sorted(cards, key=urgency_key)


def get_run_dashboard(run_id: int) -> Dict[str, Any]:
    """
    Single payload for the run dashboard page.
    """
    run = (
        DueDiligenceRun.objects
        .select_related("target_company", "template")
        .prefetch_related(
            "participants__user",
            "risks",
            "conditions",
            "evidence",
            Prefetch("responses", queryset=DDResponse.objects.select_related("criterion", "criterion__scoring_scale", "criterion__section")),
        )
        .get(id=run_id)
    )
    snapshot = getattr(run, "snapshot", None)
    section_scores = compute_section_scores(run)
    nonneg = compute_failed_non_negotiables(run)

    # Risks
    risks = list(
        run.risks.all()
        .order_by("-blocking", "-risk_score", "-updated_at")
        .values(
            "id", "title", "category", "severity", "likelihood", "risk_score", "status", "blocking"
        )
    )

    # Conditions
    conditions = list(
        run.conditions.all()
        .order_by("must_complete_before", "due_by", "status", "id")
        .values("id", "title", "must_complete_before", "due_by", "status")
    )

    # Evidence (recent)
    evidence = list(
        run.evidence.all()
        .order_by("-created_at")[:12]
        .values("id", "title", "evidence_type", "url", "file_path", "sensitivity", "created_at")
    )

    # Participants
    participants = [
        dict(
            id=p.id,
            user=str(p.user),
            role=p.role,
            permission=p.permission,
        )
        for p in run.participants.all().order_by("role", "id")
    ]

    # Summary counts
    nonneg_fail = sum(1 for x in nonneg if x["status"] == "fail")
    nonneg_unknown = sum(1 for x in nonneg if x["status"] == "unknown")
    blockers = run.risks.filter(blocking=True, status__in=["open", "mitigating"]).count() + nonneg_fail
    completion = response_completion_for_run(run)

    return dict(
        run=run,
        snapshot=snapshot,
        section_scores=section_scores,
        nonneg=nonneg,
        nonneg_fail=nonneg_fail,
        nonneg_unknown=nonneg_unknown,
        blockers=blockers,
        risks=risks,
        conditions=conditions,
        evidence=evidence,
        participants=participants,
        completion=completion
    )

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import DDPromotionBatch, DDPromotedItem





import re
from django.db.models import Prefetch

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"&", "and", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _clamp_0_100(x):
    if x is None:
        return None
    try:
        v = float(x)
    except Exception:
        return None
    return max(0.0, min(100.0, v))

def get_dd_compare_payload() -> dict:
    cards = get_dd_cockpit()
    run_ids = [c["run_id"] for c in cards]

    runs = (
        DueDiligenceRun.objects
        .select_related("target_company", "template", "snapshot")
        .prefetch_related("template__sections")
        .filter(id__in=run_ids)
    )
    run_map = {r.id: r for r in runs}

    # --- Build a UNION of sections across all templates (normalized title as key) ---
    section_index = {}  # norm_title -> {"title": original, "weight": max_weight_seen}
    for rid in run_ids:
        run = run_map.get(rid)
        if not run:
            continue
        for sec in run.template.sections.all().order_by("order_index", "id"):
            k = _norm(sec.title)
            if not k:
                continue
            if k not in section_index:
                section_index[k] = {"section_title": sec.title, "weight": sec.weight or 0}
            else:
                # keep a reasonable weight (max seen) and prefer longer/more descriptive title
                section_index[k]["weight"] = max(section_index[k]["weight"], sec.weight or 0)
                if len(sec.title or "") > len(section_index[k]["section_title"] or ""):
                    section_index[k]["section_title"] = sec.title

    # stable ordering: by weight desc (or whatever you prefer), then title
    baseline_sections = sorted(
        section_index.values(),
        key=lambda d: (-int(d["weight"] or 0), d["section_title"].lower()),
    )

    # --- Scores by run keyed by normalized section title ---
    scores_by_run = {}
    for rid in run_ids:
        run = run_map.get(rid)
        if not run:
            continue
        sec_scores = compute_section_scores(run)
        scores_by_run[rid] = {
            _norm(s.get("section_title")): _clamp_0_100(s.get("section_score_0_100"))
            for s in sec_scores
            if s.get("section_title")
        }

    rows = []
    for sec in baseline_sections:
        title = sec["section_title"]
        k = _norm(title)
        rows.append(
            dict(
                section_title=title,
                weight=sec["weight"],
                scores=[scores_by_run.get(rid, {}).get(k, None) for rid in run_ids],
            )
        )

    # Columns
    cols = [c for c in cards if c["run_id"] in run_map]
    for c in cols:
        run = run_map.get(c["run_id"])
        snap = getattr(run, "snapshot", None) if run else None
        c["snap_customers"] = getattr(snap, "total_customers", None) if snap else None
        c["snap_arr"] = getattr(snap, "arr", None) if snap else None
        c["snap_mrr"] = getattr(snap, "mrr", None) if snap else None
        c["snap_gm"] = getattr(snap, "gross_margin_pct", None) if snap else None
        c["snap_nrr"] = getattr(snap, "net_revenue_retention_pct", None) if snap else None
        c["snap_burn"] = getattr(snap, "burn_rate_monthly", None) if snap else None
        c["snap_runway"] = getattr(snap, "runway_months", None) if snap else None

    return {"cols": cols, "rows": rows}


@transaction.atomic
def promote_run_to_okrs(run: DueDiligenceRun, user) -> DDPromotionBatch:
    """
    Creates a DDPromotionBatch + DDPromotedItems from:
      - Blocking/open risks
      - Open conditions
      - Failed non-negotiables
    Does NOT create real OKR objects yet; it creates draft promotion items.
    """
    batch = DDPromotionBatch.objects.create(
        run=run,
        created_by=user if getattr(user, "is_authenticated", False) else None,
        target_context_label=f"{run.target_company.name} - Tech DD",
        notes="Auto-generated from Janus DD run dashboard promotion.",
    )

    created = 0

    # 1) Blocking/open risks first
    risks = (
        run.risks.filter(status__in=["open", "mitigating"])
        .order_by("-blocking", "-risk_score", "-updated_at")
    )
    for r in risks:
        if not r.blocking:
            continue
        DDPromotedItem.objects.create(
            batch=batch,
            source_type=DDPromotedItem.SourceType.RISK,
            source_id=r.id,
            priority=DDPromotedItem.Priority.HIGH,
            proposed_objective=f"Mitigate blocking risk: {r.title}",
            proposed_key_result="Risk reduced or accepted with documented mitigation; evidence attached.",
        )
        created += 1

    # 2) Open conditions
    conditions = run.conditions.filter(status="open").order_by("must_complete_before", "due_by", "id")
    for c in conditions:
        DDPromotedItem.objects.create(
            batch=batch,
            source_type=DDPromotedItem.SourceType.CONDITION,
            source_id=c.id,
            priority=DDPromotedItem.Priority.HIGH if c.must_complete_before in ["signing", "closing"] else DDPromotedItem.Priority.MED,
            proposed_objective=f"Complete DD condition: {c.title}",
            proposed_key_result=f"Condition completed ({c.must_complete_before.replace('_',' ')}) with proof/evidence recorded.",
        )
        created += 1

    # 3) Failed non-negotiables
    nonneg = compute_failed_non_negotiables(run)
    for n in nonneg:
        if n["status"] != "fail":
            continue
        DDPromotedItem.objects.create(
            batch=batch,
            source_type=DDPromotedItem.SourceType.CRITERION,
            source_id=int(n["criterion_id"]),
            priority=DDPromotedItem.Priority.HIGH,
            proposed_objective=f"Resolve non-negotiable gap: {n['title']}",
            proposed_key_result="Gap remediated to threshold; validation evidence attached; re-score confirms pass.",
        )
        created += 1

    # If nothing was created, at least seed a placeholder item
    if created == 0:
        DDPromotedItem.objects.create(
            batch=batch,
            source_type=DDPromotedItem.SourceType.CRITERION,
            source_id=0,
            priority=DDPromotedItem.Priority.MED,
            proposed_objective="Review DD findings and draft integration OKRs",
            proposed_key_result="At least 3 Objectives and 6 Key Results drafted from evidence, risks, and conditions.",
        )

    return batch
