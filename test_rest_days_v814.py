from garmin_recovery import rest_days

REG = {"entries": [{"date": "2026-11-05"}, {"date": "2026-11-03"}, {"date": "2026-11-09"}, {"date": "mal"}, "x"]}


def test_confirmed_ignores_future_and_invalid():
    assert sorted(rest_days.confirmed(REG, "2026-11-05")) == ["2026-11-03", "2026-11-05"]


def test_annotate_marks_only_days_without_sessions():
    series = [{"date": "2026-11-03", "sessions": 2}, {"date": "2026-11-04", "sessions": 0}, {"date": "2026-11-05", "sessions": 0}]
    rest_days.annotate(series, REG, "2026-11-05")
    assert [r["rest_confirmed"] for r in series] == [False, False, True]


def test_summary_counts_and_conflicts():
    s = rest_days.summary(REG, "2026-11-05", [{"date": "2026-11-03"}, {"date": "2026-11-04", "removed": 1}])
    assert s["last7"] == 1 and s["last28"] == 1 and s["today"] is True
    assert s["dates_28d"] == ["2026-11-05"] and s["conflicts"] == ["2026-11-03"]


def test_missing_file_is_empty(tmp_path):
    assert rest_days.load(tmp_path) is None
    s = rest_days.summary(None, "2026-11-05")
    assert s["last7"] == 0 and s["dates_28d"] == [] and s["today"] is False
