"""V4.0.1 visual snapshot regression tests, all offline and deterministic."""
import copy
import html
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cycle_snapshot_report_v38 import SnapshotError, digest
from garmin_report_v40 import latest_id
from test_garmin_report_v40 import fixture
from report_visual_v401 import render, publish


class VisualTests(unittest.TestCase):
    def test_realistic_visual_sections_and_metrics(self):
        ledger, cid = fixture()
        page, meta = render(ledger, cid)
        for expected in ('<!doctype html>', '<html lang="es">', 'width=device-width',
                         'Recuperación fisiológica', '88/100', 'HRV nocturna', '66 ms',
                         'FC reposo', '53 lpm', '03 · Carga CrossFit', '112',
                         '04 · Entrenamiento resumido', '1457.7', '30 465 kg',
                         'Entrega no verificada', 'SHA-256 del snapshot', 'sRPE'):
            self.assertIn(expected, page)
        self.assertIn('<svg', page)
        self.assertIn('prefers-color-scheme:dark', page)
        self.assertTrue(meta['sleep_confirmed'])
        self.assertTrue(meta['chart_complete'])

    def test_offline_no_scripts_or_external_resources(self):
        ledger, cid = fixture()
        page, _ = render(ledger, cid)
        self.assertNotIn('<script', page.lower())
        self.assertNotIn('https://', page)
        self.assertNotIn('http://', page)
        self.assertNotIn('<iframe', page)

    def test_deterministic_and_no_mutation(self):
        ledger, cid = fixture()
        before = copy.deepcopy(ledger)
        self.assertEqual(render(ledger, cid), render(copy.deepcopy(ledger), cid))
        self.assertEqual(ledger, before)

    def test_malformed_snapshot_fails_closed(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['recovery_assessment']['score'] = 50
        with self.assertRaises(SnapshotError):
            render(ledger, cid)

    def test_pending_sleep_hides_sleep_and_hrv(self):
        ledger, cid = fixture(confirmed=False)
        page, info = render(ledger, cid)
        self.assertFalse(info['sleep_confirmed'])
        self.assertIn('Sueño pendiente', page)
        self.assertIn('No se muestra la distribución de fases', page)
        self.assertNotIn('7.23 h', page)
        self.assertNotIn('66 ms', page)
        self.assertNotIn('Sueño confirmado</p><div class="focal">7.23 h', page)

    def test_sleep_gate_pending_even_with_stale_assessed_state(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['morning_sleep'] = {'state': 'pending', 'evidence_valid': False}
        ledger['cycles'][0]['snapshot_sha256'] = digest(ledger['cycles'][0]['snapshot'])
        page, info = render(ledger, cid)
        self.assertFalse(info['sleep_confirmed'])
        self.assertIn('Pendiente', page)
        self.assertNotIn('<div class="metric-number caution">88/100</div>', page)
        self.assertIn('<span>FC nocturna</span>', page)
        self.assertNotIn('58.3 lpm</strong><span>FC nocturna', page)

    def test_stale_heart_rate_absent_from_today_panel(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['garmin']['heart_rate_today']['date'] = '2026-10-11'
        ledger['cycles'][0]['snapshot_sha256'] = digest(ledger['cycles'][0]['snapshot'])
        page, info = render(ledger, cid)
        self.assertIn('La FC registrada no corresponde al día del ciclo', page)
        self.assertIn('FC reposo</p><div class="metric-number neutral">No disponible', page)

    def test_partial_day_is_stated(self):
        ledger, cid = fixture()
        page, _ = render(ledger, cid)
        self.assertIn('día parcial', page)

    def test_chart_not_invented_for_missing_data(self):
        ledger, cid = fixture(complete=False)
        page, info = render(ledger, cid)
        self.assertFalse(info['chart_complete'])
        self.assertIn('Gráfica de carga semanal no disponible', page)
        self.assertNotIn('<svg class="chart-svg"', page)

    def test_missing_chart_values_are_not_zero(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['crossfit']['performance_report']['daily_chart_7d'][3]['srpe_from_recorded_duration'] = None
        ledger['cycles'][0]['snapshot_sha256'] = digest(ledger['cycles'][0]['snapshot'])
        page, _ = render(ledger, cid)
        self.assertIn('Gráfica de carga incompleta', page)
        self.assertNotIn('<svg class="chart-svg"', page)

    def test_duplicate_chart_date_not_rendered(self):
        ledger, cid = fixture()
        snap = ledger['cycles'][0]['snapshot']
        snap['crossfit']['performance_report']['daily_chart_7d'][0]['date'] = snap['crossfit']['performance_report']['daily_chart_7d'][1]['date']
        ledger['cycles'][0]['snapshot_sha256'] = digest(snap)
        page, _ = render(ledger, cid)
        self.assertIn('Gráfica de carga semanal no disponible', page)

    def test_html_escaping_untrusted_recommendations(self):
        ledger, cid = fixture()
        rec = '<script>alert("XSS")</script><svg onload=alert(1)>'
        ledger['cycles'][0]['snapshot']['crossfit']['performance_report']['recommendations'][0]['text'] = rec
        ledger['cycles'][0]['snapshot_sha256'] = digest(ledger['cycles'][0]['snapshot'])
        page, _ = render(ledger, cid)
        self.assertIn(html.escape(rec, quote=True), page)
        self.assertNotIn('<script', page)
        self.assertNotIn('onload=alert(1)>', page)

    def test_idempotence_and_hash_manifest(self):
        ledger, cid = fixture()
        with TemporaryDirectory() as td:
            one = publish(ledger, cid, td, write=True)
            two = publish(ledger, cid, td, write=True)
            self.assertEqual(one['state'], 'published_local')
            self.assertEqual(two['state'], 'already_present')
            self.assertEqual(len(list(Path(td).glob('*.html'))), 1)
            self.assertEqual(len(list(Path(td).glob('*.manifest.json'))), 1)
            manifest = json.loads((Path(td) / one['manifest_file']).read_text())
            self.assertEqual(manifest['html_sha256'], one['html_sha256'])
            self.assertEqual(manifest['delivery'], 'unverified_no_chatgpt_receipt')

    def test_conflict_preserves_original(self):
        ledger, cid = fixture()
        with TemporaryDirectory() as td:
            out = publish(ledger, cid, td, write=True)
            original = Path(td) / out['html_file']
            original.write_text('wrong', encoding='utf-8')
            with self.assertRaises(SnapshotError):
                publish(ledger, cid, td, write=True)
            self.assertEqual(original.read_text(), 'wrong')

    def test_dry_run_leaves_no_folder(self):
        ledger, cid = fixture()
        with TemporaryDirectory() as td:
            dest = Path(td) / 'new'
            out = publish(ledger, cid, dest, write=False)
            self.assertEqual(out['state'], 'dry_run')
            self.assertFalse(dest.exists())

    def test_unverified_delivery_disclaimer(self):
        ledger, cid = fixture()
        page, meta = render(ledger, cid)
        self.assertIn('La entrega de este informe en ChatGPT permanece sin verificar', page)
        self.assertEqual(meta['delivery'], 'unverified_no_chatgpt_receipt')

    def test_stale_recovery_hidden(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['recovery_assessment']['current']['date'] = '2026-10-11'
        ledger['cycles'][0]['snapshot_sha256'] = digest(ledger['cycles'][0]['snapshot'])
        page, _ = render(ledger, cid)
        self.assertIn('Pendiente', page)
        self.assertNotIn('<div class="metric-number positive">88/100</div>', page)

    def test_real_ledger_when_available(self):
        path = Path('report_cycles.json')
        if not path.exists():
            self.skipTest('Real ledger not available in local bundle')
        ledger = json.loads(path.read_text(encoding='utf-8'))
        page, meta = render(ledger, latest_id(ledger))
        self.assertIn(meta['snapshot_sha256'], page)
        self.assertIn('<html lang="es">', page)


if __name__ == '__main__':
    unittest.main()
