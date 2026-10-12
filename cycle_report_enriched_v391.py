#!/usr/bin/env python3
"""V3.9.1.1: opt-in, snapshot-verified enrichment; legacy publisher untouched."""
from cycle_snapshot_report_v38 import build
from cycle_report_compat_v386 import render as render_legacy
from report_interpretation_v391 import enrich


def render(ledger, cycle_id):
    """Return enriched Markdown and the original completeness classification.

    Both renderers verify the snapshot SHA and provenance. No live data access.
    """
    report, completeness = render_legacy(ledger, cycle_id)
    certified = build(ledger, cycle_id)
    return enrich(report, certified['data']), completeness
