import json
from pathlib import Path

from garmin_recovery import panel_v9 as pv

CAL = {"days": {"2026-11-03": "TN", "2026-11-11": "MT"}, "shift_hours": {"MT": {"start": "08:00", "end": "22:00"}}}


def _trend(n=20, today="2026-11-10"):
    from datetime import date, timedelta
    t = date.fromisoformat(today)
    return [{"date": (t - timedelta(days=i)).isoformat(), "hrv_ms": 50 + (i % 5), "resting_hr": 57, "sleep_hours": 7.5, "sleep_score": 75,
             "srpe": 300, "v2_score": 80} for i in range(n - 1, -1, -1)]


def test_context_and_normal_range():
    assert pv.context_of("2026-11-03", CAL) == "TN" and pv.context_of("2026-11-04", CAL) == "post-TN"
    assert pv.context_of("2026-11-11", CAL) == "MT" and pv.context_of("2026-11-12", CAL) == "libre" and pv.context_of("mal", CAL) == "libre"
    rng = pv.normal_range(_trend(), "hrv_ms", "2026-11-10", CAL)
    assert rng["n"] == 19 and rng["p10"] <= rng["p50"] <= rng["p90"] and rng["context"]["label"] == "días libres"
    assert pv.normal_range(_trend(5), "hrv_ms", "2026-11-10") is None  # pocos días: sin rango


def test_verdict_direction():
    rng = {"p10": 50, "p50": 55, "p90": 60, "n": 20}
    assert pv.verdict(55, rng, True)[0] == "ok"
    assert pv.verdict(65, rng, True)[0] == "good" and pv.verdict(65, rng, False)[0] == "bad"
    assert pv.verdict(None, rng, True)[0] == "na" and pv.verdict(55, None, True)[0] == "na"


def test_complete_weeks_only_full_weeks():
    s = [{"date": "2026-10-14", "srpe": 100, "rpe": 9}, {"date": "2026-10-20", "srpe": 200, "rpe": 7},
         {"date": "2026-10-27", "srpe": 300, "rpe": 8}, {"date": "2026-11-10", "srpe": 999, "rpe": 9}]
    w = pv.complete_weeks(s, "2026-11-10")
    assert [x["monday"] for x in w] == ["2026-10-19", "2026-10-26", "2026-11-02"]  # la semana del 12/10 no está entera; la actual no cuenta
    assert w[0]["srpe"] == 200 and w[1]["hard"] == 1 and w[2]["sessions"] == 0


def test_render_tabs_and_escaping(tmp_path: Path):
    (tmp_path / "shift_calendar.json").write_text(json.dumps(CAL), encoding="utf-8")
    result = {"date": "2026-11-10", "decision": {"zone": "green", "guidance": {"label": "<b>Listo</b>", "rpe_max": 9}, "crossfit": ["<i>x</i>"]},
              "trend_28d": _trend(28), "sessions_28d": [{"date": "2026-11-10", "label": "<script>s</script>", "srpe": 1, "rpe": 9}],
              "load": {"week_sessions": 3}}
    html = pv.render(tmp_path, result, {"ai_lead": ["<em>lead</em>"], "athlete_progress": {"maxes": [{"name": "press <b>", "series": [], "sessions": 1}]}})
    for t in ('id="p-hoy"', 'id="p-recuperacion"', 'id="p-entrenos"', 'id="p-progreso"', "¿Cómo estás frente a tu normal?",
              "Mañana", "MT 08:00–22:00", "1 sesión", "panel_completo.html"):
        assert t in html, t
    for bad in ("<b>Listo</b>", "<i>x</i>", "<script>s</script>", "<em>lead</em>", "press <b>"):
        assert bad not in html, bad
    assert "{{" not in html
