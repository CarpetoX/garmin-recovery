import json
from pathlib import Path

from garmin_recovery import visual_report as vr


def _root(tmp: Path) -> Path:
    (tmp / "app").mkdir()
    rv3 = {"date": "2026-11-10",
           "decision": {"zone": "green", "agreement": "total", "guidance": {"label": "Listo <b>", "rpe_max": 9, "volume": "100 %", "text": "x"},
                        "crossfit": ["<script>alert(1)</script>"]},
           "readiness": {"score": 73},
           "load": {"week_srpe": 2300.5, "week_sessions": 12, "acwr": 1.41, "monotony": 0.85},
           "trend_28d": [{"date": f"2026-11-{d:02d}", "hrv_ms": 50 + d, "hrv_low_ms": 45, "hrv_high_ms": 60, "resting_hr": 57, "night_hr": 62,
                          "sleep_hours": 7.5, "sleep_score": 55 if d == 5 else 80, "srpe": 0 if d in (5, 6) else 300, "v2_score": 85,
                          "rest_confirmed": d == 5} for d in range(1, 11)],
           "recent_sessions": [{"id": "i1", "date": "2026-11-10", "start_local": "2026-11-10T10:44:35", "label": "WOD <i>", "duration_min": 32.2,
                                "rpe": 9, "srpe": 290, "avg_hr": 156, "max_hr": 176}]}
    (tmp / "app" / "readiness_v3.json").write_text(json.dumps(rv3), encoding="utf-8")
    (tmp / "report_ready.json").write_text(json.dumps({"status": "ready", "cycle_id": "2026-11-10-2245", "verified_at": "2026-11-10T22:49:26+01:00"}), encoding="utf-8")
    (tmp / "crossfit_insights.json").write_text(json.dumps({"activities": [{"date": "2026-11-10", "activity_id": "i1", "manual_blocks": [
        {"activity": "WOD", "rpe": 9, "notes": "E2MO2M <b>", "sensations": "Cansado; agujetas en piernas"}]}]}), encoding="utf-8")
    (tmp / "shift_calendar.json").write_text(json.dumps({"days": {"2026-11-11": "MT"}, "shift_hours": {"MT": {"start": "08:00", "end": "22:00"}}}), encoding="utf-8")
    return tmp


def test_page_has_sections_and_escapes(tmp_path):
    html = vr.build(_root(tmp_path))
    for text in ("Cierre nocturno", "Decisión del día", "Recuperación por modelo", "Sueño", "HRV y frecuencia cardiaca",
                 "Carga", "Entrenamiento de hoy", "Sensaciones", "Turnos", "MT 08:00–22:00", "desc.", "Cansado; agujetas en piernas"):
        assert text in html, text
    assert "<script>alert" not in html and "Listo <b>" not in html and "WOD <i>" not in html and "E2MO2M <b>" not in html


def test_missing_optional_files_still_render(tmp_path):
    root = _root(tmp_path)
    (root / "crossfit_insights.json").unlink()
    (root / "shift_calendar.json").unlink()
    html = vr.build(root)
    assert "Aún no hay sensaciones" in html and "libre" in html


def test_helpers_are_safe():
    assert vr.num(None) == "—" and vr.num(float("nan")) == "—" and vr.num(1062.9) == "1.063" and vr.num(8.73, 1) == "8,7"
    assert "Sin datos" in vr.line_chart([], [("x", "X", "s1")]) and vr.bb_curve([]).startswith("<p")
    assert vr.ddmm("2026-11-10") == "mar 10 nov"
