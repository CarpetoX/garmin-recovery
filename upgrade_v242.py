#!/usr/bin/env python3
'''One-shot Garmin Recovery V2.4.2 upgrade.

Changes convergence severity aggregation from raw metric count to independent
physiological-domain count. Metric thresholds, Recovery Score, Hybrid Readiness,
weights and physiological source selection are unchanged.
'''
from pathlib import Path

ROOT = Path(".")
DOMAIN_MODULE = '#!/usr/bin/env python3\n"""Independent-domain convergence aggregation for Garmin Recovery V2.4.2.\n\nThis layer does not change physiological signal thresholds. It only prevents\ncorrelated metrics from the same domain from being counted as independent\nevidence when assigning convergence severity.\n"""\n\nSIGNAL_DOMAINS = {\n    "sleep_hours_low": "sleep",\n    "sleep_score_low": "sleep",\n    "resting_hr_high": "cardiovascular",\n    "night_hr_high": "cardiovascular",\n    "hrv_low": "hrv",\n    "stress_high": "stress",\n    "body_battery_low": "stress",\n    "recovery_time_high": "load",\n}\n\n\ndef _number(value):\n    if isinstance(value, bool) or not isinstance(value, (int, float)):\n        return None\n    return float(value)\n\n\ndef signal_domain(signal):\n    name = str((signal or {}).get("signal") or "unknown")\n    return SIGNAL_DOMAINS.get(name, f"other:{name}")\n\n\ndef signal_is_strong(signal):\n    if not isinstance(signal, dict):\n        return False\n\n    z = _number(signal.get("robust_z"))\n    if z is not None and abs(z) >= 1.5:\n        return True\n\n    if signal.get("signal") == "recovery_time_high":\n        hours = _number(signal.get("value_hours"))\n        if hours is not None and hours >= 36:\n            return True\n\n    return False\n\n\ndef severity_from_domains(domain_count, any_strong):\n    """Mirror the prior convergence rule, but over independent domains."""\n    if domain_count >= 4 or (domain_count >= 3 and any_strong):\n        return "red"\n    if domain_count >= 3:\n        return "yellow"\n    return "none"\n\n\ndef apply_domain_convergence(alert):\n    alert = dict(alert) if isinstance(alert, dict) else {}\n\n    signals = []\n    domain_rows = {}\n\n    for raw in alert.get("signals", []) or []:\n        if not isinstance(raw, dict):\n            continue\n\n        item = dict(raw)\n        domain = signal_domain(item)\n        item["domain"] = domain\n        strong = signal_is_strong(item)\n        signals.append(item)\n\n        row = domain_rows.setdefault(\n            domain,\n            {\n                "signal_count": 0,\n                "signals": [],\n                "strong": False,\n                "strongest_abs_robust_z": None,\n            },\n        )\n        row["signal_count"] += 1\n        row["signals"].append(item.get("signal"))\n        row["strong"] = bool(row["strong"] or strong)\n\n        z = _number(item.get("robust_z"))\n        if z is not None:\n            magnitude = round(abs(z), 2)\n            current = row["strongest_abs_robust_z"]\n            if current is None or magnitude > current:\n                row["strongest_abs_robust_z"] = magnitude\n\n    active_domains = sorted(domain_rows)\n    any_strong = any(row.get("strong") for row in domain_rows.values())\n    domain_count = len(active_domains)\n\n    alert["signals"] = signals\n    alert["signal_count"] = len(signals)\n    alert["raw_metric_signal_count"] = len(signals)\n    alert["domain_count"] = domain_count\n    alert["active_domains"] = active_domains\n    alert["domain_summary"] = {\n        domain: domain_rows[domain]\n        for domain in active_domains\n    }\n    alert["severity"] = severity_from_domains(domain_count, any_strong)\n    alert["aggregation_version"] = "domain_convergence_v2.4.2"\n    alert["aggregation_rule"] = (\n        "Severity is based on independent physiological domains, not raw metric count. "\n        "Sleep duration + sleep score count once; resting HR + night HR count once; "\n        "stress + Body Battery count once. Signal thresholds are unchanged."\n    )\n\n    return alert\n\n\ndef _self_test():\n    case = {\n        "severity": "red",\n        "signals": [\n            {"signal": "sleep_hours_low", "robust_z": -1.7},\n            {"signal": "sleep_score_low", "robust_z": -2.1},\n            {"signal": "resting_hr_high", "robust_z": 1.3},\n        ],\n    }\n    out = apply_domain_convergence(case)\n    assert out["signal_count"] == 3\n    assert out["domain_count"] == 2\n    assert out["active_domains"] == ["cardiovascular", "sleep"]\n    assert out["severity"] == "none"\n    assert out["domain_summary"]["sleep"]["signal_count"] == 2\n\n    case = {\n        "signals": [\n            {"signal": "sleep_hours_low", "robust_z": -1.2},\n            {"signal": "resting_hr_high", "robust_z": 1.1},\n            {"signal": "hrv_low", "robust_z": -1.1},\n        ]\n    }\n    out = apply_domain_convergence(case)\n    assert out["domain_count"] == 3\n    assert out["severity"] == "yellow"\n\n    case["signals"][2]["robust_z"] = -1.6\n    out = apply_domain_convergence(case)\n    assert out["severity"] == "red"\n\n    case = {\n        "signals": [\n            {"signal": "stress_high", "robust_z": 1.7},\n            {"signal": "body_battery_low", "robust_z": -1.8},\n        ]\n    }\n    out = apply_domain_convergence(case)\n    assert out["domain_count"] == 1\n    assert out["active_domains"] == ["stress"]\n\n    print("convergence_domains_v242 self-test: OK")\n\n\nif __name__ == "__main__":\n    _self_test()\n'
OLD_APPLY = "    fused_alert = fused_convergence_alert(records, now, adv.get('convergence_alert'))\n    adv['convergence_alert'] = fused_alert"
NEW_APPLY = "    fused_alert = fused_convergence_alert(records, now, adv.get('convergence_alert'))\n    from convergence_domains_v242 import apply_domain_convergence\n    fused_alert = apply_domain_convergence(fused_alert)\n    adv['convergence_alert'] = fused_alert"
OLD_POLICY = "        'version': '2.4.0',\n        'canonical_for_recovery_reports': 'recovery_assessment.baseline_28d',\n        'convergence_history': 'fused_recovery_history_v2.4',\n        'source': 'fused Garmin timelines + Intervals fallback',\n        'excludes_current_day': True,\n        'scoring_changed': False,\n        'thresholds_changed': False,\n        'note': ('Advanced convergence_alert now reuses fused recovery history for '\n                 'HRV, sleep, resting HR and night HR; stress/body battery keep '\n                 'their Advanced Analytics sources. Thresholds and readiness scoring are unchanged.')"
NEW_POLICY = "        'version': '2.4.2',\n        'canonical_for_recovery_reports': 'recovery_assessment.baseline_28d',\n        'convergence_history': 'fused_recovery_history_v2.4',\n        'convergence_aggregation': 'independent_domains',\n        'aggregation_version': 'domain_convergence_v2.4.2',\n        'source': 'fused Garmin timelines + Intervals fallback',\n        'excludes_current_day': True,\n        'scoring_changed': False,\n        'thresholds_changed': False,\n        'aggregation_changed': True,\n        'note': ('Recovery-sensitive signals still use fused history with the same '\n                 'thresholds, but convergence severity is now based on independent '\n                 'domains so correlated metrics are not double-counted. Recovery '\n                 'Score and Hybrid Readiness scoring are unchanged.')"
OLD_VERSION_GATE = '    if not isinstance(policy, dict) or policy.get("version") != "2.4.0":\n        return'
NEW_VERSION_GATE = '    if not isinstance(policy, dict) or policy.get("version") not in {"2.4.0", "2.4.2"}:\n        return'
DOMAIN_TEST = '\ndef test_domain_convergence(advanced, errors, warnings):\n    policy = advanced.get("recovery_baseline_policy", {}) if isinstance(advanced, dict) else {}\n    if not isinstance(policy, dict) or policy.get("version") != "2.4.2":\n        return\n\n    alert = advanced.get("convergence_alert", {})\n    if not isinstance(alert, dict):\n        fail(errors, "domain_convergence_alert_missing")\n        return\n\n    if alert.get("aggregation_version") != "domain_convergence_v2.4.2":\n        fail(errors, "domain_convergence_version_missing")\n\n    if policy.get("convergence_aggregation") != "independent_domains":\n        fail(errors, "domain_convergence_policy_missing")\n\n    if policy.get("thresholds_changed") is not False:\n        fail(errors, "domain_convergence_thresholds_must_be_unchanged")\n\n    if policy.get("scoring_changed") is not False:\n        fail(errors, "domain_convergence_scoring_must_be_unchanged")\n\n    from convergence_domains_v242 import (\n        severity_from_domains,\n        signal_domain,\n        signal_is_strong,\n    )\n\n    signals = [x for x in alert.get("signals", []) or [] if isinstance(x, dict)]\n    if alert.get("signal_count") != len(signals):\n        fail(\n            errors,\n            "domain_convergence_raw_signal_count_mismatch",\n            f"{alert.get(\'signal_count\')}!={len(signals)}",\n        )\n\n    expected_domains = sorted({signal_domain(x) for x in signals})\n    active_domains = sorted(alert.get("active_domains", []) or [])\n    if active_domains != expected_domains:\n        fail(\n            errors,\n            "domain_convergence_active_domains_mismatch",\n            f"{active_domains}!={expected_domains}",\n        )\n\n    if alert.get("domain_count") != len(expected_domains):\n        fail(\n            errors,\n            "domain_convergence_domain_count_mismatch",\n            f"{alert.get(\'domain_count\')}!={len(expected_domains)}",\n        )\n\n    expected_severity = severity_from_domains(\n        len(expected_domains),\n        any(signal_is_strong(x) for x in signals),\n    )\n    if alert.get("severity") != expected_severity:\n        fail(\n            errors,\n            "domain_convergence_severity_mismatch",\n            f"{alert.get(\'severity\')}!={expected_severity}",\n        )\n\n    sleep_signals = {\n        x.get("signal")\n        for x in signals\n        if x.get("signal") in {"sleep_hours_low", "sleep_score_low"}\n    }\n    if len(sleep_signals) == 2:\n        if not all(\n            x.get("domain") == "sleep"\n            for x in signals\n            if x.get("signal") in sleep_signals\n        ):\n            fail(errors, "sleep_metrics_not_grouped")\n        sleep_summary = (alert.get("domain_summary") or {}).get("sleep", {})\n        if sleep_summary.get("signal_count") != 2:\n            fail(errors, "sleep_domain_double_count_guard_missing")\n\n    cardio_signals = {\n        x.get("signal")\n        for x in signals\n        if x.get("signal") in {"resting_hr_high", "night_hr_high"}\n    }\n    if len(cardio_signals) == 2:\n        if not all(\n            x.get("domain") == "cardiovascular"\n            for x in signals\n            if x.get("signal") in cardio_signals\n        ):\n            fail(errors, "cardiovascular_metrics_not_grouped")\n'


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"V2.4.2 patch anchor missing: {label}")
    return text.replace(old, new, 1)


