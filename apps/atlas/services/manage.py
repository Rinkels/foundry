"""Manage-panel data for a deployed CloudProject: live health, Cloud Run
revisions (+ rollback), and recent logs. All via the gcloud CLI, reusing the
project's auth/identity (see provisioner._auth)."""
from __future__ import annotations

import json
import time

from . import provisioner, shell

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


def _common(cp):
    return (
        provisioner._project_id(cp),
        provisioner._region(cp),
        provisioner._service_name(cp),
        *provisioner._auth(cp),  # (args, env)
    )


def service_overview(cp) -> dict:
    pid, region, svc, args, env = _common(cp)
    if not pid:
        return {"error": "No GCP project id set on this project."}
    res = shell.run(["gcloud", "run", "services", "describe", svc,
                     "--project", pid, "--region", region, "--format=json", *args], env=env)
    if not res.ok:
        return {"error": (res.output or "").strip()[-500:]}
    try:
        d = json.loads(res.output)
    except Exception:
        return {"error": "Could not parse service description (is it deployed yet?)."}
    status = d.get("status", {})
    traffic = {t.get("revisionName"): t.get("percent", 0)
               for t in status.get("traffic", []) if t.get("revisionName")}
    return {
        "service": svc,
        "url": status.get("url"),
        "latest_ready": status.get("latestReadyRevisionName"),
        "ready": any(c.get("type") == "Ready" and c.get("status") == "True"
                     for c in status.get("conditions", [])),
        "traffic": traffic,
    }


def list_revisions(cp, traffic=None, limit: int = 10) -> list:
    pid, region, svc, args, env = _common(cp)
    if not pid:
        return []
    res = shell.run(["gcloud", "run", "revisions", "list", "--service", svc,
                     "--project", pid, "--region", region, "--format=json",
                     "--limit", str(limit), *args], env=env)
    if not res.ok:
        return []
    try:
        data = json.loads(res.output)
    except Exception:
        return []
    traffic = traffic or {}
    out = []
    for r in data:
        md, st = r.get("metadata", {}), r.get("status", {})
        name = md.get("name")
        out.append({
            "name": name,
            "created": md.get("creationTimestamp"),
            "ready": any(c.get("type") == "Ready" and c.get("status") == "True"
                         for c in st.get("conditions", [])),
            "traffic": traffic.get(name, 0),
        })
    return out


def recent_logs(cp, limit: int = 40) -> list:
    pid, region, svc, args, env = _common(cp)
    if not pid:
        return []
    res = shell.run(["gcloud", "logging", "read",
                     f'resource.type="cloud_run_revision" resource.labels.service_name="{svc}"',
                     "--project", pid, "--limit", str(limit),
                     "--format=json", "--freshness=1d", *args], env=env)
    if not res.ok:
        return []
    try:
        data = json.loads(res.output)
    except Exception:
        return []
    logs = []
    for e in data:
        txt = e.get("textPayload") or (e.get("jsonPayload") or {}).get("message") or ""
        txt = (txt or "").strip()
        if txt:
            logs.append({"ts": e.get("timestamp"), "severity": e.get("severity", "DEFAULT"), "text": txt[:300]})
    return logs


def health_check(cp, url: str | None) -> dict | None:
    if not requests or not url:
        return None
    try:
        t = time.time()
        r = requests.get(url, timeout=12)
        return {"status": r.status_code, "ms": int((time.time() - t) * 1000), "ok": r.status_code < 500}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "ms": None, "ok": False, "error": str(e)[:140]}


def rollback(cp, revision: str):
    pid, region, svc, args, env = _common(cp)
    return shell.run(["gcloud", "run", "services", "update-traffic", svc,
                      "--to-revisions", f"{revision}=100",
                      "--project", pid, "--region", region, "--quiet", *args], env=env)


# ---------------------------------------------------------------------------
# V2 — metrics (Cloud Monitoring API) + cost estimate
# ---------------------------------------------------------------------------
import datetime  # noqa: E402

_MON_URL = "https://monitoring.googleapis.com/v3/projects/{p}/timeSeries"


def _access_token(cp):
    """gcloud access token for the project's identity (honors impersonation)."""
    args, env = provisioner._auth(cp)
    imp = []
    if "--impersonate-service-account" in args:
        i = args.index("--impersonate-service-account")
        imp = args[i:i + 2]
    res = shell.run(["gcloud", "auth", "print-access-token", *imp], env=env)
    return res.output.strip() if res.ok else None


def _ts(pid, token, metric, start, end, period, aligner, reducer=None, group_by=None):
    if not requests or not token:
        return []
    params = {
        "filter": f'metric.type="{metric}"',
        "interval.startTime": start, "interval.endTime": end,
        "aggregation.alignmentPeriod": f"{period}s",
        "aggregation.perSeriesAligner": aligner,
    }
    if reducer:
        params["aggregation.crossSeriesReducer"] = reducer
    if group_by:
        params["aggregation.groupByFields"] = group_by
    try:
        r = requests.get(_MON_URL.format(p=pid), params=params,
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        if r.status_code != 200:
            return []
        return r.json().get("timeSeries", [])
    except Exception:
        return []


def _sum_points(series):
    total = 0.0
    for s in series:
        for p in s.get("points", []):
            v = p.get("value", {})
            total += float(v.get("int64Value") or v.get("doubleValue") or 0)
    return total


def metrics(cp, days: int = 1) -> dict:
    """Cloud Run metrics over the last `days` (default 24h): request count,
    5xx error rate, p95 latency, and billable instance-seconds (for cost)."""
    pid, region, svc, args, env = _common(cp)
    if not pid:
        return {}
    token = _access_token(cp)
    if not token:
        return {"error": "Could not get an access token (re-run `gcloud auth login`)."}

    now = datetime.datetime.utcnow()
    start = (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    period = days * 86400

    # Cloud Monitoring requires the service in the filter — append it.
    def q(metric, aligner, reducer=None, group_by=None):
        params_metric = f'{metric}" AND resource.labels.service_name="{svc}'
        return _ts(pid, token, params_metric, start, end, period, aligner, reducer, group_by)

    rc = q("run.googleapis.com/request_count", "ALIGN_DELTA", "REDUCE_SUM",
           "metric.labels.response_code_class")
    total = _sum_points(rc)
    err = _sum_points([s for s in rc
                       if s.get("metric", {}).get("labels", {}).get("response_code_class") == "5xx"])

    lat = q("run.googleapis.com/request_latencies", "ALIGN_PERCENTILE_95", "REDUCE_MEAN")
    p95 = None
    lat_pts = [float(p.get("value", {}).get("doubleValue") or 0)
               for s in lat for p in s.get("points", [])]
    if lat_pts:
        p95 = round(sum(lat_pts) / len(lat_pts))

    bit = q("run.googleapis.com/container/billable_instance_time", "ALIGN_SUM", "REDUCE_SUM")
    inst_sec = _sum_points(bit)

    return {
        "days": days,
        "requests": int(total),
        "error_rate": round(100 * err / total, 2) if total else 0.0,
        "p95_ms": p95,
        "billable_instance_sec": int(inst_sec),
        "has_data": total > 0 or inst_sec > 0,
    }
