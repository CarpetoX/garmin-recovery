import unittest
from security.export_gate import inspect_certificate

class ExportGateTests(unittest.TestCase):
    def test_empty_fails_closed(self):
        self.assertFalse(inspect_certificate({})['eligible_for_further_verification'])
    def test_not_ready_fails(self):
        self.assertFalse(inspect_certificate({'status': 'pending'})['eligible_for_further_verification'])
    def test_chain_must_be_complete(self):
        self.assertFalse(inspect_certificate({'status': 'ready', 'cycle_id': 'x', 'chain': {}})['eligible_for_further_verification'])

if __name__ == '__main__':
    unittest.main()