def main():
    (ROOT / "convergence_domains_v242.py").write_text(
        DOMAIN_MODULE,
        encoding="utf-8",
    )

    path = ROOT / "recovery_reliability.py"
    source = path.read_text(encoding="utf-8")

    if "apply_domain_convergence(fused_alert)" not in source:
        source = replace_once(
            source,
            OLD_APPLY,
            NEW_APPLY,
            "domain aggregation call",
        )

    if "'version': '2.4.2'" not in source:
        source = replace_once(
            source,
            OLD_POLICY,
            NEW_POLICY,
            "V2.4.2 baseline/convergence policy",
        )

    path.write_text(source, encoding="utf-8")

    tests_path = ROOT / "pipeline_regression_tests.py"
    tests = tests_path.read_text(encoding="utf-8")

    tests = tests.replace(
        '"""Regression invariants for Garmin Recovery V2.4.',
        '"""Regression invariants for Garmin Recovery V2.4.2.',
        1,
    )

    if OLD_VERSION_GATE in tests:
        tests = tests.replace(
            OLD_VERSION_GATE,
            NEW_VERSION_GATE,
            1,
        )

    marker = "\ndef test_cycle_snapshots(cycles, errors, warnings):"
    if "def test_domain_convergence(" not in tests:
        if marker not in tests:
            raise RuntimeError("V2.4.2 test insertion anchor missing")
        tests = tests.replace(marker, "\n" + DOMAIN_TEST + marker, 1)

    old_call = (
        "    test_fused_convergence(advanced, recovery, errors, warnings)\n"
        "    test_cycle_snapshots(cycles, errors, warnings)"
    )
    new_call = (
        "    test_fused_convergence(advanced, recovery, errors, warnings)\n"
        "    test_domain_convergence(advanced, errors, warnings)\n"
        "    test_cycle_snapshots(cycles, errors, warnings)"
    )
    if "test_domain_convergence(advanced, errors, warnings)" not in tests:
        tests = replace_once(
            tests,
            old_call,
            new_call,
            "domain regression call",
        )

    tests = tests.replace(
        '        "version": "2.4.0",',
        '        "version": "2.4.2",',
        1,
    )

    old_check = (
        '            "fused_convergence_history",\n'
        '            "historical_cycle_snapshot_hash",'
    )
    new_check = (
        '            "fused_convergence_history",\n'
        '            "independent_domain_convergence",\n'
        '            "historical_cycle_snapshot_hash",'
    )
    if "independent_domain_convergence" not in tests:
        tests = replace_once(
            tests,
            old_check,
            new_check,
            "regression check list",
        )

    tests_path.write_text(tests, encoding="utf-8")

    print(
        "V2.4.2 applied: independent-domain convergence + regression guard. "
        "Physiological thresholds and readiness scoring unchanged."
    )


if __name__ == "__main__":
    main()
