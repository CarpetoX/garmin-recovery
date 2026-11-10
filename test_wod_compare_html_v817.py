from garmin_recovery import dashboard as d


def test_side_by_side_block():
    m = {"format": "20-15-10-5 For Time", "result": "completado · 100 reps en total", "rpe": 8.5, "timing": ["Oficial 7:59", "Cap 10:00"],
         "similar": [{"date": "2026-10-13", "format": "AMRAP", "result": "5 rondas + 5 reps · 155 reps en total", "rpe": 9, "timing": [],
                      "shared": ["dominadas", "snatch"], "only_this": [], "only_other": ["wall ball"], "repeat": False}]}
    html = d._similar_html(m)
    assert "Se parece al 13/10" in html and "7:59" in html and "5 rondas + 5 reps" in html and "155 reps" not in html
    assert "Solo el 13/10" in html and "wall ball" in html and "width:85%" in html and "width:90%" in html


def test_escapes_and_empty():
    assert d._similar_html({"similar": []}) == ""
    m = {"format": "<b>x</b>", "similar": [{"date": "2026-10-13", "format": "<i>", "shared": ["<s>"], "repeat": True}]}
    html = d._similar_html(m)
    assert "<b>x</b>" not in html and "<i>" not in html and "Mismo WOD que el" in html
