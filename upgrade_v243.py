#!/usr/bin/env python3
'''One-shot maintenance upgrade for Garmin Recovery V2.4.3.

Fixes safe schema-1 -> schema-2 ledger migration and activates the existing
V2.4.2 independent-domain regression. No physiological scoring changes.
'''
from pathlib import Path

ROOT = Path(".")
HELPER = '\ndef _mark_legacy_cycles(items):\n    """Mark pre-schema-2 rows without inventing unavailable historical snapshots."""\n    out = []\n    for raw in items:\n        if not isinstance(raw, dict):\n            out.append(raw)\n            continue\n        row = dict(raw)\n        if \'entry_schema_version\' not in row:\n            if isinstance(row.get(\'snapshot\'), dict) and isinstance(row.get(\'snapshot_sha256\'), str):\n                row[\'entry_schema_version\'] = 2\n            else:\n                row[\'entry_schema_version\'] = 1\n                row[\'legacy_without_snapshot\'] = True\n                row[\'snapshot_status\'] = \'legacy_unavailable\'\n                row[\'legacy_note\'] = (\n                    \'Created before report_cycles schema 2; no retrospective \'\n                    \'snapshot was fabricated.\'\n                )\n        out.append(row)\n    return out\n\n\ndef _write_ledger(path, items):\n    items = sorted(\n        items,\n        key=lambda x: x.get(\'slot_at\', \'\') if isinstance(x, dict) else \'\'\n    )[-120:]\n    path.write_text(json.dumps({\n        \'schema_version\': 2,\n        \'ledger_version\': \'2.3.4\',\n        \'purpose\': \'Historical data-readiness ledger (not an outgoing notification receipt)\',\n        \'cycles\': items,\n        \'count\': len(items)\n    }, ensure_ascii=False, indent=2) + \'\\n\', encoding=\'utf-8\')\n'
OLD_HEAD = 'def append_ready_cycle(cert, path=Path(\'report_cycles.json\'), max_entries=120):\n    """Persist completed-data cycles. A readiness ledger is NOT a delivery receipt."""\n    try:\n        data = json.loads(path.read_text(encoding=\'utf-8\'))\n        items = data.get(\'cycles\', []) if isinstance(data, dict) else []\n        if not isinstance(items, list):\n            items = []\n    except (OSError, ValueError):\n        items = []\n    cycle_id = cert[\'cycle_id\']\n    if any(isinstance(x, dict) and x.get(\'cycle_id\') == cycle_id for x in items):\n        return False\n    snapshot, snapshot_sha256 = compact_cycle_snapshot(cert)\n    items.append({\n        \'cycle_id\': cycle_id, \'ready_at\': cert[\'verified_at\'],'
NEW_HEAD = 'def append_ready_cycle(cert, path=Path(\'report_cycles.json\'), max_entries=120):\n    """Persist completed-data cycles. A readiness ledger is NOT a delivery receipt."""\n    source_schema_version = 1\n    try:\n        data = json.loads(path.read_text(encoding=\'utf-8\'))\n        source_schema_version = (\n            int(data.get(\'schema_version\') or 1)\n            if isinstance(data, dict)\n            else 1\n        )\n        items = data.get(\'cycles\', []) if isinstance(data, dict) else []\n        if not isinstance(items, list):\n            items = []\n    except (OSError, ValueError, TypeError):\n        items = []\n\n    if source_schema_version < 2:\n        items = _mark_legacy_cycles(items)\n\n    cycle_id = cert[\'cycle_id\']\n    if any(isinstance(x, dict) and x.get(\'cycle_id\') == cycle_id for x in items):\n        if source_schema_version < 2:\n            _write_ledger(path, items)\n        return False\n\n    snapshot, snapshot_sha256 = compact_cycle_snapshot(cert)\n    items.append({\n        \'entry_schema_version\': 2,\n        \'cycle_id\': cycle_id, \'ready_at\': cert[\'verified_at\'],'
OLD_TAIL = "    items = sorted(items, key=lambda x: x.get('slot_at', ''))[-max_entries:]\n    path.write_text(json.dumps({\n        'schema_version': 2,\n        'ledger_version': '2.3.4',\n        'purpose': 'Historical data-readiness ledger (not an outgoing notification receipt)',\n        'cycles': items, 'count': len(items)\n    }, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    return True"
NEW_TAIL = "    items = sorted(\n        items,\n        key=lambda x: x.get('slot_at', '') if isinstance(x, dict) else ''\n    )[-max_entries:]\n    _write_ledger(path, items)\n    return True"
NEW_CYCLE_TEST = 'def test_cycle_snapshots(cycles, errors, warnings):\n    if not isinstance(cycles, dict):\n        return\n\n    ledger_schema = int(number(cycles.get("schema_version")) or 0)\n    if ledger_schema < 2:\n        return\n\n    rows = cycles.get("cycles", [])\n    if not isinstance(rows, list):\n        fail(errors, "report_cycles_not_list")\n        return\n\n    for row in rows:\n        if not isinstance(row, dict):\n            fail(errors, "report_cycle_entry_not_object")\n            continue\n\n        cycle_id = str(row.get("cycle_id") or "")\n        entry_schema = int(number(row.get("entry_schema_version")) or 0)\n\n        if entry_schema < 2:\n            explicitly_legacy = (\n                row.get("legacy_without_snapshot") is True\n                and row.get("snapshot_status") == "legacy_unavailable"\n            )\n            if not explicitly_legacy:\n                fail(errors, "schema2_unmarked_legacy_cycle", cycle_id or "unknown")\n                continue\n            if isinstance(row.get("snapshot"), dict) or row.get("snapshot_sha256"):\n                fail(errors, "legacy_cycle_has_conflicting_snapshot", cycle_id or "unknown")\n            continue\n\n        snapshot = row.get("snapshot")\n        digest = row.get("snapshot_sha256")\n        if not isinstance(snapshot, dict):\n            fail(errors, "v2_cycle_missing_snapshot", cycle_id)\n            continue\n        if snapshot.get("snapshot_version") != "2.3.4":\n            fail(errors, "bad_snapshot_version", cycle_id)\n\n        encoded = json.dumps(\n            snapshot,\n            ensure_ascii=False,\n            sort_keys=True,\n            separators=(",", ":"),\n        ).encode("utf-8")\n        actual = hashlib.sha256(encoded).hexdigest()\n\n        if digest != actual:\n            fail(errors, "snapshot_hash_mismatch", cycle_id)\n        if cycle_id[:10] and snapshot.get("date") != cycle_id[:10]:\n            fail(errors, "snapshot_date_mismatch", cycle_id)\n        if row.get("source_generated_at") != snapshot.get("source_generated_at"):\n            fail(errors, "snapshot_provenance_mismatch", cycle_id)\n'
OLD_CALLS = '    test_partial_day(heart, advanced, quality, errors, warnings)\n    test_fused_convergence(advanced, recovery, errors, warnings)\n    test_cycle_snapshots(cycles, errors, warnings)'
NEW_CALLS = '    test_partial_day(heart, advanced, quality, errors, warnings)\n    test_fused_convergence(advanced, recovery, errors, warnings)\n    test_domain_convergence(advanced, errors, warnings)\n    test_cycle_snapshots(cycles, errors, warnings)'


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"V2.4.3 patch anchor missing: {label}")
    return text.replace(old, new, 1)


