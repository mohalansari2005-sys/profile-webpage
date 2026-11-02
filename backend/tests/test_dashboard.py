import base64
from datetime import UTC, date, datetime, timedelta

import pytest
from django.core.cache import cache

# Noon in Riyadh on 2026-11-02, so "today" is unambiguous in both UTC and Riyadh.
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def password(settings):
    settings.DASHBOARD_PASSWORD = "s3cret"
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    return "s3cret"


def basic(user, password):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def open_dashboard(client, password, query=""):
    return client.get(f"/dashboard/{query}", HTTP_AUTHORIZATION=basic("me", password))


def view(ip="203.0.113.1", at=None, **fields):
    """A PageView, moved to `at` afterwards because auto_now_add ignores the kwarg."""
    from analytics.models import PageView
    from chat.models import hash_ip

    row = PageView.objects.create(ip_hash=hash_ip(ip), path=fields.pop("path", "/"),
                                  device=fields.pop("device", "desktop"),
                                  browser=fields.pop("browser", "Chrome"), **fields)
    if at is not None:
        PageView.objects.filter(pk=row.pk).update(created_at=at)
    return row


def chat(ip="203.0.113.1", at=None, refused=False, reason="", question="q", latency_ms=1200):
    from chat.models import ChatLog, hash_ip

    row = ChatLog.objects.create(ip_hash=hash_ip(ip), question=question, answer="a",
                                 refused=refused, refusal_reason=reason,
                                 latency_ms=latency_ms, model="gpt-model")
    if at is not None:
        ChatLog.objects.filter(pk=row.pk).update(created_at=at)
    return row


def collect(days=7, now=NOW):
    from analytics.stats import collect

    return collect(days, now=now)


# --- access ---------------------------------------------------------------


def test_the_dashboard_is_a_404_until_a_password_is_set(db, client, settings):
    settings.DASHBOARD_PASSWORD = ""
    assert client.get("/dashboard/").status_code == 404
    assert client.get("/dashboard/", HTTP_AUTHORIZATION=basic("me", "")).status_code == 404


def test_no_credentials_get_a_basic_challenge(db, client, password):
    r = client.get("/dashboard/")
    assert r.status_code == 401
    assert r["WWW-Authenticate"] == 'Basic realm="dashboard"'


@pytest.mark.parametrize("header", [
    basic("me", "wrong"),
    basic("s3cret", ""),  # the username is ignored, not tried as the password
    "Basic s3cret",  # not base64
    "Basic " + base64.b64encode(b"no-colon").decode(),
    "Bearer s3cret",
])
def test_a_wrong_password_is_refused(db, client, password, header):
    r = client.get("/dashboard/", HTTP_AUTHORIZATION=header)
    assert r.status_code == 401
    assert r["WWW-Authenticate"] == 'Basic realm="dashboard"'


def test_the_right_password_opens_it_whatever_the_username(db, client, password):
    for user in ("me", "", "anyone"):
        r = client.get("/dashboard/", HTTP_AUTHORIZATION=basic(user, password))
        assert r.status_code == 200
        assert r["Content-Type"].startswith("text/html")


def test_a_client_that_accepts_only_html_gets_the_page(db, client, password):
    # Browsers add */*, but a stricter client (an uptime checker, curl -H) got
    # a 406 from DRF before the password was even looked at.
    r = client.get("/dashboard/", HTTP_AUTHORIZATION=basic("me", password),
                   HTTP_ACCEPT="text/html")
    assert r.status_code == 200


def test_responses_are_never_cached_or_indexed(db, client, password):
    for r in (client.get("/dashboard/"), open_dashboard(client, password)):
        assert r["Cache-Control"] == "no-store"
        assert r["X-Robots-Tag"] == "noindex"


def test_password_guessing_is_throttled_per_ip(db, client, password, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK,
                               "DEFAULT_THROTTLE_RATES": {"dashboard": "2/min"}}
    attempts = [basic("me", "guess-1"), basic("me", "guess-2"), basic("me", password)]
    codes = [client.get("/dashboard/", HTTP_AUTHORIZATION=header,
                        REMOTE_ADDR="198.51.100.1").status_code for header in attempts]
    # Even the right password is turned away once the guesses used the budget.
    assert codes == [401, 401, 429]
    other = client.get("/dashboard/", HTTP_AUTHORIZATION=basic("me", password),
                       REMOTE_ADDR="198.51.100.2")
    assert other.status_code == 200


def test_the_password_comparison_survives_non_ascii(db, client, settings):
    settings.DASHBOARD_PASSWORD = "مرحبا-كلمة"
    assert open_dashboard(client, "مرحبا-كلمة").status_code == 200
    assert open_dashboard(client, "خطأ").status_code == 401


# --- range ----------------------------------------------------------------


@pytest.mark.parametrize("query, days", [
    ("", 30), ("?days=7", 7), ("?days=90", 90), ("?days=365", 365),
    ("?days=12", 30), ("?days=abc", 30), ("?days=-7", 30),
])
def test_the_range_is_one_of_the_offered_lengths(db, client, password, query, days):
    r = open_dashboard(client, password, query)
    assert r.status_code == 200
    assert r.context["stats"]["days"] == days
    assert len(r.context["stats"]["daily"]) == days


