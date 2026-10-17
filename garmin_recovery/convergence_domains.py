#!/usr/bin/env python3
"""Independent-domain convergence aggregation for Garmin Recovery V2.4.2.

This layer does not change physiological signal thresholds. It only prevents
correlated metrics from the same domain from being counted as independent
evidence when assigning convergence severity.
"""

SIGNAL_DOMAINS = {
    "sleep_hours_low": "sleep",
    "sleep_score_low": "sleep",
    "resting_hr_high": "cardiovascular",
    "night_hr_high": "cardiovascular",
    "hrv_low": "hrv",
    "stress_high": "stress",
    "body_battery_low": "stress",
    "recovery_time_high": "load",
}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def signal_domain(signal):
    name = str((signal or {}).get("signal") or "unknown")
    return SIGNAL_DOMAINS.get(name, f"other:{name}")


def signal_is_strong(signal):
    if not isinstance(signal, dict):
        return False

    z = _number(signal.get("robust_z"))
    if z is not None and abs(z) >= 1.5:
        return True

    if signal.get("signal") == "recovery_time_high":
        hours = _number(signal.get("value_hours"))
        if hours is not None and hours >= 36:
            return True

    return False


def severity_from_domains(domain_count, any_strong):
    """Mirror the prior convergence rule, but over independent domains."""
    if domain_count >= 4 or (domain_count >= 3 and any_strong):
        return "red"
    if domain_count >= 3:
        return "yellow"
    return "none"


def apply_domain_convergence(alert):
    alert = dict(alert) if isinstance(alert, dict) else {}

    signals = []
    domain_rows = {}

    for raw in alert.get("signals", []) or []:
        if not isinstance(raw, dict):
            continue

        item = dict(raw)
        domain = signal_domain(item)
        item["domain"] = domain
        strong = signal_is_strong(item)
        signals.append(item)

        row = domain_rows.setdefault(
            domain,
            {
                "signal_count": 0,
                "signals": [],
                "strong": False,
                "strongest_abs_robust_z": None,
            },
        )
        row["signal_count"] += 1
        row["signals"].append(item.get("signal"))
        row["strong"] = bool(row["strong"] or strong)

        z = _number(item.get("robust_z"))
        if z is not None:
            magnitude = round(abs(z), 2)
            current = row["strongest_abs_robust_z"]
            if current is None or magnitude > current:
                row["strongest_abs_robust_z"] = magnitude

    active_domains = sorted(domain_rows)
    any_strong = any(row.get("strong") for row in domain_rows.values())
    domain_count = len(active_domains)

    alert["signals"] = signals
    alert["signal_count"] = len(signals)
    alert["raw_metric_signal_count"] = len(signals)
    alert["domain_count"] = domain_count
    alert["active_domains"] = active_domains
    alert["domain_summary"] = {
        domain: domain_rows[domain]
        for domain in active_domains
    }
    alert["severity"] = severity_from_domains(domain_count, any_strong)
    alert["aggregation_version"] = "domain_convergence_v2.4.2"
    alert["aggregation_rule"] = (
        "Severity is based on independent physiological domains, not raw metric count. "
        "Sleep duration + sleep score count once; resting HR + night HR count once; "
        "stress + Body Battery count once. Signal thresholds are unchanged."
    )

    return alert


def _self_test():
    case = {
        "severity": "red",
        "signals": [
            {"signal": "sleep_hours_low", "robust_z": -1.7},
            {"signal": "sleep_score_low", "robust_z": -2.1},
            {"signal": "resting_hr_high", "robust_z": 1.3},
        ],
    }
    out = apply_domain_convergence(case)
    assert out["signal_count"] == 3
    assert out["domain_count"] == 2
    assert out["active_domains"] == ["cardiovascular", "sleep"]
    assert out["severity"] == "none"
    assert out["domain_summary"]["sleep"]["signal_count"] == 2

    case = {
        "signals": [
            {"signal": "sleep_hours_low", "robust_z": -1.2},
            {"signal": "resting_hr_high", "robust_z": 1.1},
            {"signal": "hrv_low", "robust_z": -1.1},
        ]
    }
    out = apply_domain_convergence(case)
    assert out["domain_count"] == 3
    assert out["severity"] == "yellow"

    case["signals"][2]["robust_z"] = -1.6
    out = apply_domain_convergence(case)
    assert out["severity"] == "red"

    case = {
        "signals": [
            {"signal": "stress_high", "robust_z": 1.7},
            {"signal": "body_battery_low", "robust_z": -1.8},
        ]
    }
    out = apply_domain_convergence(case)
    assert out["domain_count"] == 1
    assert out["active_domains"] == ["stress"]

    print("convergence_domains_v242 self-test: OK")


if __name__ == "__main__":
    _self_test()
