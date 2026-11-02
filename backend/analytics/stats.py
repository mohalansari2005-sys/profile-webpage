"""Everything the dashboard shows, computed in one place.

The template only prints: numbers arrive formatted and chart geometry arrives
as coordinates, so no arithmetic or timezone logic lives in HTML.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from analytics.models import PageView
from chat.models import ChatLog

RANGES = (7, 30, 90, 365)
DEFAULT_DAYS = 30

# What chat logs for a turn the AI provider failed: "generation unavailable"
# (the gate or generate), "retrieval unavailable" (the embedding) and
# "condense unavailable; <the refusal that caused>". Kept apart from refusals:
# on 2026-10-23 a retired model made every question fail this way for ten
# days, and as "refused" it looked like visitors asking off-topic.
SERVICE_ERROR = (Q(refusal_reason__endswith=" unavailable")
                 | Q(refusal_reason__startswith="condense unavailable"))


def _is_service_error(reason: str) -> bool:
    return reason.endswith(" unavailable") or reason.startswith("condense unavailable")

BREAKDOWN_ROWS = 10
LATEST_QUESTIONS = 25
QUESTION_CHARS = 160

# viewBox units. The SVG stretches to the column (preserveAspectRatio="none"),
# so these set proportions, not pixels; text stays in HTML where it cannot be
# stretched.
CHART_WIDTH = 720
CHART_HEIGHT = 140
OUTER_BAR = 18  # page views / questions, capped so a 7-day range is not slabs
INNER_BAR = 8  # visitors / users, nested inside: always a subset of the outer


def parse_days(raw) -> int:
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return days if days in RANGES else DEFAULT_DAYS


def collect(days: int, now: datetime | None = None) -> dict:
    tz = ZoneInfo(settings.DASHBOARD_TZ)
    local_now = (now or timezone.now()).astimezone(tz)
    today = local_now.date()
    first = today - timedelta(days=days - 1)
    # Local midnights, so the range and the daily buckets agree at both ends.
    start = datetime.combine(first, time.min, tzinfo=tz)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)
    day_list = [first + timedelta(days=i) for i in range(days)]

    views = PageView.objects.filter(created_at__gte=start, created_at__lt=end)
    chats = ChatLog.objects.filter(created_at__gte=start, created_at__lt=end)
    totals = _totals(views, chats)
    daily = _daily(views, chats, tz, day_list)
    all_time = _all_time(tz)

    return {
        "days": days,
        "tz": settings.DASHBOARD_TZ,
        "generated": local_now.strftime("%d %b %Y %H:%M"),
        "first": first,
        "today": today,
        "totals": totals,
        "tiles": _tiles(totals),
        "all_time": all_time,
        "daily": daily,
        "charts": [
            _chart(daily, "Visitors and page views per day",
                   outer=("page_views", "Page views"), inner=("visitors", "Visitors"),
                   describe="{visitors} visitors, {page_views} page views",
                   since=all_time["first_view"]),
            _chart(daily, "Chatbot users and questions per day",
                   outer=("questions", "Questions"), inner=("chat_users", "Chatbot users"),
                   highlight=("service_errors", "Service errors"),
                   describe="{chat_users} chatbot users, {questions} questions, "
                            "{service_errors} service errors",
                   since=all_time["first_question"]),
        ],
        "breakdowns": _breakdowns(views),
        "latest": _latest(tz),
    }


def _totals(views, chats) -> dict:
    v = views.aggregate(visitors=Count("ip_hash", distinct=True), page_views=Count("id"))
    c = chats.aggregate(
        chat_users=Count("ip_hash", distinct=True),
        questions=Count("id"),
        refused=Count("id", filter=Q(refused=True) & ~SERVICE_ERROR),
        service_errors=Count("id", filter=SERVICE_ERROR),
    )
    # The join the shared ip_hash exists for: visitors in range who also asked.
    chatted = (views.filter(ip_hash__in=chats.values("ip_hash"))
               .aggregate(n=Count("ip_hash", distinct=True))["n"])
    return {**v, **c, "visitors_who_chatted": chatted}


def _daily(views, chats, tz, day_list) -> list[dict]:
    day = TruncDate("created_at", tzinfo=tz)
    per_view = {row["day"]: row for row in views.annotate(day=day).values("day").annotate(
        visitors=Count("ip_hash", distinct=True), page_views=Count("id"))}
    per_chat = {row["day"]: row for row in chats.annotate(day=day).values("day").annotate(
        chat_users=Count("ip_hash", distinct=True), questions=Count("id"),
        service_errors=Count("id", filter=SERVICE_ERROR))}
    empty_view = {"visitors": 0, "page_views": 0}
    empty_chat = {"chat_users": 0, "questions": 0, "service_errors": 0}
    rows = []
    for d in day_list:
        v = per_view.get(d, empty_view)
        c = per_chat.get(d, empty_chat)
        rows.append({
            "day": d,
            "visitors": v["visitors"], "page_views": v["page_views"],
            "chat_users": c["chat_users"], "questions": c["questions"],
            "service_errors": c["service_errors"],
        })
    return rows


def _tiles(t: dict) -> list[dict]:
    return [
        {"label": "Visitors", "value": _n(t["visitors"])},
        {"label": "Page views", "value": _n(t["page_views"])},
        {"label": "Chatbot users", "value": _n(t["chat_users"])},
        {"label": "Questions asked", "value": _n(t["questions"])},
        {"label": "Visitors who used the chat",
         "value": _share(t["visitors_who_chatted"], t["visitors"])},
        {"label": "Questions refused", "value": _share(t["refused"], t["questions"])},
        {"label": "Service errors", "value": _n(t["service_errors"]),
         "alert": "service-errors" if t["service_errors"] else "",
         "note": "AI provider unavailable" if t["service_errors"] else ""},
    ]


def _all_time(tz) -> dict:
    v = PageView.objects.aggregate(visitors=Count("ip_hash", distinct=True),
                                   page_views=Count("id"))
    c = ChatLog.objects.aggregate(chat_users=Count("ip_hash", distinct=True),
                                  questions=Count("id"))
    first_view = PageView.objects.order_by("created_at").values_list("created_at", flat=True).first()
    first_question = ChatLog.objects.order_by("created_at").values_list("created_at", flat=True).first()
    return {
        **v, **c,
        # Two dates, not one: the chat has logged since it launched, page views
        # only since this shipped, so one "since" would misdate one of them.
        "first_view": first_view.astimezone(tz).date() if first_view else None,
        "first_question": first_question.astimezone(tz).date() if first_question else None,
    }


def _chart(daily, title, outer, inner, describe, highlight=(None, ""), since=None) -> dict:
    """Daily bars: `outer` wide and grey, `inner` (a subset of it) narrow and
    green inside it, `highlight` (also a subset) amber across the outer bar's
    top. Each field is a (key in `daily`, legend label) pair. Days before
    `since`, the first day anything was recorded, are shaded: they are not
    zero, they were not counted."""
    (outer, outer_label), (inner, inner_label), (highlight, hi_label) = outer, inner, highlight
    busiest = max((d[outer] for d in daily), default=0)
    top = _nice_ceiling(busiest)
    slot = CHART_WIDTH / len(daily)
    outer_w = min(OUTER_BAR, slot * 0.8)
    inner_w = min(INNER_BAR, slot * 0.45)
    untracked = sum(1 for d in daily if since and d["day"] < since)
    bars = []
    for i, d in enumerate(daily):
        centre = slot * i + slot / 2
        h = _height(d[outer], top)
        inner_h = _height(d[inner], top)
        # The highlighted share sits on top of the outer bar, inside its height.
        hi_h = _height(d[highlight], top) if highlight else 0
        bars.append({
            "slot_x": _r(slot * i), "slot_w": _r(slot),
            "x": _r(centre - outer_w / 2), "w": _r(outer_w),
            "y": _r(CHART_HEIGHT - h), "h": _r(h),
            "inner_x": _r(centre - inner_w / 2), "inner_w": _r(inner_w),
            "inner_y": _r(CHART_HEIGHT - inner_h), "inner_h": _r(inner_h),
            "hi_y": _r(CHART_HEIGHT - h), "hi_h": _r(hi_h),
            "title": f"{d['day']:%a %d %b}: " + (
                "before tracking began" if i < untracked else describe.format(**d)),
        })
    # A week has room to name every bar; longer ranges name the two ends.
    labels = [d["day"] for d in daily] if len(daily) <= 7 else [daily[0]["day"], daily[-1]["day"]]
    return {
        "title": title, "outer_label": outer_label, "inner_label": inner_label,
        "hi_label": hi_label, "empty": not busiest,
        "bars": bars, "top": _n(top), "mid": _n(top // 2),
        "width": CHART_WIDTH, "height": CHART_HEIGHT, "mid_y": CHART_HEIGHT / 2,
        "untracked_w": _r(slot * untracked), "labels": labels, "every_day": len(daily) <= 7,
    }


def _breakdowns(views) -> list[dict]:
    fields = [
        ("Pages", "path", "/"),
        ("Referrers", "referrer_host", "(direct or internal)"),
        ("Sources", "source", "(none)"),
        ("Countries", "country", "(unknown)"),
        ("Devices", "device", "(unknown)"),
        ("Browsers", "browser", "(unknown)"),
    ]
    total = views.count()
    out = []
    for title, field, blank in fields:
        rows = (views.values(field)
                .annotate(views=Count("id"), visitors=Count("ip_hash", distinct=True))
                .order_by("-views", field)[:BREAKDOWN_ROWS])
        out.append({"title": title, "rows": [{
            "label": r[field] or blank,
            "visitors": r["visitors"],
            "views": r["views"],
            "pct": round(100 * r["views"] / total) if total else 0,
        } for r in rows]})
    return out


def _latest(tz) -> list[dict]:
    rows = []
    for log in ChatLog.objects.order_by("-created_at")[:LATEST_QUESTIONS]:
        if _is_service_error(log.refusal_reason):
            outcome = "service error"
        elif log.refused:
            outcome = "refused"
        else:
            outcome = "answered"
        question = log.question
        if len(question) > QUESTION_CHARS:
            question = question[:QUESTION_CHARS - 1].rstrip() + "…"
        rows.append({
            "when": log.created_at.astimezone(tz).strftime("%d %b %H:%M"),
            "question": question,
            "outcome": outcome,
            "reason": log.refusal_reason if log.refused else "",
            "latency": f"{log.latency_ms / 1000:.1f} s",
        })
    return rows


def _height(value: int, top: int) -> float:
    if not value:
        return 0
    # A floor of one unit, so a single visit on a busy chart is still a mark.
    return max(value / top * CHART_HEIGHT, 1)


def _nice_ceiling(n: int) -> int:
    """The smallest 2, 4, 6, 8 or 10 x 10^k at or above n: a round top gridline
    with at most about half the plot left empty above the busiest day, and an
    even one, so the labelled midline is a whole number too."""
    if n <= 2:
        return 2
    magnitude = 10 ** (len(str(n - 1)) - 1)
    for step in (2, 4, 6, 8, 10):
        if step * magnitude >= n:
            return step * magnitude
    return n  # unreachable: 10 x magnitude always reaches n


def _r(x: float) -> float:
    return round(x, 2)


def _n(n: int) -> str:
    return f"{n:,}"


def _share(part: int, whole: int) -> str:
    if not whole:
        return "–"
    pct = 100 * part / whole
    if 0 < pct < 1:
        return "<1%"
    return f"{round(pct)}%"
