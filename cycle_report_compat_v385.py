#!/usr/bin/env python3
"""V3.8.5: historical compatibility without changing snapshots or bypassing SHA256."""
import re
from cycle_snapshot_report_v38 import build, SnapshotError
from cycle_visual_report_v382 import make

SAFE_ID = re.compile(r'\A\d{4}-\d{2}-\d{2}-\d{4}(?:-post-sleep)?\Z', re.ASCII)


def render(ledger, cycle_id):
    if not isinstance(cycle_id, str) or not SAFE_ID.fullmatch(cycle_id):
        raise SnapshotError('Unsafe cycle id')
    cert = build(ledger, cycle_id)  # Mandatory original SHA-256 and provenance validation.
    performance = ((cert['data'].get('crossfit') or {}).get('performance_report') or {})
    chart = performance.get('daily_chart_7d')
    valid_chart = (isinstance(chart, list) and len(chart) == 7 and
                   all(isinstance(p, dict) and isinstance(p.get('date'), str)
                       and '\n' not in p['date'] and '\r' not in p['date'] for p in chart))
    if valid_chart:
        return make(ledger, cycle_id), 'complete'
    # Do not fabricate any missing chart, measurements, or recommendations.
    lines = ['# Garmin Recovery — Informe histórico V3.8.5 (parcial)', '',
             f"**Ciclo:** `{cycle_id}` · **Corte:** `{cert['slot_at']}`",
             f"**SHA-256 verificado:** `{cert['snapshot_sha256']}`", '',
             '**Fuente:** snapshot histórico certificado exclusivamente.', '',
             '## Disponibilidad de datos', '',
             '- Gráfica CrossFit de siete días: **no disponible o formato incompatible**.',
             '- No se inventan valores ni se reconstruye una gráfica ausente.',
             '- Para un informe completo se requiere un snapshot con los datos necesarios.', '',
             '## Limitaciones', '',
             '- Informe parcial; no sustituye al informe completo V3.8.2.',
             '- No implica entrega en ChatGPT ni lectura en tiempo real.', '']
    return '\n'.join(lines), 'partial_missing_crossfit_chart'
