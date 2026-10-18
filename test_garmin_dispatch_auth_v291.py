import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from garmin_recovery.dispatch_auth import (InvalidOrigin, canonical_message,
    classify, attach_lineage)

KEY = 'some-long-local-test-signing-key-1234567890'
NOW = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)


def sign(at=NOW, cycle='2026-10-11-1645', key=KEY):
    fields = {'origin_source': 'apps_script_backup', 'cycle_id': cycle,
              'requested_at': at.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
              'request_id': '79c9ed03-7074-4f3c-8ae2-ea3c5c083143'}
    fields['origin_proof'] = hmac.new(key.encode(), canonical_message(
        fields['origin_source'], fields['cycle_id'], fields['requested_at'],
        fields['request_id']), hashlib.sha256).hexdigest()
    return {'inputs': fields}


class OriginAuthenticationTests(unittest.TestCase):
    def test_github_schedule(self):
        r = classify('schedule', {}, now=NOW)
        self.assertTrue(r['source_verified'])
        self.assertEqual(r['origin_source'], 'github_schedule')

    def test_manual_without_signature_is_not_called_manual_confirmed(self):
        r = classify('workflow_dispatch', {'inputs': {}}, now=NOW)
        self.assertFalse(r['source_verified'])
        self.assertEqual(r['origin_source'], 'workflow_dispatch_unattributed')

    def test_manual_with_empty_default_inputs(self):
        inp = {k: '' for k in sign()['inputs']}
        self.assertFalse(classify('workflow_dispatch', {'inputs': inp}, now=NOW)['source_verified'])

    def test_valid_signed_apps_script(self):
        r = classify('workflow_dispatch', sign(), KEY, NOW)
        self.assertTrue(r['source_verified'])
        self.assertEqual(r['origin_source'], 'apps_script_backup')
        self.assertEqual(r['auth_method'], 'hmac_sha256_shared_secret_v291')
        self.assertNotIn('origin_proof', r)

    def test_missing_secret_fails_closed_for_claimed_signature(self):
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', sign(), None, NOW)

    def test_wrong_signature_fails(self):
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', sign(), KEY + 'wrong', NOW)

    def test_mislabelled_cycle_fails(self):
        e = sign()
        e['inputs']['cycle_id'] = '2026-10-11-2245'
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', e, KEY, NOW)

    def test_partial_provenance_fails(self):
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', {'inputs': {'origin_source':'apps_script_backup'}}, KEY, NOW)

    def test_expired_signature_fails(self):
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', sign(NOW-timedelta(minutes=35)), KEY, NOW)

    def test_future_signature_fails(self):
        with self.assertRaises(InvalidOrigin):
            classify('workflow_dispatch', sign(NOW+timedelta(minutes=3)), KEY, NOW)

    def test_repository_dispatch_unsigned_remains_unverified(self):
        r = classify('repository_dispatch', {'action':'garmin-sync','client_payload':{}}, now=NOW)
        self.assertFalse(r['source_verified'])

    def test_lineage_propagates_verified_origin(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base/'lineage.json'; op = base/'origin.json'
            p.write_text(json.dumps({'stage':'sync','run_id':123, 'root':{'run_id':123,'origin_certainty':'dispatch_sender_unverified'},'stages':{'sync':{'event':'workflow_dispatch'}}}))
            op.write_text(json.dumps(classify('workflow_dispatch', sign(), KEY, NOW)))
            out = attach_lineage(p, op, 123)
            self.assertEqual(out['root']['origin_certainty'], 'apps_script_hmac_sha256_v291')
            self.assertTrue(json.loads(p.read_text())['root']['origin_v291']['source_verified'])

    def test_lineage_does_not_falsely_verify_manual_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'lineage.json'; op=Path(d)/'origin.json'
            p.write_text(json.dumps({'stage':'sync','run_id':123,'root':{'run_id':123,'origin_certainty':'dispatch_sender_unverified'},'stages':{'sync':{'event':'workflow_dispatch'}}}))
            op.write_text(json.dumps(classify('workflow_dispatch',{},now=NOW)))
            r=attach_lineage(p,op,123)
            self.assertEqual(r['root']['origin_certainty'], 'dispatch_sender_unverified')
            self.assertFalse(r['root']['origin_v291']['source_verified'])

    def test_lineage_mismatched_run_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'lineage.json'; op=Path(d)/'origin.json'
            p.write_text(json.dumps({'stage':'sync','run_id':123,'root':{'run_id':123},'stages':{'sync':{'event':'workflow_dispatch'}}}))
            op.write_text(json.dumps(classify('workflow_dispatch',sign(),KEY,NOW)))
            with self.assertRaises(InvalidOrigin):
                attach_lineage(p,op,124)

if __name__=='__main__':unittest.main()
