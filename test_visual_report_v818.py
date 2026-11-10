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
    assert "no has respondido la encuesta" in html and "libre" in html


def test_helpers_are_safe():
    assert vr.num(None) == "—" and vr.num(float("nan")) == "—" and vr.num(1062.9) == "1.063" and vr.num(8.73, 1) == "8,7"
    assert "Sin datos" in vr.line_chart([], [("x", "X", "s1")]) and vr.bb_curve([]).startswith("<p")
    assert vr.ddmm("2026-11-10") == "mar 10 nov"


def test_survey_section_and_bb_time(tmp_path):
    from garmin_recovery import sensations as sn
    root = _root(tmp_path)
    sn.record(root, "2026-11-10", {"cansancio": "Cansado", "agujetas": "Moderadas", "estres": "Bajo", "motivacion": "Con muchas ganas"}, time="23:43")
    (root / "garmin_body_battery.json").write_text(json.dumps({"days": {"2026-11-10": {
        "charged": 56, "drained": 59, "endTimestampLocal": "2026-11-10T19:50:00.0",
        "bodyBatteryValuesArray": [[1794265200000, 28], None, [1794335940000, 25, "x"], ["a", 3]]}}}), encoding="utf-8")
    html = vr.build(root)
    assert "Encuesta de hoy · 23:43" in html and "Moderadas" in html and "Con muchas ganas" in html and "Últimos 14 días" in html
    assert "a las 19:39" in html  # hora de la última muestra en Madrid, no el fin del bloque


def test_odd_values_do_not_crash(tmp_path):
    root = _root(tmp_path)
    rv3 = json.loads((root / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
    rv3["trend_28d"][0]["date"] = "2026-11-01T00:00"
    rv3["trend_28d"][1]["srpe"] = -5
    (root / "app" / "readiness_v3.json").write_text(json.dumps(rv3), encoding="utf-8")
    (root / "shift_calendar.json").write_text(json.dumps({"days": {"2026-11-11": {"x": 1}}, "shift_hours": []}), encoding="utf-8")
    (root / "recovery_assessment.json").write_text(json.dumps({"confidence": {"x": 1}}), encoding="utf-8")
    assert "Turnos" in vr.build(root) and vr.num(-0.4) == "0"


def test_sensations_record_rejects_unknown(tmp_path):
    from garmin_recovery import sensations as sn
    try:
        sn.record(tmp_path, "2026-11-10", {"cansancio": "Reventado"})
    except ValueError:
        pass
    else:
        raise AssertionError("debía rechazar una etiqueta desconocida")
    sn.record(tmp_path, "2026-11-09", {"estres": "Alto"})
    w = sn.window(sn.load(tmp_path), "2026-11-10", 3)
    assert [r["estres"] for r in w] == [None, 2, None] and sn.by_date(sn.load(tmp_path), "2026-11-08") == {}


def test_full_survey_index_and_legacy(tmp_path):
    from garmin_recovery import sensations as sn
    (tmp_path / sn.FILE).write_text(json.dumps({"entries": [{"date": "2026-11-10", "time": "23:43",
        "cansancio": {"level": 2, "label": "Cansado"}, "animo": {"level": 0, "label": "Con muchas ganas"}}]}), encoding="utf-8")
    e = sn.load(tmp_path)[0]
    assert e["motivacion"]["label"] == "Con muchas ganas" and "animo" not in e  # V8.18 → V8.19
    full = sn.record(tmp_path, "2026-11-10", {"sueno": "Bien", "molestias": "Leves", "animo": "Bueno", "agujetas": "Moderadas", "estres": "Bajo"},
                     time="23:43", zones=["Rodilla derecha", " "])
    assert full["cansancio"]["level"] == 2 and full["motivacion"]["level"] == 0 and full["zonas"] == ["Rodilla derecha"]
    assert sn.wellbeing(full) == 67 and sn.wellbeing({"estres": {"level": 0}}) is None
    an = sn.analysis(sn.load(tmp_path), "2026-11-10", zone="green")
    texts = " ".join(o["text"] for o in an["observations"])
    assert an["today"] == 67 and "Rodilla derecha" in texts and "no coinciden" in texts and an["load_relation"] is None


def test_load_relation_needs_seven_days(tmp_path):
    from garmin_recovery import sensations as sn
    trend = []
    for d in range(1, 11):
        day = f"2026-11-{d:02d}"
        sn.record(tmp_path, day, {"cansancio": "Cansado" if d % 2 else "Fresco", "agujetas": "Nada", "estres": "Bajo", "animo": "Bueno"})
        trend.append({"date": day, "srpe": 600 if d % 2 == 0 else 100})
    lr = sn.analysis(sn.load(tmp_path), "2026-11-10", trend)["load_relation"]
    assert lr and lr["pairs"] == 9 and lr["after_high"] < lr["after_low"]


def test_panel_card_escapes():
    from garmin_recovery import dashboard as d
    html = d._sensations_html({"index": 67, "zones": ["<b>rodilla</b>"], "items": [{"name": "Cansancio", "label": "Cansado", "level": 2}],
                               "observations": ["<script>x</script>"]})
    assert "Sensaciones de hoy" in html and "<b>rodilla" not in html and "<script>x" not in html and "l2" in html
    assert d._sensations_html(None) == ""
