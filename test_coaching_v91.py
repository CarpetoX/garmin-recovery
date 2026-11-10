import json
from pathlib import Path

from garmin_recovery import coaching as co


def _s(date, rpe=None, srpe=None, trimp=None):
    return {"date": date, "rpe": rpe, "srpe": srpe, "trimp": trimp, "minutes": 30}


def test_ratio_and_estimate():
    ss = [_s(f"2026-10-{d:02d}", 8, 400, 80) for d in range(1, 9)] + [_s("2026-10-09", None, None, 50)]
    r = co.srpe_trimp_ratio(ss)
    assert r == {"ratio": 5.0, "n": 8}
    est = co.with_estimate(ss, r)
    assert est[-1]["load_estimated"] == 250 and est[-1]["load_official"] == 0 and est[0]["load_estimated"] is None
    assert co.srpe_trimp_ratio(ss[:5]) is None  # pocas sesiones: sin estimación


def test_weeks_and_deload():
    from datetime import date, timedelta
    start = date(2026, 9, 28)  # lunes
    ss = []
    for i in range(43):
        d = start + timedelta(days=i)
        if d.weekday() in (0, 2, 4):
            light = date(2026, 10, 5) <= d <= date(2026, 10, 11)
            ss.append(dict(_s(d.isoformat(), 8, 100 if light else 500), load_official=100 if light else 500, load_estimated=None))
    weeks = co.complete_weeks(ss, "2026-11-10")
    assert [w["monday"] for w in weeks][0] == "2026-09-28" and weeks[-1]["monday"] == "2026-11-02"  # nunca la semana en curso
    assert weeks[1]["total"] == 300 and weeks[0]["total"] == 1500 and weeks[0]["hard"] == 3
    dl = co.deload(weeks)
    assert dl["status"] == "due" and dl["run"] == 4 and dl["last_light"] == "2026-10-05"
    assert co.deload([{"monday": "a", "total": 1}] * 3)["status"] == "insufficient"


def test_post_tn_months():
    daily = {"2026-10-03": {"v2_score": "40"}, "2026-10-04": {"v2_score": "80"}, "2026-10-05": {"v2_score": "70"},
             "2026-10-10": {"v2_score": "50"}, "2026-10-20": {"v2_score": "45"}}
    ctx = {"2026-10-03": "post-TN", "2026-10-10": "post-TN", "2026-10-20": "post-TN"}
    sess = [_s("2026-10-03", 9), _s("2026-10-04", 7)]
    m = co.post_tn_months(daily, sess, lambda d: ctx.get(d, "libre"))
    assert m[0]["post"] == {"days_scored": 3, "score": 45, "rpe": 9.0, "sessions": 1} and m[0]["rest"]["score"] == 75
    t = co.post_tn_today(m)
    assert t == {"days": 3, "score": 45.0, "rpe": 9.0, "rest_score": 75.0}


def test_tests_registry(tmp_path: Path):
    co.record_test(tmp_path, "2026-09-01", "fran", 300)
    co.record_test(tmp_path, "2026-11-01", "fran", 270)
    co.record_test(tmp_path, "2026-11-01", "fran", 250, scaled="thrusters 35 kg")
    co.record_test(tmp_path, "2026-10-01", "sentadilla_3rm", 150)
    s = {(r["test"], r["scaled"]): r for r in co.tests_summary(co.load_tests(tmp_path), "2026-12-30")}
    rx = s[("fran", "")]
    assert rx["change"] == -30 and rx["improved"] is True and rx["best"] == 270 and rx["due"] is True
    assert s[("fran", "thrusters 35 kg")]["count"] == 1 and s[("sentadilla_3rm", "")]["prev"] is None
    assert co.fmt_value(270, "s") == "4:30" and co.fmt_value(152.5, "kg") == "152,5 kg"
    for bad in (("nope", 1), ("fran", "x")):
        try:
            co.record_test(tmp_path, "2026-11-01", *bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    (tmp_path / co.TESTS_FILE).write_text(json.dumps({"entries": [{"test": "fran", "date": "mal", "value": 1}, "x"]}), encoding="utf-8")
    assert co.load_tests(tmp_path) == []
