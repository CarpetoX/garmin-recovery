"""V4.0.2 offline visual dashboard, metadata and immutable publisher tests."""
import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from cycle_snapshot_report_v38 import SnapshotError,digest
from test_garmin_report_v40 import fixture
from test_report_visual_data_v402 import add_day,resign
from report_visual_v402 import render,publish, spark


class VisualV402Tests(unittest.TestCase):
    def setUp(self):
        self.ledger,self.cid=fixture()

    def test_complete_sections(self):
        page, meta=render(self.ledger,self.cid)
        for string in ('Mini tendencias','Calendario · 28 días','Evolución de fuerza',
                       'Cronología de sueño','Intensidad y tipos de sesión','Fiabilidad de las visualizaciones'):
            self.assertIn(string,page)
        self.assertIn('4.0.2-visual-preview',json.dumps(meta))
        self.assertEqual(meta['coverage']['historical_days_28d'],1)

    def test_offline_no_script_no_external_network(self):
        page,_=render(self.ledger,self.cid)
        self.assertNotIn('<script',page)
        self.assertNotIn('https://',page)
        self.assertNotIn('<iframe',page)
        self.assertIn('<svg',page)

    def test_pending_sleep_hides_recovery_spark(self):
        s=self.ledger['cycles'][0]['snapshot'];s['morning_sleep']={'state':'pending','evidence_valid':False}
        resign(self.ledger['cycles'][0]);page,meta=render(self.ledger,self.cid)
        self.assertIn('Cronología no disponible',page)
        self.assertEqual(meta['coverage']['hrv_7d'],0)
        self.assertNotIn('66.0 ms</div>',page)

    def test_missing_strength_is_explicit(self):
        page,meta=render(self.ledger,self.cid)
        self.assertIn('series manuales por ejercicio',page)
        self.assertEqual(meta['visual_panels']['strength'],'insufficient_structured_manual_sets')

    def test_strength_shown_when_verified(self):
        s=self.ledger['cycles'][0]['snapshot']
        s['crossfit']['activities_today']=[{'date':'2026-10-12','activity_id':'run-1','manual_strength_sets':[{'exercise':'deadlift','equipment':'barbell','weight_kg':180,'reps':2,'verified':True}]}]
        resign(self.ledger['cycles'][0]);page,meta=render(self.ledger,self.cid)
        self.assertIn('Peso muerto',page)
        self.assertIn('180 kg',page)
        self.assertEqual(meta['visual_panels']['strength'],'rendered')

    def test_timeline_absent_is_honest(self):
        page,meta=render(self.ledger,self.cid)
        self.assertIn('No se inventa su orden',page)
        self.assertEqual(meta['visual_panels']['sleep_timeline'],'stages_aggregated_only_or_pending')

    def test_chart_28days_has_missing_cells(self):
        page,_=render(self.ledger,self.cid)
        self.assertEqual(page.count('class="rec-day"'),28)
        self.assertEqual(page.count('data-status="missing"'),27)

    def test_quality_quarantine_historical_row(self):
        old=add_day(self.ledger,'2026-10-11')
        old['snapshot']['recovery_assessment']['score']=-999
        page,meta=render(self.ledger,self.cid)
        self.assertIn('excluidos por no superar validación',page)
        self.assertEqual(meta['coverage']['quarantined_invalid_historical_cycles'],1)

    def test_visual_dates_escaped(self):
        s=self.ledger['cycles'][0]['snapshot']
        s['crossfit']['activities_today']=[{'date':'2026-10-12','activity_id':123,'manual_strength_sets':[{'exercise':'<script>alert(1)</script>','equipment':'barbell','weight_kg':200,'reps':3,'verified':True}]}]
        resign(self.ledger['cycles'][0]);page,_=render(self.ledger,self.cid)
        self.assertNotIn('<script>alert',page)

    def test_spark_missing_values_not_joined(self):
        svg=spark([{'date':'2026-10-10','value':5},{'date':'2026-10-11','value':None},{'date':'2026-10-12','value':9}], 'Sueño')
        self.assertNotIn('polyline',svg)
        self.assertIn('sin dato',svg)

    def test_spark_all_missing_no_zero(self):
        html=spark([{'date':'2026-10-12','value':None}], 'Sueño')
        self.assertIn('Sin mediciones certificadas',html)
        self.assertNotIn('<svg',html)

    def test_determinism(self):
        self.assertEqual(render(self.ledger,self.cid),render(copy.deepcopy(self.ledger),self.cid))

    def test_source_tampering_rejected(self):
        self.ledger['cycles'][0]['snapshot']['recovery_assessment']['score']=12
        with self.assertRaises(SnapshotError):render(self.ledger,self.cid)

    def test_immutable_write_and_second_run(self):
        with TemporaryDirectory() as temp:
            first=publish(self.ledger,self.cid,temp,True)
            second=publish(self.ledger,self.cid,temp,True)
            self.assertEqual(first['state'],'published_local')
            self.assertEqual(second['state'],'already_present')
            self.assertEqual(len(list(Path(temp).glob('*-v402-visual.html'))),1)
            man=json.loads(next(Path(temp).glob('*v402*.manifest.json')).read_text())
            self.assertEqual(man['html_sha256'],first['html_sha256'])

    def test_dry_run_does_not_write(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'not-there'
            r=publish(self.ledger,self.cid,target,False)
            self.assertEqual(r['state'],'dry_run')
            self.assertFalse(target.exists())

    def test_conflict_does_not_overwrite(self):
        with TemporaryDirectory() as temp:
            r=publish(self.ledger,self.cid,temp,True)
            path=Path(temp)/r['html_file']
            path.write_text('modified')
            with self.assertRaises(SnapshotError):publish(self.ledger,self.cid,temp,True)
            self.assertEqual(path.read_text(),'modified')

    def test_real_ledger_if_bundled(self):
        path=Path('report_cycles.json')
        if not path.is_file():self.skipTest('Real ledger available in GitHub CI')
        ledger=json.loads(path.read_text(encoding='utf-8'))
        from garmin_report_v40 import latest_id
        cid=latest_id(ledger)
        page,meta=render(ledger,cid)
        self.assertIn('28 días',page)
        self.assertEqual(meta['cycle_id'],cid)
        self.assertEqual(meta['chatgpt_delivery'],'unverified_no_receipt')


if __name__=='__main__':unittest.main()
