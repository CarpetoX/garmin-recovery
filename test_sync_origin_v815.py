from datetime import datetime, timezone

from garmin_recovery import monitor_v231 as m, sync_origin_ledger as led

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
OK = {"source_verified": True, "origin_source": "apps_script_backup", "auth_method": "hmac", "cycle_id": "2026-11-10-0830"}


def test_record_only_verified(tmp_path):
    p = tmp_path / "l.json"
    assert led.record(OK, "111", NOW, p) is True
    assert led.record({"source_verified": False, "origin_source": "workflow_dispatch_unattributed"}, "222", NOW, p) is False
    assert led.record(OK, "", NOW, p) is False
    assert led.verified_run_ids(led.load(p)) == {"111"}


def test_record_prunes_and_dedupes(tmp_path):
    p = tmp_path / "l.json"
    led.record(OK, "1", datetime(2026, 9, 1, tzinfo=timezone.utc), p)
    led.record(OK, "2", NOW, p)
    led.record(OK, "2", NOW, p)
    assert [r["run_id"] for r in led.load(p)["runs"]] == ["2"]


def test_malformed_ledger_is_empty(tmp_path):
    p = tmp_path / "l.json"
    p.write_text("[1]", encoding="utf-8")
    assert led.verified_run_ids(led.load(p)) == set()


def _run(i, when):
    return {"id": i, "status": "completed", "conclusion": "success", "event": "workflow_dispatch", "created_at": when}


def test_verified_dispatch_counts_as_apps_script():
    now = datetime(2026, 11, 10, 12, 0, tzinfo=m.TZ)
    runs = [_run(1, "2026-11-10T07:31:38Z"), _run(2, "2026-11-09T21:46:40Z"), _run(3, "2026-11-09T15:46:42Z"), _run(4, "2026-11-09T07:31:44Z")]
    a = m.audit_slots(now, runs, verified_run_ids={"1", "2", "3", "4"})
    assert a["state"] == "recovered" and a["recovered_by_manual"] == []
    assert len(a["recovered_by_apps_script_verified"]) == 4 and a["dispatch_origin_verified"] is True
    b = m.audit_slots(now, runs, verified_run_ids={"1"})
    assert len(b["recovered_by_manual"]) == 3 and b["dispatch_origin_verified"] is False
    c = m.audit_slots(now, runs)
    assert c["dispatch_origin_verified"] is False and len(c["recovered_by_manual"]) == 4
