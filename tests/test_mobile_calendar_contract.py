"""Static regression checks for native calendar failure handling and lockfile integrity."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"


def test_calendar_does_not_recreate_on_update_failure():
    source = (MOBILE / "src/services/nativeBookingCalendar.ts").read_text()
    assert "await Calendar.updateEventAsync(tracked.id, data)" in source
    assert "const existing = await Calendar.getEventAsync(tracked.id)" in source
    assert "if (existing)" in source
    assert "await Calendar.createEventAsync(writable.id, data)" in source
    assert "catch {\n      // Evento foi removido" not in source


def test_calendar_dependency_matches_expo_sdk_57():
    package = json.loads((MOBILE / "package.json").read_text())
    lock = json.loads((MOBILE / "package-lock.json").read_text())
    assert package["dependencies"]["expo-calendar"] == "~57.0.5"
    assert lock["packages"][""]["dependencies"]["expo-calendar"] == "~57.0.5"
    entry = lock["packages"]["node_modules/expo-calendar"]
    assert entry["version"] == "57.0.5"
    assert entry["integrity"].startswith("sha512-")
    assert entry["resolved"].startswith("https://registry.npmjs.org/expo-calendar/")
