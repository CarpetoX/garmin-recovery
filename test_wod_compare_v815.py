from garmin_recovery import wod_compare as w

A = {"type": "metcon", "format": "20-15-10-5 For Time", "prescribed_rounds": [20, 15, 10, 5],
     "exercises": [{"name": "power snatch", "load_kg": 35}, {"name": "chest-to-bar pull-ups"}]}
B = {"type": "metcon", "format": "AMRAP", "duration_minutes": 10, "prescribed_round": [
    {"name": "hang power snatch", "load_kg": 45}, {"name": "butterfly pull-ups"}, {"name": "wall balls", "load_kg": 9}]}
C = {"type": "metcon", "format": "AMRAP", "prescribed_round": [{"name": "carrera"}, {"name": "swing americano", "load_kg": 24}]}
E2 = {"type": "metcon", "format": "E2MO2M", "prescribed_round": [
    {"interval": 1, "exercises": [{"name": "remo"}]}, {"interval": 2, "exercises": [{"name": "sit-ups"}, {"name": "swing americano"}]}]}


def test_families():
    assert w.signature(A)["families"] == ["dominadas", "snatch"]
    assert w.family("DB snatch alterno") == "db snatch"
    assert w.signature(E2)["families"] == ["remo", "sit-up", "swing"]


def test_similar_needs_two_shared_families():
    assert w.similarity(w.signature(A), w.signature(B)) > 0.5
    assert w.similarity(w.signature(A), w.signature(C)) == 0.0


def test_annotate_marks_similar_and_repeat():
    cards = [{"date": "2026-11-09", "activity_id": "a", "format": "x", "key": "a"},
             {"date": "2026-10-13", "activity_id": "b", "format": "AMRAP", "result": "5 rondas", "rpe": 9, "key": "b"},
             {"date": "2026-10-01", "activity_id": "c", "format": "x", "key": "c"},
             {"date": "2026-11-20", "activity_id": "d", "format": "x", "key": "d"}]
    w.annotate(cards, {"a": A, "b": B, "c": C, "d": dict(A)})
    a = cards[0]
    assert a["similar"][0]["activity_id"] == "d" and a["similar"][0]["repeat"] is True
    assert a["similar"][1]["activity_id"] == "b" and a["similar"][1]["shared"] == ["dominadas", "snatch"]
    assert a["similar"][1]["only_other"] == ["wall ball"] and a["similar"][1]["only_this"] == []
    assert a["repeat_of"] == ["2026-11-20"] and cards[2]["similar"] == []


def test_empty_detail_is_safe():
    assert w.signature(None)["families"] == [] and w.similarity(w.signature({}), w.signature(A)) == 0.0
