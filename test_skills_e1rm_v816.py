from garmin_recovery import athlete_progress as ap


def _row(date, name, detail):
    return {"date": date, "id": "x", "name": name, "rpe": "", "notes": "", "detail": detail}


ROWS = [
    _row("2026-10-29", "Técnica - handstand push-up déficit", {"type": "skill", "exercise": "handstand push-up",
                                                               "progression": "déficit 20 + 10"}),
    _row("2026-10-29", "Hito - primer bar muscle up", {"type": "skill", "exercise": "bar muscle up", "milestone": "Primer bar muscle up",
                                                       "performed": {"reps": 4, "unbroken": False}}),
    _row("2026-11-03", "Técnica - comba", {"type": "skill", "exercise": "comba: double unders, crossover",
                                           "milestones": ["primer crossover single under", "primer crossover double under"]}),
    _row("2026-11-09", "Técnica - handstand push-ups en déficit", {"type": "skill", "exercise": "handstand push-ups en déficit",
                                                                  "deficit": {"label": "disco 20 kg + disco 5 kg"}, "max_reps_declared": 5}),
]


def test_milestones_list_and_levels():
    sk = ap.skills(ROWS)
    titles = [s["title"] for s in sk if s["kind"] == "hito"]
    assert "Primer crossover double under" in titles and "Primer bar muscle up" in titles
    hspu = next(s for s in sk if s["date"] == "2026-11-09")
    assert hspu["sub"] == "déficit disco 20 kg + disco 5 kg · hasta 5 repeticiones" and hspu["skill"] == "Handstand push-up"


def test_skill_groups_merge_variants():
    g = {x["skill"]: x for x in ap.skill_groups(ap.skills(ROWS))}
    assert g["Handstand push-up"]["sessions"] == 2 and len(g["Handstand push-up"]["levels"]) == 2
    assert g["Handstand push-up"]["level"].startswith("déficit disco 20")
    assert len(g["Comba"]["hitos"]) == 2 and g["Bar muscle up"]["sessions"] == 0


def test_e1rm_series_and_delta():
    entries = {
        "a": {"exercise": "sentadilla trasera", "unit": "kg_total_barra", "date": "2026-10-18", "sets": [{"load": 185, "reps": 1}]},
        "b": {"exercise": "sentadilla trasera", "unit": "kg_total_barra", "date": "2026-11-10",
              "sets": [{"load": 140, "reps": 6}, {"load": 100, "reps": 12}]},
        "c": {"exercise": "power clean + squat clean", "unit": "kg_total_barra", "date": "2026-11-10", "sets": [{"load": 90, "reps": 1}]},
    }
    m = ap.estimated_max(entries)
    assert [x["name"] for x in m] == ["sentadilla trasera"]
    sq = m[0]
    assert sq["series"] == [{"date": "2026-10-18", "e1rm": 185.0}, {"date": "2026-11-10", "e1rm": 168.0}]
    assert sq["delta"] == -17.0 and sq["e1rm"] == 185.0
