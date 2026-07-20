from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any

from django.conf import settings
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest
from google.oauth2 import service_account
import os
from django.conf import settings
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.oauth2 import service_account

@dataclass
class Ga4Summary:
    active_users: int
    sessions: int
    page_views: int

def _client() -> BetaAnalyticsDataClient:
    path = getattr(settings, "GA4_SERVICE_ACCOUNT_FILE", "") or ""
    print("Ga4 service account file: {}".format(path))
    if not path:
        raise RuntimeError(
            "GA4_SERVICE_ACCOUNT_FILE is not set. "
            "Set it in settings or use GOOGLE_APPLICATION_CREDENTIALS."
        )
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"GA4 service account file not found: {path}\n"
            "Fix the path or move the JSON to that location."
        )

    creds = service_account.Credentials.from_service_account_file(
        path,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=creds)



def fetch_summary(property_id: str, start: date, end: date) -> Ga4Summary:
    """
    Fetch summary metrics for a GA4 property in a date range.
    """
    client = _client()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
        ],
    )

    resp = client.run_report(request)

    # Data API returns rows; for pure metrics with no dimensions, expect 1 row
    if not resp.rows:
        return Ga4Summary(active_users=0, sessions=0, page_views=0)

    values = resp.rows[0].metric_values
    return Ga4Summary(
        active_users=int(values[0].value or 0),
        sessions=int(values[1].value or 0),
        page_views=int(values[2].value or 0),
    )
