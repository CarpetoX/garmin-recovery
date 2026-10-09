#!/usr/bin/env python3
"""One-shot migration: Garmin Recovery V2.3.3 -> V2.3.4 robustness update.

Changes only robustness/provenance. It does NOT change recovery score thresholds
or readiness weighting.
"""
from pathlib import Path
import re

ROOT = Path(".")
changed = []

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")
    changed.append(path)

def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"V2.3.4 patch anchor missing: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# 1) report_delivery_gate.py: immutable compact snapshot per certified cycle.
# ---------------------------------------------------------------------------
p = "report_delivery_gate.py"
s = read(p)
s = replace_once(
    s,
    '"""Garmin Recovery V2.3.3: certificate for a completed cross-workflow report cycle.',
    '"""Garmin Recovery V2.3.4: certificate for a completed cross-workflow report cycle.',
    "gate doc version",
)
s = replace_once(s, "import json\nimport os", "import hashlib\nimport json\nimport os", "gate hashlib import")
s = s.replace("'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.2'", "'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.4'")
s = s.replace("'gate_version': '2.3.3'", "'gate_version': '2.3.4'")

anchor = "\n\n\ndef append_ready_cycle(cert, path=Path('report_cycles.json'), max_entries=120):"
if anchor not in s:
    raise RuntimeError("V2.3.4 patch anchor missing: append_ready_cycle")

snapshot_code = r