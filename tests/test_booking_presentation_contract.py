"""QA-005/007/008 — booking presentation contract, without mutating reservations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = [
    "app/templates/bookings/mine.html",
    "app/templates/public/experience-detail.html",
    "app/templates/bookings/confirm.html",
]


def test_booking_templates_still_parse(app):
    # Parsing catches broken Jinja blocks in the real pages.
    for template in TEMPLATES:
        app.jinja_env.parse((ROOT / template).read_text(encoding="utf-8"))


def test_brazilian_currency_on_each_booking_surface():
    expected = (
        ("app/templates/bookings/mine.html", "item.price_at_booking"),
        ("app/templates/public/experience-detail.html", "experience.price"),
        ("app/templates/public/experience-detail.html", "experience.regular_price"),
        ("app/templates/bookings/confirm.html", "booking.price_at_booking"),
    )
    for path, value in expected:
        content = (ROOT / path).read_text(encoding="utf-8")
        assert f"'%.2f'|format({value})|replace('.', ',')" in content
        assert f"R$ {{{{ {value} }}}}" not in content


def test_booking_sharing_retains_real_owner_scoped_links():
    content = (ROOT / TEMPLATES[0]).read_text(encoding="utf-8")
    assert "bookings.export_booking_calendar" in content
    assert "bookings.share_booking" in content
    assert 'rel="noopener noreferrer"' in content
    assert "booking-sharing__actions" in content
    assert "booking-sharing__action" in content
    assert "booking-sharing__hint" in content


def test_booking_detail_retains_timeline_and_policies():
    content = (ROOT / TEMPLATES[0]).read_text(encoding="utf-8")
    for needle in (
        'class="booking-detail"',
        "booking-detail__trigger-copy",
        "booking-detail__content",
        "booking-detail__section",
        "booking-detail__policies",
        "row.timeline",
        "event.reason",
        "bookings.withdraw_cancel_request",
        "bookings.request_booking_reschedule",
        "bookings.export_booking_calendar",
        "csrf_token",
    ):
        assert needle in content


def test_booking_details_use_scoped_tokens_and_touch_targets():
    css = (ROOT / "app/static/css/booking-mine.css").read_text(encoding="utf-8")
    scoped = css.split("/* QA-007/008")[1]
    assert ".my-bookings-page .booking-sharing__action" in scoped
    assert ".my-bookings-page .booking-detail > summary" in scoped
    assert "var(--ds-control-min-target)" in scoped
    assert "@media (max-width: 600px)" in scoped
    assert "focus-visible" in scoped
    import re
    assert not re.search(r"#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])", scoped)
    assert "!important" not in scoped


def test_mobile_booking_details_keep_real_actions():
    screen = (ROOT / "mobile/src/app/booking-detail.tsx").read_text(encoding="utf-8")
    for needle in (
        "styles.detailGrid",
        "styles.eventTime",
        "getBookingTimeline(id)",
        "getBookingCalendar(id)",
        "getBookingSafeShare(id)",
        "syncNativeBookingCalendar(id)",
        "requestBookingReschedule(id, slotId)",
        'toFixed(2).replace(".", ",")',
    ):
        assert needle in screen
