"""Read-only Cloud SQL backup-health for a CloudProject's attached instance(s).

Surfaces whether the database behind a managed Cloud Run service is actually
protected (automated backups + PITR + a recent successful backup), so a silent
gap is visible in Atlas -> Manage instead of discovered by accident.

READ ONLY. This module only issues SQL Admin API GET/list calls. It never
mutates a GCP resource and never runs a state-changing command. Enabling or
patching backups stays a manual, one-time GCP operation.
"""
from __future__ import annotations

import datetime
import json
import time

from . import provisioner, shell
from .manage import _access_token

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

_SQL = "https://sqladmin.googleapis.com/v1/projects/{p}/instances/{i}"
_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 300          # cache each instance's health for 5 min
_STALE_HOURS = 48   # a "recent" successful backup must be newer than this


def _service_cloudsql_instances(cp) -> list[str]:
    """Instance connection names attached to the Cloud Run service, read from the
    `run.googleapis.com/cloudsql-instances` template annotation. [] if none."""
    pid = provisioner._project_id(cp)
    region = provisioner._region(cp)
    svc = provisioner._service_name(cp)
    args, env = provisioner._auth(cp)
    if not pid:
        return []
    res = shell.run(["gcloud", "run", "services", "describe", svc,
                     "--project", pid, "--region", region, "--format=json", *args], env=env)
    if not res.ok:
        return []
    try:
        d = json.loads(res.output)
    except Exception:
        return []
    ann = ((((d.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("annotations") or {})
    raw = ann.get("run.googleapis.com/cloudsql-instances") or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _neutral(instance, project, region, note) -> dict:
    # Missing visibility != missing backups: neutral 'unknown', never 'red'.
    return {"instance": instance, "project": project, "region": region,
            "status": "unknown", "unavailable": note, "reasons": [note]}


def _get(url, token, params=None):
    if not requests or not token:
        return None, "no-token"
    try:
        r = requests.get(url, params=params or {},
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        return r, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:140]


def get_backup_health(cp, instance_connection_name: str) -> dict:
    """READ-ONLY backup posture for one Cloud SQL instance (`project:region:name`)."""
    parts = instance_connection_name.split(":")
    if len(parts) != 3:
        return _neutral(instance_connection_name, "", "", "unavailable (malformed instance name)")
    project, region, instance = parts

    cached = _CACHE.get(instance_connection_name)
    if cached and (time.time() - cached[0]) < _TTL:
        return cached[1]

    token = _access_token(cp)
    if not token:
        return _neutral(instance, project, region, "unavailable (no access token — gcloud auth)")

    # 1. instances.get
    r, err = _get(_SQL.format(p=project, i=instance), token)
    if r is None:
        return _neutral(instance, project, region, f"unavailable ({err})")
    if r.status_code == 403:
        return _neutral(instance, project, region, "unavailable (permission — grant cloudsql.viewer)")
    if r.status_code in (404, 410):
        return _neutral(instance, project, region, "unavailable (instance not found)")
    if r.status_code != 200:
        return _neutral(instance, project, region, f"unavailable (HTTP {r.status_code})")
    inst = r.json()
    st = inst.get("settings", {}) or {}
    bc = st.get("backupConfiguration", {}) or {}
    enabled = bool(bc.get("enabled"))
    pitr = bool(bc.get("pointInTimeRecoveryEnabled"))
    state = inst.get("state", "UNKNOWN")
    retention = (bc.get("backupRetentionSettings") or {}).get("retainedBackups")
    log_days = bc.get("transactionLogRetentionDays")
    window = bc.get("startTime")

    # 2. backupRuns.list -> newest SUCCESSFUL
    last_ok = None
    rr, _ = _get(_SQL.format(p=project, i=instance) + "/backupRuns", token, {"maxResults": 5})
    if rr is not None and rr.status_code == 200:
        for run in (rr.json().get("items") or []):
            if run.get("status") == "SUCCESSFUL":
                last_ok = _parse_dt(run.get("endTime") or run.get("windowStartTime"))
                break

    # 3. evaluate
    now = datetime.datetime.now(datetime.timezone.utc)
    reasons: list[str] = []
    if not enabled:
        status = "red"
        reasons.append("Automated backups are OFF")
    else:
        if state != "RUNNABLE":
            reasons.append(f"Instance state is {state}")
        if not pitr:
            reasons.append("Point-in-time recovery (PITR) is OFF — nightly-only")
        if last_ok is None:
            reasons.append("Backups enabled — awaiting first successful backup")
        elif (now - last_ok).total_seconds() > _STALE_HOURS * 3600:
            reasons.append(f"Last successful backup older than {_STALE_HOURS}h")
        status = "green" if not reasons else "amber"

    result = {
        "instance": instance, "project": project, "region": region,
        "db_version": inst.get("databaseVersion"), "tier": st.get("tier"),
        "state": state,
        "backups_enabled": enabled, "pitr_enabled": pitr,
        "retained_backups": retention, "log_retention_days": log_days,
        "backup_window": window,
        "last_successful_backup": last_ok.isoformat() if last_ok else None,
        "status": status, "reasons": reasons,
        # Guidance text only — Atlas does NOT run this.
        "enable_cmd": (f"gcloud sql instances patch {instance} --project={project} "
                       f"--backup-start-time=03:00 --enable-point-in-time-recovery"),
    }
    _CACHE[instance_connection_name] = (time.time(), result)
    return result


def project_backup_health(cp) -> list[dict]:
    """One BackupHealth per attached Cloud SQL instance. [] if the service has no
    cloudsql-instances annotation (render nothing — not an error)."""
    out = []
    for name in _service_cloudsql_instances(cp):
        try:
            out.append(get_backup_health(cp, name))
        except Exception as e:  # noqa: BLE001
            proj = name.split(":")[0] if ":" in name else ""
            out.append(_neutral(name.split(":")[-1], proj, "", f"unavailable ({str(e)[:80]})"))
    return out
