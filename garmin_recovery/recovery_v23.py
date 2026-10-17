#!/usr/bin/env python3
"""Garmin Recovery V2.3: post-TN sleep provenance and privacy-safe symptom guardrails.

The existing V2.2 scoring remains authoritative. V2.3 annotates reliability,
never invents sleep minutes, and only *restricts* exercise guidance.

Use RECOVERY_CHECKIN_B64 (GitHub Actions secret) for optional private check-ins:
base64 of JSON {"YYYY-MM-DD": {"sleepiness": 0..3,
"physical_fatigue": 0..3, "headache": 0..10, "headache_usual": true/false}}.
Raw symptoms are neither returned nor written to the public repository.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")


def _as_local(value, *, utc_if_naive=False):
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            moment = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc)
        else:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc if utc_if_naive else TZ)
        return moment.astimezone(TZ)
    except (ValueError, TypeError, OverflowError):
        return None


def _number(v, low, high):
    if isinstance(v, bool):
        return None
    try:
        v = float(v)
        return v if low <= v <= high else None
    except (ValueError, TypeError):
        return None


def sleep_integrity(assessment, extended):
    """Flag possible side episodes; Body Battery events are NOT confirmed sleep."""
    current = assessment.get("current") or {}
    day = str(current.get("date") or "")
    start = _as_local(current.get("sleep_start_local"))
    end = _as_local(current.get("sleep_end_local"))
    ext_day = (extended.get("days") or {}).get(day) or {}
    raw = ((ext_day.get("body_battery_events") or {}).get("events") or [])
    candidates = 0
    candidate_minutes = 0
    overlapping_events = 0
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("event.eventType") or item.get("eventType") or "").upper()
        if kind != "SLEEP":
            continue
        begin = _as_local(item.get("event.eventStartTimeGmt") or item.get("eventStartTimeGmt"), utc_if_naive=True)
        milliseconds = _number(item.get("event.durationInMilliseconds", item.get("durationInMilliseconds")), 0, 86400000)
        if begin is None or milliseconds is None or milliseconds < 900000:
            continue
        finish = begin + timedelta(milliseconds=milliseconds)
        overlap = 0.0
        if start and end and end > start:
            overlap = max(0.0, (min(finish, end) - max(begin, start)).total_seconds())
        # Full or partial overlap with main episode: never count as a separate period.
        if overlap:
            overlapping_events += 1
        else:
            candidates += 1
            candidate_minutes += round(milliseconds / 60000)
    return {
        "main_sleep_confirmed": bool(start and end and end > start),
        "main_sleep_minutes": round(float(current.get("sleep_hours") or 0) * 60) if current.get("sleep_hours") is not None else None,
        "unconfirmed_separate_events": candidates,
        "unconfirmed_separate_minutes": candidate_minutes,
        "overlapping_body_battery_events": overlapping_events,
        "minutes_added_to_sleep": 0,
        "policy": "Body Battery sleep events are candidates only; never add to confirmed Garmin sleep.",
    }


def score_source_audit(assessment, daily, extended):
    """Do not substitute the sleep component of readiness for the sleep score."""
    current = assessment.get("current") or {}
    day = current.get("date")
    ext_day = (extended.get("days") or {}).get(day) or {}
    main = _number(current.get("sleep_score"), 0, 100)
    tr = (ext_day.get("training_readiness") or
          (daily.get("garmin_metrics") or {}).get("training_readiness") or {})
    component = _number(tr.get("sleep_score"), 0, 100)
    if main is None or component is None:
        flag = "missing_comparison"
    elif abs(main - component) >= 5:
        flag = "different_fields_not_interchangeable"
    else:
        flag = "close_values"
    return {
        "confirmed_sleep_score": main,
        "readiness_sleep_field": component,
        "status": flag,
        "policy": "Use the confirmed sleep-detail score for the recovery model, not the training-readiness component.",
    }


def _read_checkin(day, encoded=None):
    """Use private environment input only. Invalid/unmatched payload is ignored."""
    encoded = os.getenv("RECOVERY_CHECKIN_B64", "") if encoded is None else encoded
    if not encoded:
        return None
    try:
        obj = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
        entry = obj.get(day) if isinstance(obj, dict) else None
        if not isinstance(entry, dict):
            return None
        sleepy = _number(entry.get("sleepiness"), 0, 3)
        physical = _number(entry.get("physical_fatigue"), 0, 3)
        headache = _number(entry.get("headache"), 0, 10)
        usual = entry.get("headache_usual")
        if any(v is None for v in (sleepy, physical, headache)) or not isinstance(usual, bool):
            return None
        return (sleepy, physical, headache, usual)
    except (ValueError, TypeError, UnicodeError, KeyError):
        return None


def enhance_assessment(assessment, extended, daily, now=None, *, checkin_encoded=None):
    """Enhance V2.2 assessment without changing its base score or alert thresholds."""
    if not isinstance(assessment, dict):
        raise ValueError("Recovery assessment must be a mapping")
    result = dict(assessment)
    today = str((result.get("current") or {}).get("date") or "")
    post_tn = str(result.get("work_shift_context") or "") == "post-TN"
    audit = sleep_integrity(result, extended if isinstance(extended, dict) else {})
    alignment = score_source_audit(result, daily if isinstance(daily, dict) else {}, extended if isinstance(extended, dict) else {})
    checkin = _read_checkin(today, checkin_encoded)
    sleepiness = checkin[0] if checkin else None
    physical = checkin[1] if checkin else None
    pain = checkin[2] if checkin else None
    severe_functional = checkin is not None and (sleepiness >= 2 or physical >= 3 or pain >= 5)
    insufficient_sleep = _number((result.get("current") or {}).get("sleep_hours"), 0, 24)
    insufficient_sleep = insufficient_sleep is not None and insufficient_sleep < 6
    restrict_intensity = bool(severe_functional or (post_tn and insufficient_sleep) or result.get("status") == "red")
    reason_codes = []
    if post_tn:
        reason_codes.append("post_night_shift")
    if insufficient_sleep:
        reason_codes.append("short_sleep")
    if audit["unconfirmed_separate_events"]:
        reason_codes.append("unconfirmed_body_battery_sleep_event")
    if severe_functional:
        reason_codes.append("private_subjective_guardrail")
    result["methodology_version"] = "recovery-reliability-v2.3"
    result["v23"] = {
        "version": "2.3",
        "shift_context": "post-TN" if post_tn else result.get("work_shift_context"),
        "sleep_integrity": audit,
        "sleep_score_provenance": alignment,
        "subjective_checkin": "applied_privately" if checkin else "not_provided",
        "subjective_values_exported": False,
        "intensity_guardrail": "avoid_maximum" if restrict_intensity else "use_v22_guidance",
        "reason_codes": reason_codes,
        "baseline_caution": "day_sleep_baseline_not_mature" if result.get("sleep_context") == "day_sleep" and (result.get("baseline_28d") or {}).get("hrv_ms", {}).get("scope") == "overall" else "standard",
        "note": "Conservative context layer; score remains V2.2, not a validated physiological measure.",
    }
    if restrict_intensity:
        # Keep V2.2 raw score visible, but never publish a green clearance when
        # post-TN sleep or a private check-in requires an intensity restriction.
        if result.get("status") == "green":
            result["v23"]["raw_score_before_guardrail"] = result.get("score")
            if _number(result.get("score"), 0, 100) is not None:
                result["score"] = min(round(result["score"]), 74)
            result["status"] = "yellow"
            result["v23"]["reason_codes"].append("green_clearance_blocked")
        result["recommendation"] = "Recuperación prioritaria; evitar cargas máximas y reevaluar sueño, síntomas y calentamiento."
    return result


def install():
    """Idempotent, fail-closed patch on repository working copy."""
    base = Path("recovery_reliability.py")
    wf = Path(".github/workflows/advanced-analytics-rpe.yml")
    if not base.is_file() or not wf.is_file():
        raise SystemExit("Execute --install from the Garmin repository root.")
    text = base.read_text(encoding="utf-8")
    needle = "    assessment['input_freshness'] = {'hrv': hrv_fresh, 'sleep': sleep_fresh, 'heart_rate': hr_fresh}"
    insertion = ("    from recovery_v23 import enhance_assessment\n"
                 "    assessment = enhance_assessment(assessment, extended, daily, now)\n")
    if "enhance_assessment(assessment, extended, daily, now)" not in text:
        if text.count(needle) != 1:
            raise SystemExit("Unsupported recovery_reliability.py: injection anchor missing/ambiguous; no files changed.")
        text = text.replace(needle, insertion + needle, 1)
    workflow = wf.read_text(encoding="utf-8")
    if "recovery_v23.py" not in workflow:
        compile_old = "python -m py_compile advanced_analytics.py rpe_enrichment.py validate_pipeline.py recovery_reliability.py"
        if workflow.count(compile_old) != 1:
            raise SystemExit("Unsupported analytics workflow: compile anchor missing/ambiguous; no files changed.")
        workflow = workflow.replace(compile_old, compile_old + " recovery_v23.py", 1)
    if "RECOVERY_CHECKIN_B64" not in workflow:
        old = "      - name: Fusionar recuperación, sueño y VFC con guardrails\n        run: |"
        new = ("      - name: Fusionar recuperación, sueño y VFC con guardrails\n"
               "        env:\n"
               "          RECOVERY_CHECKIN_B64: ${{ secrets.RECOVERY_CHECKIN_B64 }}\n"
               "        run: |")
        if workflow.count(old) != 1:
            raise SystemExit("Unsupported analytics workflow: fusion step anchor missing/ambiguous; no files changed.")
        workflow = workflow.replace(old, new, 1)
    base.write_text(text, encoding="utf-8")
    wf.write_text(workflow, encoding="utf-8")
    print("V2.3 installed in repository working tree; run tests before committing.")


def self_test():
    import unittest

    class TestV23(unittest.TestCase):
        def fixture(self):
            return {"current":{"date":"2026-10-09","sleep_hours":4.8,"sleep_score":56,
                       "sleep_start_local":"2026-10-09T08:00:00+02:00",
                       "sleep_end_local":"2026-10-09T12:50:00+02:00"},
                    "status":"red","score":48,"work_shift_context":"post-TN",
                    "sleep_context":"day_sleep","baseline_28d":{"hrv_ms":{"scope":"overall"}}}

        def ex(self):
            return {"days":{"2026-10-09":{"body_battery_events":{"events":[
                {"event.eventType":"SLEEP", "event.eventStartTimeGmt":"2026-10-09T04:04:14.0",
                 "event.durationInMilliseconds":3960000},
                {"event.eventType":"SLEEP", "event.eventStartTimeGmt":"2026-10-09T08:30:00.0",
                 "event.durationInMilliseconds":1800000}]},
                "training_readiness":{"sleep_score":43}}}}

        def test_separate_event_not_added(self):
            a = sleep_integrity(self.fixture(), self.ex())
            self.assertEqual(a["unconfirmed_separate_events"], 1)
            self.assertEqual(a["unconfirmed_separate_minutes"], 66)
            self.assertEqual(a["minutes_added_to_sleep"], 0)
            self.assertEqual(a["overlapping_body_battery_events"], 1)

        def test_score_source_not_overwritten(self):
            a = enhance_assessment(self.fixture(), self.ex(), {})
            self.assertEqual(a["current"]["sleep_score"], 56)
            self.assertEqual(a["v23"]["sleep_score_provenance"]["readiness_sleep_field"], 43)
            self.assertEqual(a["score"], 48)

        def test_private_subjective_guardrail(self):
            raw = json.dumps({"2026-10-09":{"sleepiness":3,"physical_fatigue":1,
                "headache":2,"headache_usual":True}}).encode()
            a = enhance_assessment(self.fixture(), self.ex(), {}, checkin_encoded=base64.b64encode(raw).decode())
            self.assertEqual(a["v23"]["subjective_checkin"], "applied_privately")
            self.assertNotIn("headache", json.dumps(a))
            self.assertEqual(a["v23"]["intensity_guardrail"], "avoid_maximum")

        def test_ignore_invalid_private_payload(self):
            a = enhance_assessment(self.fixture(), self.ex(), {}, checkin_encoded="not base64")
            self.assertEqual(a["v23"]["subjective_checkin"], "not_provided")

        def test_no_new_green_clearance(self):
            d = self.fixture()
            d["status"] = "yellow"
            d["score"] = 72
            out = enhance_assessment(d, {"days":{}}, {}, checkin_encoded="")
            self.assertEqual(out["v23"]["intensity_guardrail"], "avoid_maximum")
            self.assertEqual(out["score"], 72)

        def test_subjective_checkin_blocks_green_without_exposing_symptoms(self):
            fixture = self.fixture()
            fixture["status"] = "green"
            fixture["score"] = 91
            fixture["current"]["sleep_hours"] = 8
            fixture["work_shift_context"] = "free"
            private = {"2026-10-09":{"sleepiness":3,"physical_fatigue":0,
                       "headache":0,"headache_usual":True}}
            payload = base64.b64encode(json.dumps(private).encode()).decode()
            out = enhance_assessment(fixture, {}, {}, checkin_encoded=payload)
            self.assertEqual(out["status"], "yellow")
            self.assertEqual(out["score"], 74)
            self.assertEqual(out["v23"]["raw_score_before_guardrail"], 91)
            self.assertNotIn("headache", json.dumps(out))

        def test_idempotent_with_no_events(self):
            out = enhance_assessment(self.fixture(), {"days":{}}, {})
            self.assertEqual(out["v23"]["sleep_integrity"]["unconfirmed_separate_events"], 0)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestV23)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    if "--install" in sys.argv:
        install()
    elif "--self-test" in sys.argv:
        self_test()
    else:
        print("Usage: python recovery_v23.py --self-test | --install")
