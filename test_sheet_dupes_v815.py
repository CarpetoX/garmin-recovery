import json
from datetime import datetime
from pathlib import Path

from garmin_recovery import alerts

NOW = datetime(2026, 11, 10, 14, 0, tzinfo=alerts.TZ)


def _root(tmp: Path, flags):
    (tmp / "app").mkdir()
    (tmp / "app" / "readiness_v3.json").write_text(json.dumps({"generated_at": NOW.isoformat()}), encoding="utf-8")
    (tmp / "crossfit_insights.json").write_text(json.dumps({"data_quality": {"flags": flags}}), encoding="utf-8")
    return tmp


def test_duplicate_rows_raise_alert(tmp_path):
    root = _root(tmp_path, [{"code": "duplicate_sheet_ids", "ids": ["i208205608"], "count": 1}])
    found = [p for p in alerts.problems(root, NOW) if p["key"] == "sheet_dupes"]
    assert found and "i208205608" in found[0]["text"]
    assert alerts._in_scope("sheet_dupes", "chain") and not alerts._in_scope("sheet_dupes", "watchdog")


def test_no_duplicates_no_alert(tmp_path):
    root = _root(tmp_path, [])
    assert not [p for p in alerts.problems(root, NOW) if p["key"] == "sheet_dupes"]
