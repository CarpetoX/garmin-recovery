#!/usr/bin/env python3
"""Garmin Recovery V2.4.4 traceability upgrade.

Distinguishes GitHub cron, manual workflow_dispatch and Apps Script backup via
repository_dispatch. No physiological scoring, thresholds or recovery logic change.
"""
from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"V2.4.4 patch anchor missing: {label}")
    return text.replace(old, new, 1)


def patch_gate():
    path = Path("report_delivery_gate.py")
    src = path.read_text(encoding="utf-8")
    old = "sync = parent_before(sync_runs, heart, {'schedule', 'workflow_dispatch'})"
    new = "sync = parent_before(sync_runs, heart, {'schedule', 'workflow_dispatch', 'repository_dispatch'})"
    if new not in src:
        src = replace_once(src, old, new, "report gate sync events")
    src = src.replace(
        "'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.4',",
        "'User-Agent': 'Garmin-Report-Delivery-Gate/2.4.4',",
        1,
    )
    path.write_text(src, encoding="utf-8")


def patch_monitor():
    path = Path("monitor_v231.py")
    src = path.read_text(encoding="utf-8")

    src = src.replace(
        '"""Garmin V2.3.4 monitor: separate cron failures, recovered syncs and real gaps.',
        '"""Garmin V2.4.4 monitor: distinguish cron, Apps Script backup and manual syncs.',
        1,
    )

    old = """    scheduled = []
    dispatched = []"""
    new = """    scheduled = []
    apps_dispatched = []
    manual_dispatched = []"""
    if "apps_dispatched = []" not in src:
        src = replace_once(src, old, new, "monitor dispatch buckets")

    old = """        if run.get('event') == 'schedule':
            scheduled.append(started)
        elif run.get('event') == 'workflow_dispatch':
            dispatched.append(started)"""
    new = """        if run.get('event') == 'schedule':
            scheduled.append(started)
        elif run.get('event') == 'repository_dispatch':
            apps_dispatched.append(started)
        elif run.get('event') == 'workflow_dispatch':
            manual_dispatched.append(started)"""
    if "repository_dispatch" not in src[src.find("def audit_slots"):src.find("def gate_status")]:
        src = replace_once(src, old, new, "monitor event classification")

    old = """    matched, recovered, uncovered = [], [], []
    for slot in slots:"""
    new = """    matched, recovered, uncovered = [], [], []
    recovered_apps, recovered_manual = [], []
    for slot in slots:"""
    if "recovered_apps, recovered_manual" not in src:
        src = replace_once(src, old, new, "monitor recovered buckets")

    old = """        if any(lower <= t <= upper for t in scheduled):
            matched.append(slot.isoformat())
        elif any(lower <= t <= upper for t in dispatched):
            recovered.append(slot.isoformat())
        else:
            uncovered.append(slot.isoformat())"""
    new = """        if any(lower <= t <= upper for t in scheduled):
            matched.append(slot.isoformat())
        elif any(lower <= t <= upper for t in apps_dispatched):
            recovered.append(slot.isoformat())
            recovered_apps.append(slot.isoformat())
        elif any(lower <= t <= upper for t in manual_dispatched):
            recovered.append(slot.isoformat())
            recovered_manual.append(slot.isoformat())
        else:
            uncovered.append(slot.isoformat())"""
    if "recovered_apps.append" not in src:
        src = replace_once(src, old, new, "monitor recovered classification")

    old = """        'recovered_count': len(recovered), 'recovered': recovered,
        'cron_missed': recovered + uncovered, 'uncovered': uncovered,
        'missed': uncovered,  # compatibility with V2.3.1 consumers
        'manual_runs_counted_as_schedule': False,
        'dispatch_origin_verified': False,"""
    new = """        'recovered_count': len(recovered), 'recovered': recovered,
        'recovered_by_apps_script': recovered_apps,
        'recovered_by_manual': recovered_manual,
        'cron_missed': recovered + uncovered, 'uncovered': uncovered,
        'missed': uncovered,  # compatibility with V2.3.1 consumers
        'manual_runs_counted_as_schedule': False,
        'dispatch_origin_verified': True if recovered else None,"""
    if "'recovered_by_apps_script'" not in src:
        src = replace_once(src, old, new, "monitor origin fields")

    src = src.replace(
        "'schedule_version': 'three_syncs_v234',",
        "'schedule_version': 'three_syncs_v244',",
        1,
    )
    src = src.replace(
        "        'note': ('Recovered means a successful dispatch was found, but it is not '\n"
        "                 'provably an Apps Script dispatch rather than a human dispatch.'),",
        "        'note': ('repository_dispatch=Apps Script backup; '\n"
        "                 'workflow_dispatch=manual; schedule=GitHub cron.'),",
        1,
    )

    old = """        alerts.append({'severity': 'info', 'code': 'cron_missed_dispatch_recovered',
                       'slots': slots.get('recovered'), 'dispatch_origin': 'unverified'})"""
    new = """        dispatch_origin = ('apps_script_backup' if slots.get('recovered_by_apps_script')
                           else 'manual' if slots.get('recovered_by_manual')
                           else 'unknown')
        alerts.append({'severity': 'info', 'code': 'cron_missed_dispatch_recovered',
                       'slots': slots.get('recovered'),
                       'dispatch_origin': dispatch_origin,
                       'dispatch_origin_verified': slots.get('dispatch_origin_verified')})"""
    if "dispatch_origin_verified': slots.get" not in src:
        src = replace_once(src, old, new, "monitor alert origin")

    # Extend self-test so repository_dispatch is explicitly covered.
    marker = "    scheduled = dict(manual, event='schedule')\n"
    addition = "    apps = dict(manual, event='repository_dispatch')\n    scheduled = dict(manual, event='schedule')\n"
    if "apps = dict(manual, event='repository_dispatch')" not in src:
        src = replace_once(src, marker, addition, "monitor self-test apps fixture")

    marker = """    a = audit_slots(now, [manual], lookback_hours=12)
    assert a['due'] == 1 and a['matched'] == 0 and a['recovered_count'] == 1 and a['state'] == 'recovered', a
    b = audit_slots(now, [scheduled], lookback_hours=12)"""
    addition = """    a = audit_slots(now, [manual], lookback_hours=12)
    assert a['due'] == 1 and a['matched'] == 0 and a['recovered_count'] == 1 and a['state'] == 'recovered', a
    assert a['recovered_by_manual'] and not a['recovered_by_apps_script'], a
    app = audit_slots(now, [apps], lookback_hours=12)
    assert app['state'] == 'recovered' and app['recovered_by_apps_script'], app
    assert app['dispatch_origin_verified'] is True, app
    b = audit_slots(now, [scheduled], lookback_hours=12)"""
    if "assert app['dispatch_origin_verified'] is True" not in src:
        src = replace_once(src, marker, addition, "monitor self-test apps assertion")

    src = src.replace(
        "print('OK: 6 tests of V2.3.4 schedule distinction')",
        "print('OK: V2.4.4 schedule/manual/Apps Script distinction')",
        1,
    )

    path.write_text(src, encoding="utf-8")


def main():
    patch_gate()
    patch_monitor()
    print("V2.4.4 applied: explicit Apps Script backup provenance enabled.")


if __name__ == "__main__":
    main()
