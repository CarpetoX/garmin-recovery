#!/usr/bin/env python3
"""Regression invariants for Garmin Recovery V2.4.2.

These tests protect data semantics. They do not change recovery/readiness scores.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


def load(name, default):
    try:
        value = json.loads(Path(name).read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def fail(errors, code, detail=None):
    errors.append(code if detail is None else f"{code}:{detail}")


def warn(warnings, code, detail=None):
    warnings.append(code if detail is None else f"{code}:{detail}")


def activity_ids(activities):
    return {
        str(x.get("id"))
        for x in activities
        if isinstance(x, dict) and x.get("id") is not None
    }


def feedback_ids(feedback):
    rows = feedback.get("activities", {}) if isinstance(feedback, dict) else {}
    if isinstance(rows, dict):
        return {str(k) for k in rows if k}
    if isinstance(rows, list):
        return {
            str(x.get("activity_id") or x.get("id"))
            for x in rows
            if isinstance(x, dict) and (x.get("activity_id") or x.get("id"))
        }
    return set()


def test_sleep_integrity(recovery, errors, warnings):
    v23 = recovery.get("v23", {}) if isinstance(recovery, dict) else {}
    integrity = (
        v23.get("sleep_integrity")
        if isinstance(v23, dict)
        else None
    ) or recovery.get("sleep_integrity", {})

    if not isinstance(integrity, dict) or not integrity:
        warn(warnings, "sleep_integrity_missing")
        return

    added = number(integrity.get("minutes_added_to_sleep"))
    if added not in (None, 0):
        fail(errors, "unconfirmed_sleep_added", added)

    unconfirmed = number(integrity.get("unconfirmed_separate_minutes"))
    if unconfirmed and added not in (None, 0):
        fail(errors, "body_battery_sleep_double_counted")

    if integrity.get("main_sleep_confirmed") is True:
        main_minutes = number(integrity.get("main_sleep_minutes"))
        current = recovery.get("current", {}) if isinstance(recovery, dict) else {}
        current_hours = number(current.get("sleep_hours")) if isinstance(current, dict) else None
        if main_minutes is not None and current_hours is not None:
            if abs(current_hours * 60 - main_minutes) > 3:
                fail(
                    errors,
                    "confirmed_sleep_duration_mismatch",
                    f"{current_hours * 60:.1f}_vs_{main_minutes:.1f}",
                )


def test_actual_only(activities, feedback, crossfit, errors, warnings):
    actual = activity_ids(activities)
    manual = feedback_ids(feedback)

    orphan_feedback = sorted(manual - actual)
    if orphan_feedback:
        fail(errors, "manual_feedback_without_actual_activity", ",".join(orphan_feedback[:8]))

    for row in crossfit.get("activities", []) if isinstance(crossfit, dict) else []:
        if not isinstance(row, dict):
            continue
        aid = row.get("activity_id")
        manual_match = row.get("manual_match")
        if manual_match and (not aid or str(aid) not in actual):
            fail(errors, "crossfit_manual_row_without_actual_activity", aid or "missing_id")
        if str(manual_match or "").lower() in {"planned", "planificado", "previsto"}:
            fail(errors, "planned_row_used_as_performed", aid or "missing_id")
        for block in row.get("manual_blocks", []) or []:
            if not isinstance(block, dict):
                continue
            status = str(block.get("status") or "").strip().upper()
            if status in {"PREVISTO", "PLANNED", "PLANIFICADO"}:
                fail(errors, "planned_block_used_as_performed", aid or "missing_id")


def test_rpe_consistency(advanced, feedback, errors, warnings):
    rpe = advanced.get("rpe_feedback", {}) if isinstance(advanced, dict) else {}
    if not isinstance(rpe, dict):
        warn(warnings, "advanced_rpe_feedback_missing")
        return

    feedback_n = int(number(rpe.get("feedback_activities")) or 0)
    matched_n = int(number(rpe.get("matched_activities")) or 0)
    used_n = int(number(rpe.get("used_as_primary_rpe")) or 0)

    if used_n > matched_n or matched_n > feedback_n:
        fail(
            errors,
            "rpe_count_invariant_broken",
            f"used={used_n},matched={matched_n},feedback={feedback_n}",
        )

    remote_adv = int(number(rpe.get("remote_rows_loaded")) or 0)
    remote_feedback = int(number(feedback.get("remote_rows_loaded")) or 0)
    if remote_adv and remote_feedback and remote_adv != remote_feedback:
        fail(
            errors,
            "rpe_remote_row_count_mismatch",
            f"advanced={remote_adv},feedback={remote_feedback}",
        )

    if rpe.get("remote_fetch_error"):
        warn(warnings, "rpe_remote_fetch_error", str(rpe.get("remote_fetch_error"))[:120])


def test_load_unit_separation(advanced, crossfit, errors, warnings):
    rows = advanced.get("activity_analysis", []) if isinstance(advanced, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        aid = row.get("activity_id") or "unknown"
        if not isinstance(row.get("internal_load"), dict):
            fail(errors, "advanced_internal_load_missing", aid)
        if not isinstance(row.get("work_output_proxies"), dict):
            fail(errors, "advanced_work_output_missing", aid)
        for forbidden in ("combined_load", "total_combined_load", "all_load_units_sum"):
            if forbidden in row:
                fail(errors, "mixed_units_field_present", f"{aid}:{forbidden}")

    for row in crossfit.get("activities", []) if isinstance(crossfit, dict) else []:
        if not isinstance(row, dict):
            continue
        aid = row.get("activity_id") or "unknown"
        if "external_work" in row and not isinstance(row.get("external_work"), dict):
            fail(errors, "crossfit_external_work_not_object", aid)
        if "internal_load_not_additive" in row and not isinstance(
            row.get("internal_load_not_additive"), dict
        ):
            fail(errors, "crossfit_internal_load_not_object", aid)


def test_partial_day(heart, advanced, quality, errors, warnings):
    days = heart.get("days", {}) if isinstance(heart, dict) else {}
    if not isinstance(days, dict) or not days:
        warn(warnings, "heart_days_missing")
        return
    latest_day = sorted(days)[-1]
    latest = days.get(latest_day, {})
    if not isinstance(latest, dict) or latest.get("partial_day") is not True:
        return

    trends = advanced.get("robust_trends", {}) if isinstance(advanced, dict) else {}
    for window in ("3d", "7d", "28d"):
        metric = (
            trends.get(window, {})
            .get("metrics", {})
            .get("daytime_hr", {})
            if isinstance(trends, dict)
            else {}
        )
        excluded = int(number(metric.get("partial_days_excluded")) or 0)
        if excluded < 1:
            fail(errors, "partial_day_not_excluded_from_daytime_trend", window)

    today = quality.get("today", {}) if isinstance(quality, dict) else {}
    if isinstance(today, dict) and today.get("heart_rate_partial_day") is not True:
        fail(errors, "partial_day_quality_flag_lost", latest_day)


def test_fused_convergence(advanced, recovery, errors, warnings):
    policy = advanced.get("recovery_baseline_policy", {}) if isinstance(advanced, dict) else {}
    if not isinstance(policy, dict) or policy.get("version") not in {"2.4.0", "2.4.2"}:
        return

    alert = advanced.get("convergence_alert", {})
    if not isinstance(alert, dict):
        fail(errors, "convergence_alert_missing")
        return

    if alert.get("baseline_source") != "fused_recovery_history_v2.4":
        fail(errors, "convergence_not_using_fused_history")

    baseline_metrics = alert.get("baseline_metrics", {})
    canonical = recovery.get("baseline_28d", {}) if isinstance(recovery, dict) else {}
    mapping = {
        "hrv_ms": "hrv_ms",
        "sleep_hours": "sleep_hours",
        "sleep_score": "sleep_score",
        "resting_hr": "resting_hr",
        "night_hr": "night_hr",
    }
    for alert_key, canonical_key in mapping.items():
        a_n = (
            baseline_metrics.get(alert_key, {}).get("n")
            if isinstance(baseline_metrics, dict)
            else None
        )
        c_n = (
            canonical.get(canonical_key, {}).get("n")
            if isinstance(canonical, dict)
            else None
        )
        if isinstance(a_n, (int, float)) and isinstance(c_n, (int, float)) and int(a_n) != int(c_n):
            fail(errors, "fused_convergence_n_mismatch", f"{alert_key}:{a_n}!={c_n}")



def test_domain_convergence(advanced, errors, warnings):
    policy = advanced.get("recovery_baseline_policy", {}) if isinstance(advanced, dict) else {}
    if not isinstance(policy, dict) or policy.get("version") != "2.4.2":
        return

    alert = advanced.get("convergence_alert", {})
    if not isinstance(alert, dict):
        fail(errors, "domain_convergence_alert_missing")
        return

    if alert.get("aggregation_version") != "domain_convergence_v2.4.2":
        fail(errors, "domain_convergence_version_missing")

    if policy.get("convergence_aggregation") != "independent_domains":
        fail(errors, "domain_convergence_policy_missing")

    if policy.get("thresholds_changed") is not False:
        fail(errors, "domain_convergence_thresholds_must_be_unchanged")

    if policy.get("scoring_changed") is not False:
        fail(errors, "domain_convergence_scoring_must_be_unchanged")

    from convergence_domains_v242 import (
        severity_from_domains,
        signal_domain,
        signal_is_strong,
    )

    signals = [x for x in alert.get("signals", []) or [] if isinstance(x, dict)]
    if alert.get("signal_count") != len(signals):
        fail(
            errors,
            "domain_convergence_raw_signal_count_mismatch",
            f"{alert.get('signal_count')}!={len(signals)}",
        )

    expected_domains = sorted({signal_domain(x) for x in signals})
    active_domains = sorted(alert.get("active_domains", []) or [])
    if active_domains != expected_domains:
        fail(
            errors,
            "domain_convergence_active_domains_mismatch",
            f"{active_domains}!={expected_domains}",
        )

    if alert.get("domain_count") != len(expected_domains):
        fail(
            errors,
            "domain_convergence_domain_count_mismatch",
            f"{alert.get('domain_count')}!={len(expected_domains)}",
        )

    expected_severity = severity_from_domains(
        len(expected_domains),
        any(signal_is_strong(x) for x in signals),
    )
    if alert.get("severity") != expected_severity:
        fail(
            errors,
            "domain_convergence_severity_mismatch",
            f"{alert.get('severity')}!={expected_severity}",
        )

    sleep_signals = {
        x.get("signal")
        for x in signals
        if x.get("signal") in {"sleep_hours_low", "sleep_score_low"}
    }
    if len(sleep_signals) == 2:
        if not all(
            x.get("domain") == "sleep"
            for x in signals
            if x.get("signal") in sleep_signals
        ):
            fail(errors, "sleep_metrics_not_grouped")
        sleep_summary = (alert.get("domain_summary") or {}).get("sleep", {})
        if sleep_summary.get("signal_count") != 2:
            fail(errors, "sleep_domain_double_count_guard_missing")

    cardio_signals = {
        x.get("signal")
        for x in signals
        if x.get("signal") in {"resting_hr_high", "night_hr_high"}
    }
    if len(cardio_signals) == 2:
        if not all(
            x.get("domain") == "cardiovascular"
            for x in signals
            if x.get("signal") in cardio_signals
        ):
            fail(errors, "cardiovascular_metrics_not_grouped")

def test_cycle_snapshots(cycles, errors, warnings):
    if not isinstance(cycles, dict):
        return
    if int(number(cycles.get("schema_version")) or 0) < 2:
        return

    rows = cycles.get("cycles", [])
    if not isinstance(rows, list):
        fail(errors, "report_cycles_not_list")
        return

    for row in rows:
        if not isinstance(row, dict):
            continue
        snapshot = row.get("snapshot")
        digest = row.get("snapshot_sha256")
        if not isinstance(snapshot, dict):
            fail(errors, "v2_cycle_missing_snapshot", row.get("cycle_id"))
            continue
        if snapshot.get("snapshot_version") != "2.3.4":
            fail(errors, "bad_snapshot_version", row.get("cycle_id"))
        encoded = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        actual = hashlib.sha256(encoded).hexdigest()
        if digest != actual:
            fail(errors, "snapshot_hash_mismatch", row.get("cycle_id"))
        cycle_id = str(row.get("cycle_id") or "")
        if cycle_id[:10] and snapshot.get("date") != cycle_id[:10]:
            fail(errors, "snapshot_date_mismatch", cycle_id)
        if row.get("source_generated_at") != snapshot.get("source_generated_at"):
            fail(errors, "snapshot_provenance_mismatch", cycle_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("advanced", "crossfit", "manual"), default="manual")
    args = parser.parse_args()

    errors = []
    warnings = []

    activities = load("activities.json", [])
    feedback = load("training_feedback.json", {})
    advanced = load("advanced_analytics.json", {})
    recovery = load("recovery_assessment.json", {})
    crossfit = load("crossfit_insights.json", {})
    heart = load("garmin_heart_rate.json", {})
    quality = load("data_quality.json", {})
    cycles = load("report_cycles.json", {})

    test_sleep_integrity(recovery, errors, warnings)
    test_actual_only(activities, feedback, crossfit, errors, warnings)
    test_rpe_consistency(advanced, feedback, errors, warnings)
    test_load_unit_separation(advanced, crossfit, errors, warnings)
    test_partial_day(heart, advanced, quality, errors, warnings)
    test_fused_convergence(advanced, recovery, errors, warnings)
    test_cycle_snapshots(cycles, errors, warnings)

    result = {
        "version": "2.4.2",
        "stage": args.stage,
        "status": "error" if errors else "ok",
        "errors": errors,
        "warnings": warnings,
        "checks": [
            "confirmed_sleep_not_double_counted",
            "manual_feedback_maps_to_actual_activity",
            "rpe_count_consistency",
            "load_units_kept_separate",
            "partial_day_excluded_from_daytime_trends",
            "fused_convergence_history",
            "independent_domain_convergence",
            "historical_cycle_snapshot_hash",
        ],
    }
    print(json.dumps(result, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
