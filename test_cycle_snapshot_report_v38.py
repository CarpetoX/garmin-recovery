import copy
import unittest
from cycle_snapshot_report_v38 import build, SnapshotError, digest

CID = '2026-10-12-1645'
SNAP = {'date':'2026-10-12', 'source_generated_at':{'crossfit_insights.json':'2026-10-12T17:00:33+02:00'}, 'crossfit':{'activities':[{'rpe':6}]}, 'recovery_assessment':{'score':70}}
ROW = {'cycle_id':CID, 'slot_at':'2026-10-12T16:45:00+02:00', 'state':'data_ready', 'snapshot':SNAP, 'snapshot_sha256':digest(SNAP), 'source_generated_at':SNAP['source_generated_at']}

class TestV38(unittest.TestCase):
    def ledger(self): return {'cycles':[copy.deepcopy(ROW)]}
    def test_valid(self):
        r=build(self.ledger(), CID)
        self.assertEqual(r['data']['crossfit']['activities'][0]['rpe'], 6)
        self.assertEqual(r['source'], 'immutable_ledger_snapshot_only')
        self.assertEqual(r['chatgpt_delivery'], 'unverified_no_receipt')
    def test_missing(self):
        with self.assertRaises(SnapshotError): build(self.ledger(), '2026-10-11-1645')
    def test_duplicate(self):
        l=self.ledger(); l['cycles'].append(copy.deepcopy(ROW))
        with self.assertRaises(SnapshotError): build(l,CID)
    def test_tampered(self):
        l=self.ledger(); l['cycles'][0]['snapshot']['crossfit']['activities'][0]['rpe']=10
        with self.assertRaises(SnapshotError): build(l,CID)
    def test_mixed_provenance(self):
        l=self.ledger(); l['cycles'][0]['source_generated_at']={}
        with self.assertRaises(SnapshotError): build(l,CID)
    def test_not_ready(self):
        l=self.ledger(); l['cycles'][0]['state']='pending'
        with self.assertRaises(SnapshotError): build(l,CID)
    def test_legacy(self):
        l=self.ledger(); del l['cycles'][0]['snapshot']
        with self.assertRaises(SnapshotError): build(l,CID)
    def test_no_live_data(self):
        l=self.ledger(); l['live_override']={'rpe':10}
        self.assertEqual(build(l,CID)['data']['crossfit']['activities'][0]['rpe'],6)
    def test_wrong_date(self):
        l=self.ledger(); l['cycles'][0]['snapshot']['date']='2026-10-11'; l['cycles'][0]['snapshot_sha256']=digest(l['cycles'][0]['snapshot'])
        with self.assertRaises(SnapshotError): build(l,CID)

if __name__=='__main__': unittest.main()
