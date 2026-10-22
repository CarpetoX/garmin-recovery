"""V7.28: el certificador espera si GitHub aún no marca terminada la etapa anterior."""
import unittest

from garmin_recovery import delivery_gate as g

SYNC = {"id": 1, "event": "workflow_dispatch", "status": "completed", "conclusion": "success",
        "created_at": "2026-10-22T14:46:54Z", "updated_at": "2026-10-22T14:47:11Z"}
HEART = {"id": 2, "event": "workflow_run", "status": "completed", "conclusion": "success",
         "created_at": "2026-10-22T14:47:16Z", "updated_at": "2026-10-22T14:48:12Z"}
ADV = {"id": 3, "event": "workflow_run", "status": "completed", "conclusion": "success",
       "created_at": "2026-10-22T14:48:18Z", "updated_at": "2026-10-22T14:48:58Z"}
CF = {"id": 4, "event": "workflow_run", "status": "in_progress", "conclusion": None,
      "created_at": "2026-10-22T14:49:00Z", "updated_at": "2026-10-22T14:49:05Z"}


def fake(lag_calls):
    """Devuelve la Advanced «in_progress» durante las primeras `lag_calls` consultas."""
    calls = {"adv": 0}

    def fetch(url, token):
        if url.endswith("/runs/4"):
            return dict(CF)
        if url.endswith("/runs/3"):
            calls["adv"] += 1
            return dict(ADV, status="in_progress", conclusion=None) if calls["adv"] <= lag_calls else dict(ADV)
        if "garmin-heart-rate.yml" in url:
            return {"workflow_runs": [HEART]}
        return {"workflow_runs": [SYNC]}
    return fetch, calls


class GateRetry(unittest.TestCase):
    def test_waits_for_github_to_publish_completion(self):
        fetch, calls = fake(lag_calls=2)
        waits = []
        chain, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=waits.append)
        self.assertEqual(problems, [])
        self.assertEqual(chain["slot"]["cycle_id"], "2026-10-22-1645")
        self.assertEqual(waits, list(g.RETRY_DELAYS[:2]))

    def test_gives_up_after_retries(self):
        fetch, _ = fake(lag_calls=99)
        waits = []
        _, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=waits.append)
        self.assertEqual(problems, ["advanced_missing_or_not_correlated"])
        self.assertEqual(waits, list(g.RETRY_DELAYS))

    def test_no_retry_when_chain_is_fine_or_problem_is_real(self):
        fetch, _ = fake(lag_calls=0)
        waits = []
        self.assertEqual(g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=waits.append)[1], [])
        self.assertEqual(waits, [])

        def outside(url, token):  # Sync fuera de franja: no se reintenta
            if "sync.yml" in url:
                return {"workflow_runs": [dict(SYNC, created_at="2026-10-22T12:11:00Z", updated_at="2026-10-22T14:47:11Z")]}
            return fetch(url, token)
        _, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=outside, sleep=waits.append)
        self.assertEqual(problems, ["sync_outside_report_slot"])
        self.assertEqual(waits, [])


if __name__ == "__main__":
    unittest.main()
