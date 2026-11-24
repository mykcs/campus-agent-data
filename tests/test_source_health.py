import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.collect import main
from scripts.source_health import (
    append_receipt, assess_snapshot, freshness_issues, receipt, utc_now,
)


def example(count=10, status="ok", *, sid="zju-ai-admissions", checked="2026-11-20T06:00:00Z",
            last_success=None):
    source = {
        "id": sid, "status": status, "count": count,
        "last_checked_at": checked,
        "last_success_at": last_success or checked,
    }
    records = [{
        "id": f"item_{i:02d}", "source_id": sid,
        "title": f"公开招生通知 {i}", "url": f"https://ai.zju.edu.cn/2026/1101/c123a{i+5000}/page.htm"
    } for i in range(count)]
    return {
        "version": 2, "checked_at": checked,
        "sources": [source], "notices": records, "errors": []
    }


class SourceHealthTests(unittest.TestCase):
    def test_all_sources_healthy_with_explicit_partial_coverage(self):
        old = example()
        now = example(status="partial", checked="2026-11-20T08:00:00Z")
        health = assess_snapshot(now, old)
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["issues"], [])

    def test_single_source_degraded_reaches_failure_gate(self):
        old = example()
        now = example(status="error", checked="2026-11-20T08:00:00Z",
                      last_success=old["sources"][0]["last_success_at"])
        now["errors"] = ["zju-ai-admissions: simulated timeout"]
        health = assess_snapshot(now, old)
        self.assertEqual(health["status"], "degraded")
        codes = {r["code"] for r in health["issues"]}
        self.assertIn("source_read_failed", codes)
        self.assertIn("collector_reported_errors", codes)

    def test_failure_cannot_advance_last_success(self):
        old = example()
        now = example(status="error", checked="2026-11-20T08:00:00Z")
        self.assertEqual(assess_snapshot(now, old)["status"], "failed")
        self.assertIn("failed_source_advanced_success_time",
                      [i["code"] for i in assess_snapshot(now, old)["issues"]])

    def test_abnormal_drop_fails_closed(self):
        before = example(15)
        after = example(4, checked="2026-11-20T08:00:00Z")
        health = assess_snapshot(after, before)
        self.assertEqual(health["status"], "failed")
        self.assertIn("suspicious_source_drop", [r["code"] for r in health["issues"]])

    def test_disappearing_source_is_fatal(self):
        before = example()
        after = example(10, sid="different-zju-source", checked="2026-11-20T08:00:00Z")
        health = assess_snapshot(after, before)
        self.assertEqual(health["status"], "failed")
        self.assertIn("source_disappeared", [r["code"] for r in health["issues"]])

    def test_duplicated_notice_fails(self):
        now = example(4)
        now["notices"][1]["id"] = now["notices"][0]["id"]
        self.assertEqual(assess_snapshot(now)["status"], "failed")

    def test_unattributed_notice_fails_closed(self):
        for source_id, code in ((None, "notice_source_missing"),
                                ("", "notice_source_missing"),
                                ("unregistered-source", "notice_source_unknown")):
            with self.subTest(source_id=source_id):
                snap = example()
                snap["notices"][0]["source_id"] = source_id
                health = assess_snapshot(snap)
                self.assertEqual(health["status"], "failed")
                self.assertIn(code, [issue["code"] for issue in health["issues"]])

    def test_success_without_valid_timestamp_fails_closed(self):
        for status in ("ok", "partial"):
            for timestamp in (None, "not-a-date"):
                with self.subTest(status=status, timestamp=timestamp):
                    snap = example(status=status)
                    snap["sources"][0]["last_success_at"] = timestamp
                    health = assess_snapshot(snap)
                    self.assertEqual(health["status"], "failed")
                    self.assertIn("source_success_time_missing",
                                  [issue["code"] for issue in health["issues"]])

    def test_previous_notice_ids_can_be_deduplicated_across_sources(self):
        old = example()
        now = example(status="partial", checked="2026-11-20T08:00:00Z")
        now["sources"][0]["count"] = 15  # discovered URL count before URL merge
        self.assertEqual(assess_snapshot(now, old)["status"], "healthy")

    def test_health_receipts_idempotent_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "health-checks.json"
            first = receipt("healthy", current=example(), issues=[],
                            attempted_at="2026-11-20T06:00:00Z")
            append_receipt(path, first)
            append_receipt(path, first)
            self.assertEqual(len(json.loads(path.read_text())["checks"]), 1)
            for i in range(140):
                append_receipt(path, receipt(
                    "healthy", current=example(), issues=[],
                    attempted_at=(datetime(2026, 11, 20, tzinfo=timezone.utc)
                                  + timedelta(seconds=i)).isoformat().replace("+00:00", "Z")
                ))
            entries = json.loads(path.read_text())["checks"]
            self.assertEqual(len(entries), 120)
            self.assertEqual(entries[-1]["status"], "healthy")
            self.assertNotIn("apiKey", path.read_text())

    def test_freshness_fails_if_cron_missing_or_latest_degraded(self):
        now = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)
        old_snapshot = example(checked="2026-11-20T00:00:00Z")
        old_history = {"checks": [{"attempted_at": "2026-11-20T00:00:00Z", "status": "healthy"}]}
        self.assertIn("snapshot_stale", freshness_issues(old_snapshot, old_history, now=now))
        self.assertIn("health_receipt_stale", freshness_issues(old_snapshot, old_history, now=now))
        current_snapshot = example(checked="2026-11-20T07:00:00Z")
        current_history = {"checks": [{"attempted_at": "2026-11-20T07:00:00Z", "status": "degraded"}]}
        self.assertEqual(freshness_issues(current_snapshot, current_history, now=now),
                         ["latest_collection_not_healthy"])

    def test_collector_success_writes_both_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            notices_path = Path(tmp) / "notices.json"
            checks_path = Path(tmp) / "checks.json"
            snap = example(10, checked=utc_now())
            with patch("sys.argv", ["collect.py", "--output", str(notices_path),
                                    "--checks-output", str(checks_path), "--fast"]), \
                 patch("scripts.collect.collect", return_value=snap):
                result = main()
            self.assertEqual(result, 0)
            data = json.loads(notices_path.read_text())
            self.assertEqual(data["health"]["status"], "healthy")
            self.assertEqual(json.loads(checks_path.read_text())["checks"][-1]["status"], "healthy")

    def test_collector_degraded_updates_data_but_exit_code_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            notices_path = Path(tmp) / "notices.json"
            checks_path = Path(tmp) / "checks.json"
            old = example(10)
            now = example(10, status="error", checked=utc_now(),
                          last_success=old["sources"][0]["last_success_at"])
            now["errors"] = ["simulated source read error"]
            notices_path.write_text(json.dumps(old))
            with patch("sys.argv", ["collect.py", "--output", str(notices_path),
                                    "--checks-output", str(checks_path), "--fast"]), \
                 patch("scripts.collect.collect", return_value=now):
                result = main()
            self.assertEqual(result, 2)
            self.assertEqual(json.loads(notices_path.read_text())["health"]["status"], "degraded")
            self.assertEqual(json.loads(checks_path.read_text())["checks"][-1]["status"], "degraded")

    def test_total_abort_preserves_last_known_good_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            notices_path = Path(tmp) / "notices.json"
            checks_path = Path(tmp) / "checks.json"
            old_bytes = (json.dumps(example())+"\n").encode()
            notices_path.write_bytes(old_bytes)
            with patch("sys.argv", ["collect.py", "--output", str(notices_path),
                                    "--checks-output", str(checks_path), "--fast"]), \
                 patch("scripts.collect.collect", side_effect=ConnectionError("Do not leak credentials")):
                result = main()
            self.assertEqual(result, 2)
            self.assertEqual(notices_path.read_bytes(), old_bytes)
            self.assertIn("collector_aborted", checks_path.read_text())
            self.assertNotIn("Do not leak credentials", checks_path.read_text())

    def test_suspect_drop_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            notices_path = Path(tmp) / "notices.json"
            checks_path = Path(tmp) / "checks.json"
            old_bytes = json.dumps(example(10)).encode()
            notices_path.write_bytes(old_bytes)
            now = example(2, checked=utc_now())
            with patch("sys.argv", ["collect.py", "--output", str(notices_path),
                                    "--checks-output", str(checks_path), "--fast"]), \
                 patch("scripts.collect.collect", return_value=now):
                result = main()
            self.assertEqual(result, 2)
            self.assertEqual(notices_path.read_bytes(), old_bytes)
            self.assertIn("suspicious_source_drop", checks_path.read_text())


if __name__ == "__main__":
    unittest.main()
