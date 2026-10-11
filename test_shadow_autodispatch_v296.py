"""Tests of independent auto-shadow signal; no GitHub/network access."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from shadow_autodispatch_v296 import (
    AutoShadowError, dispatch_if_needed, fetch_mirror_state, validate_state,
)


class Response:
    def __init__(self, code, body=b''):
        self.status = code
        self.body = body
    def read(self):
        return self.body
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


class FakeGitHub:
    def __init__(self, state, dispatch_code=204):
        self.state = state
        self.dispatch_code = dispatch_code
        self.calls = []
    def __call__(self, req, timeout):
        self.calls.append(req)
        if req.get_method() == 'GET':
            blob = json.dumps(self.state).encode()
            return Response(200, json.dumps({'encoding':'base64',
                             'content':base64.b64encode(blob).decode()}).encode())
        return Response(self.dispatch_code)


class AutoShadowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'report_cycles.json'
        # Ledger with valid legacy record: production source is never changed.
        self.ledger = {'schema_version':2,'ledger_version':'2.8.0','purpose':'test',
            'cycles':[{'cycle_id':'2026-10-11-0830',
                       'slot_at':'2026-10-11T08:30:00+02:00',
                       'legacy_without_snapshot':True}], 'count':1}
        self.source.write_text(json.dumps(self.ledger)+'\n', encoding='utf-8')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.state = {'format':'shadow_persist_candidate_v1','version':'2.9.6',
            'source_file_sha256':self.digest,'certificate_count':1,
            'full_original_retained':True,'production_cutover':False,
            'authorizes_replacing_report_cycles':False}

    def run_fake(self, state=None, code=204):
        fake = FakeGitHub(state or self.state, code)
        old = self.source.read_bytes()
        try:
            output = dispatch_if_needed(self.source,'CarpetoX/garmin-recovery','dummy',
                                         opener=fake,run_id='9876')
            self.assertEqual(self.source.read_bytes(),old)
            return output, fake
        finally:
            self.assertEqual(self.source.read_bytes(),old)

    def test_unchanged_source_does_not_dispatch(self):
        out, fake = self.run_fake()
        self.assertEqual(out['status'],'already_mirrored_no_dispatch')
        self.assertEqual([r.get_method() for r in fake.calls],['GET'])

    def test_new_source_dispatches_only_shadow_event(self):
        state={**self.state,'source_file_sha256':'a'*64,'certificate_count':0}
        out, fake = self.run_fake(state)
        self.assertEqual(out['status'],'dispatch_accepted_not_yet_published')
        self.assertEqual([r.get_method() for r in fake.calls],['GET','POST'])
        sent=json.loads(fake.calls[-1].data)
        self.assertEqual(sent['event_type'],'garmin-shadow-publish')
        self.assertEqual(sent['client_payload']['source_cycle_count'],1)
        self.assertEqual(sent['client_payload']['source_sha256'],self.digest)
        self.assertEqual(sent['client_payload']['monitor_run_id'],'9876')
        self.assertNotIn('Authorization', sent)

    def test_only_204_accepted(self):
        state={**self.state,'source_file_sha256':'a'*64,'certificate_count':0}
        with self.assertRaisesRegex(AutoShadowError,'HTTP 200'):
            self.run_fake(state,code=200)

    def test_deleted_state_does_not_bootstrap_silently(self):
        def missing(req, timeout):
            raise HTTPError(req.full_url,404,'Not Found',{},None)
        with self.assertRaisesRegex(AutoShadowError,'HTTP 404'):
            fetch_mirror_state('CarpetoX/garmin-recovery','dummy',opener=missing)

    def test_invalid_state_rejected(self):
        for change in [{'production_cutover':True},
                       {'full_original_retained':False},
                       {'authorizes_replacing_report_cycles':True},
                       {'certificate_count':2},
                       {'source_file_sha256':'invalid'},
                       {'version':'2.9.7'},
                       {'certificate_count':True}]:
            with self.subTest(change=change),self.assertRaises(AutoShadowError):
                self.run_fake({**self.state,**change})

    def test_same_digest_different_count_rejected(self):
        with self.assertRaises(AutoShadowError):
            validate_state({**self.state,'certificate_count':0},self.digest,1)

    def test_corrupt_source_never_calls_github(self):
        self.source.write_text('{corrupt',encoding='utf-8')
        fake=FakeGitHub(self.state)
        with self.assertRaises(ValueError):
            dispatch_if_needed(self.source,'CarpetoX/garmin-recovery','dummy',opener=fake)
        self.assertEqual(fake.calls,[])

    def test_duplicate_certificate_rejected_before_dispatch(self):
        self.ledger['cycles'].append(self.ledger['cycles'][0])
        self.ledger['count']=2
        self.source.write_text(json.dumps(self.ledger),encoding='utf-8')
        fake=FakeGitHub(self.state)
        with self.assertRaises(ValueError):
            dispatch_if_needed(self.source,'CarpetoX/garmin-recovery','dummy',opener=fake)
        self.assertEqual(fake.calls,[])

    def test_no_credentials_does_not_probe(self):
        fake=FakeGitHub(self.state)
        with self.assertRaisesRegex(AutoShadowError,'GH_TOKEN'):
            dispatch_if_needed(self.source,'CarpetoX/garmin-recovery','',opener=fake)
        self.assertEqual(fake.calls,[])

    def test_api_auth_headers_not_in_report(self):
        out, fake=self.run_fake()
        self.assertNotIn('dummy',json.dumps(out))
        self.assertTrue(fake.calls[0].has_header('Authorization'))

    def test_invalid_remote_base64_rejected(self):
        def malformed(req, timeout):
            return Response(200,b'{"encoding":"base64","content":"!!"}')
        with self.assertRaises(AutoShadowError):
            fetch_mirror_state('CarpetoX/garmin-recovery','dummy',opener=malformed)


if __name__=='__main__':
    unittest.main()
