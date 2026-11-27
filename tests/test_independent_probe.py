import unittest
from datetime import datetime,timezone
from scripts.independent_probe import observe,inspect,transition,API,RAW

NOW=datetime(2026,11,27,18,tzinfo=timezone.utc)
SHA="a"*40
def pair(at="2026-11-27T16:00:00Z",status="healthy"):
    return ({"checked_at":at,"health":{"status":status,"assessed_at":at},"notices":[{}],"sources":[{"status":"partial"}]},
            {"checks":[{"attempted_at":at,"status":status,"notices":1}]})
class IndependentProbeTests(unittest.TestCase):
    def test_pinned_same_revision_and_partial_success(self):
        a,b=pair()
        seen=[]
        def f(u):
            seen.append(u)
            return {"sha":SHA} if u==API else a if u.endswith("notices.json") else b
        self.assertEqual(observe(f,now=NOW)["status"],"healthy")
        self.assertEqual(seen,[API,RAW+SHA+"/data/notices.json",RAW+SHA+"/data/health-checks.json"])
    def test_missed_runs_and_failed_receipts(self):
        a,b=pair("2026-11-27T10:00:00Z")
        self.assertIn("snapshot_stale",inspect(a,b,NOW))
        a,b=pair(status="failed")
        self.assertIn("latest_collection_not_healthy",inspect(a,b,NOW))
        self.assertEqual(inspect({}, {},NOW),["malformed-health-input"])
    def test_mixed_snapshot_rejected_and_whole_provider_outage(self):
        a,b=pair();b["checks"][0]["notices"]=2
        self.assertIn("snapshot_receipt_mismatch",inspect(a,b,NOW))
        def fail(u):raise TimeoutError("test")
        self.assertEqual(observe(fail,now=NOW)["codes"],["public_health_input_unavailable"])
    def test_dedup_and_recovery(self):
        failed={"status":"failed","codes":["snapshot_stale"]}
        ok={"status":"healthy","codes":[]}
        self.assertEqual(transition({},ok,NOW)["event"],"none")
        first=transition(ok,failed,NOW)
        self.assertEqual(first["event"],"incident")
        self.assertEqual(transition(first,failed,NOW)["event"],"none")
        self.assertEqual(transition(first,ok,NOW)["event"],"recovered")
