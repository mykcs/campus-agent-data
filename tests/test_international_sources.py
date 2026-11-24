import unittest
from unittest.mock import patch
from scripts.international_sources import GLOBAL_SOURCES, allowed_article, parse_public_list
from scripts.additional_sources import collect_additional

class MITPublicSourcesTests(unittest.TestCase):
    def test_bulletin_date_url_and_dedup(self):
        spec = next(s for s in GLOBAL_SOURCES if s["kind"]=="hst")
        html = """
        <a href="/news-events/twihst/volume-28-number-10">November 20, 2026 - Volume 28, Number 10</a>
        <a href="/news-events/twihst/volume-28-number-9">November 13, 2026 - Volume 28, Number 9</a>
        <a href="/news-events/twihst/volume-28-number-10">November 20, 2026 - Volume 28, Number 10</a>
        <a href="https://notmit.edu/news-events/twihst/volume-28-number-11">November 21, 2026 - Volume 28, Number 11</a>
        """
        rows = parse_public_list(html, spec)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["published_at"], "2026-11-20")
        self.assertEqual(rows[0]["school"], "MIT")
        self.assertEqual(rows[0]["timezone"], "America/New_York")
        self.assertEqual(rows[0]["date_events"], [])
        self.assertEqual(rows[0]["content"], "")

    def test_funding_reference_not_open_deadline(self):
        spec = next(s for s in GLOBAL_SOURCES if s["kind"]=="oge")
        rows = parse_public_list("""
        <a href="/fellowships/nsf/">NSF Graduate Research Fellowship Program</a>
        <a href="/fellowships/hugh-hampton-young-fellowship/">Hugh Hampton Young Fellowship</a>
        <a href="/fellowships/external-fellowship-intake-form/">External fellowship intake form</a>
        """,spec)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x["published_at"] is None and x["topics"]==["scholarships"] and not x["date_events"] for x in rows))
        self.assertFalse(allowed_article("https://oge.mit.edu.evil.example/fellowships/nsf/", spec))
        self.assertFalse(allowed_article("https://oge.mit.edu/fellowships/nsf/?private=1",spec))

    def test_global_source_failure_preserves_valid_prior(self):
        spec = next(s for s in GLOBAL_SOURCES if s["kind"]=="hst")
        rows = parse_public_list('<a href="/news-events/twihst/volume-28-number-10">November 20, 2026 - Volume 28, Number 10</a>',spec)
        with patch("scripts.additional_sources.fetch_public_html",side_effect=TimeoutError("offline")):
            records,sources,errors = collect_additional({"notices":rows, "sources":[]})
        self.assertTrue(any(x["stale"] and x["source_id"]==spec["id"] for x in records))
        self.assertEqual(next(x["status"] for x in sources if x["id"]==spec["id"]),"error")

if __name__=="__main__":
    unittest.main()
