from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from apps.common.models import AiUsageEvent


@login_required
def ai_usage_dashboard(request):
    now = timezone.now()
    start = now - timedelta(days=30)

    qs = AiUsageEvent.objects.filter(created_at__gte=start)

    # 1) Daily totals
    daily = (
        qs.annotate(day=TruncDate("created_at"))
          .values("day")
          .annotate(tokens=Sum("total_tokens"), cost=Sum("cost_usd"))
          .order_by("day")
    )

    # 2) By action
    by_action = (
        qs.values("action")
          .annotate(tokens=Sum("total_tokens"), cost=Sum("cost_usd"))
          .order_by("-cost")[:25]
    )

    # 3) By user
    by_user = (
        qs.values("actor__username")
          .annotate(tokens=Sum("total_tokens"), cost=Sum("cost_usd"))
          .order_by("-cost")[:25]
    )

    # 4) By model
    by_model = (
        qs.values("model")
          .annotate(tokens=Sum("total_tokens"), cost=Sum("cost_usd"))
          .order_by("-cost")[:25]
    )

    # Totals
    totals = qs.aggregate(tokens=Sum("total_tokens"), cost=Sum("cost_usd"))

    # Prep chart arrays
    chart_labels = [d["day"].strftime("%Y-%m-%d") for d in daily]
    chart_costs = [float(d["cost"] or 0) for d in daily]
    chart_tokens = [int(d["tokens"] or 0) for d in daily]

    return render(request, "common/ai_usage_dashboard.html", {
        "start": start.date(),
        "totals": {"tokens": totals["tokens"] or 0, "cost": totals["cost"] or 0},
        "daily": list(daily),
        "by_action": list(by_action),
        "by_user": list(by_user),
        "by_model": list(by_model),
        "chart_labels": chart_labels,
        "chart_costs": chart_costs,
        "chart_tokens": chart_tokens,
    })