# --- numbers --------------------------------------------------------------


def test_visitors_are_distinct_ip_hashes_and_page_views_are_rows(db):
    view(ip="203.0.113.1", path="/")
    view(ip="203.0.113.1", path="/ar")
    view(ip="203.0.113.2", path="/")
    totals = collect(now=datetime.now(UTC))["totals"]
    assert (totals["visitors"], totals["page_views"]) == (2, 3)


def test_days_are_bucketed_in_the_dashboard_timezone(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"  # UTC+3, no daylight saving
    view(at=datetime(2026, 11, 1, 20, 30, tzinfo=UTC))  # 23:30 on Nov 1 in Riyadh
    view(at=datetime(2026, 11, 1, 21, 30, tzinfo=UTC))  # 00:30 on Nov 2 in Riyadh
    daily = {d["day"]: d["page_views"] for d in collect()["daily"]}
    assert daily[date(2026, 11, 1)] == 1
    assert daily[date(2026, 11, 2)] == 1


def test_the_range_starts_at_local_midnight(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    # A 7-day range ending Nov 2 starts at 00:00 Oct 27 Riyadh = 21:00 Oct 26 UTC.
    view(at=datetime(2026, 10, 26, 20, 59, tzinfo=UTC))
    view(at=datetime(2026, 10, 26, 21, 0, tzinfo=UTC))
    stats = collect()
    assert stats["daily"][0]["day"] == date(2026, 10, 27)
    assert stats["daily"][0]["page_views"] == 1
    assert stats["totals"]["page_views"] == 1


def test_days_without_visits_are_zero_filled(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    view(at=NOW - timedelta(days=3))
    daily = collect()["daily"]
    assert [d["day"] for d in daily] == [date(2026, 10, 27) + timedelta(days=i) for i in range(7)]
    assert [d["page_views"] for d in daily] == [0, 0, 0, 1, 0, 0, 0]
    assert [d["questions"] for d in daily] == [0] * 7


def test_chat_metrics_come_from_the_chat_log(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    view(ip="203.0.113.1", at=NOW)
    view(ip="203.0.113.2", at=NOW)
    chat(ip="203.0.113.1", at=NOW)
    chat(ip="203.0.113.1", at=NOW, refused=True, reason="weather: unrelated")
    chat(ip="203.0.113.9", at=NOW, refused=True, reason="generation unavailable")
    chat(ip="203.0.113.9", at=NOW - timedelta(days=30))  # outside the range
    totals = collect()["totals"]
    assert totals["chat_users"] == 2
    assert totals["questions"] == 3
    # .9 asked but never sent a page view, so only .1 of the two visitors chatted.
    assert totals["visitors_who_chatted"] == 1
    # Service errors are their own number, not refusals.
    assert totals["refused"] == 1
    assert totals["service_errors"] == 1
    today = collect()["daily"][-1]
    assert (today["chat_users"], today["questions"], today["service_errors"]) == (2, 3, 1)


def test_all_time_counts_ignore_the_range(db):
    view(ip="203.0.113.1", at=NOW - timedelta(days=400))
    view(ip="203.0.113.2", at=NOW)
    chat(ip="203.0.113.1", at=NOW - timedelta(days=500))
    stats = collect()
    assert stats["totals"]["page_views"] == 1
    assert stats["all_time"]["visitors"] == 2
    assert stats["all_time"]["page_views"] == 2
    assert stats["all_time"]["questions"] == 1
    assert stats["all_time"]["first_view"] == (NOW - timedelta(days=400)).date()
    assert stats["all_time"]["first_question"] == (NOW - timedelta(days=500)).date()


def test_breakdowns_count_views_per_value(db):
    view(ip="203.0.113.1", path="/", at=NOW)
    view(ip="203.0.113.2", path="/", at=NOW)
    view(ip="203.0.113.2", path="/ar", at=NOW)
    pages = {b["title"]: b for b in collect()["breakdowns"]}["Pages"]["rows"]
    assert [(r["label"], r["visitors"], r["views"]) for r in pages] == [("/", 2, 2), ("/ar", 1, 1)]


def test_blank_values_get_a_readable_label(db):
    view(at=NOW)
    labels = {b["title"]: b["rows"][0]["label"] for b in collect()["breakdowns"]}
    assert labels["Referrers"] == "(direct or internal)"
    assert labels["Countries"] == "(unknown)"


def test_the_chart_is_one_bar_per_day_scaled_to_the_busiest(db):
    view(ip="203.0.113.1", at=NOW)
    view(ip="203.0.113.1", at=NOW)
    chart = collect()["charts"][0]  # visitors and page views
    assert len(chart["bars"]) == 7
    assert chart["bars"][0]["h"] == 0
    today = chart["bars"][-1]
    assert today["h"] == chart["height"]  # 2 views, the busiest day, fills the plot
    assert 0 < today["inner_h"] < today["h"]  # 1 visitor, nested inside


@pytest.mark.parametrize("busiest, top", [
    (0, 2), (1, 2), (2, 2), (3, 4), (9, 10), (10, 10), (11, 20), (28, 40), (367, 400),
    (1001, 2000),
])
def test_the_scale_tops_out_at_a_round_even_number(busiest, top):
    # Even, so the midline gets a whole-number label; finer than 1-2-5, so a
    # 28-view day is not drawn against a scale of 50.
    from analytics.stats import _nice_ceiling

    assert _nice_ceiling(busiest) == top


def test_the_midline_is_labelled(db):
    for _ in range(3):
        view(at=NOW)
    chart = collect()["charts"][0]
    assert (chart["top"], chart["mid"]) == ("4", "2")


def test_days_before_the_first_record_are_marked_untracked(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    view(at=NOW - timedelta(days=2))  # the first page view ever: Sat 31 Oct
    chat(at=NOW - timedelta(days=30))  # the chat logged long before this range
    views, chats = collect()["charts"]
    # 27-30 Oct were not counted at all, which is not the same as zero visits.
    assert views["untracked_w"] == round(views["width"] / 7 * 4, 2)
    assert views["bars"][3]["title"] == "Fri 30 Oct: before tracking began"
    assert "before tracking" not in views["bars"][4]["title"]
    assert chats["untracked_w"] == 0


def test_a_week_names_every_day_and_longer_ranges_their_ends(db, settings):
    settings.DASHBOARD_TZ = "Asia/Riyadh"
    assert collect(days=7)["charts"][0]["labels"] == [
        date(2026, 10, 27) + timedelta(days=i) for i in range(7)]
    assert collect(days=30)["charts"][0]["labels"] == [date(2026, 10, 4), date(2026, 11, 2)]


# --- the page -------------------------------------------------------------


def test_an_empty_dashboard_still_renders(db, client, password):
    r = open_dashboard(client, password)
    assert r.status_code == 200
    html = r.content.decode()
    assert "Visitors" in html
    # What the owner sees on the first day: said in words, not as a scale of
    # "2" over blank bars or a "Top 0" / "Latest 0 questions" heading.
    assert "<span>No page views in this range.</span>" in html  # the chart, not a table
    assert "<span>No questions in this range.</span>" in html
    assert 'class="tick' not in html
    assert "Top 0" not in html
    assert "Latest 0" not in html


def test_one_of_each_reads_in_the_singular(db, client, password):
    view()
    chat()
    html = open_dashboard(client, password).content.decode()
    assert "<b>1</b> visitor ·" in html
    assert "<b>1</b> chatbot user ·" in html
    assert "<b>1</b> question since" in html
    assert "Latest question <span" in html


def test_service_errors_are_highlighted_only_when_there_are_some(db, client, password):
    assert 'data-alert="service-errors"' not in open_dashboard(client, password).content.decode()
    chat(refused=True, reason="generation unavailable")
    assert 'data-alert="service-errors"' in open_dashboard(client, password).content.decode()


def test_the_latest_questions_show_how_each_ended(db, client, password):
    chat(question="what did he build", latency_ms=1500)
    chat(question="weather?", refused=True, reason="weather: unrelated to him")
    chat(question="and Majara?", refused=True, reason="generation unavailable")
    html = open_dashboard(client, password).content.decode()
    for text in ("what did he build", "answered", "1.5 s",
                 "weather?", "refused", "weather: unrelated to him",
                 "and Majara?", "service error",
                 "Latest 3 questions", "any date, not only this range"):
        assert text in html


def test_questions_and_reasons_take_their_own_direction(db, client, password):
    # On the page's LTR, an Arabic question with Latin words came out in the
    # wrong word order; dir="auto" lets each cell follow its first letter.
    chat(question="كم سنة خبرة لديه في Python و Django؟", refused=True, reason="خارج الموضوع")
    html = open_dashboard(client, password).content.decode()
    assert '<td class="q wrap" dir="auto">كم سنة' in html
    assert '<span class="reason wrap" dir="auto">خارج الموضوع</span>' in html


def test_a_full_outage_day_stays_amber_over_the_green(db, client, password):
    # Every question failed and each came from its own user, the 2026-10-23
    # pattern: amber covers the whole bar. Drawn under the green users bar it
    # showed only as two slivers at 90 days, so the amber must come last.
    chat(ip="203.0.113.1", refused=True, reason="generation unavailable")
    chat(ip="203.0.113.2", refused=True, reason="generation unavailable")
    html = open_dashboard(client, password, "?days=90").content.decode()
    today = html.split('<g class="day">')[-1]  # the chat chart's last bar
    assert 'class="inner"' in today
    assert today.index('class="inner"') < today.index('class="hi"')


def test_visitor_supplied_strings_are_escaped(db, client, password):
    view(path="/<script>alert(1)</script>", referrer_host="<img src=x onerror=alert(2)>",
         source="<b>src</b>")
    chat(question="<script>alert(3)</script>", refused=True, reason="<i>x</i>")
    html = open_dashboard(client, password).content.decode()
    assert "<script>alert" not in html
    assert "<img src=x" not in html
    assert "<b>src</b>" not in html
    assert "<i>x</i>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