def patch_gate():
    path = ROOT / "report_delivery_gate.py"
    src = path.read_text(encoding="utf-8")

    anchor = "\ndef append_ready_cycle(cert, path=Path('report_cycles.json'), max_entries=120):"
    if "def _mark_legacy_cycles(" not in src:
        if anchor not in src:
            raise RuntimeError("V2.4.3 gate helper anchor missing")
        src = src.replace(anchor, "\n" + HELPER + anchor, 1)

    if "'entry_schema_version': 2," not in src:
        src = replace_once(src, OLD_HEAD, NEW_HEAD, "append_ready_cycle migration")

    if OLD_TAIL in src:
        src = src.replace(OLD_TAIL, NEW_TAIL, 1)

    path.write_text(src, encoding="utf-8")


def patch_regressions():
    path = ROOT / "pipeline_regression_tests.py"
    src = path.read_text(encoding="utf-8")

    src = src.replace(
        '"""Regression invariants for Garmin Recovery V2.4.2.',
        '"""Regression invariants for Garmin Recovery V2.4.3.',
        1,
    )

    start = src.find("def test_cycle_snapshots(cycles, errors, warnings):")
    end = src.find("\ndef main():", start)
    if start < 0 or end < 0:
        raise RuntimeError("V2.4.3 cycle regression function anchor missing")

    src = src[:start] + NEW_CYCLE_TEST + src[end:]

    if "    test_domain_convergence(advanced, errors, warnings)\n" not in src:
        src = replace_once(src, OLD_CALLS, NEW_CALLS, "activate domain regression")

    src = src.replace(
        '        "version": "2.4.2",',
        '        "version": "2.4.3",',
        1,
    )

    if '"legacy_schema1_cycle_migration"' not in src:
        src = replace_once(
            src,
            '            "independent_domain_convergence",\n            "historical_cycle_snapshot_hash",',
            '            "independent_domain_convergence",\n            "legacy_schema1_cycle_migration",\n            "historical_cycle_snapshot_hash",',
            "regression check list",
        )

    path.write_text(src, encoding="utf-8")


def main():
    patch_gate()
    patch_regressions()
    print("V2.4.3 applied: legacy ledger migration fixed; domain regression activated.")


if __name__ == "__main__":
    main()
