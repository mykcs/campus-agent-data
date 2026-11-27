import unittest
from datetime import datetime,timezone
from scripts.service_sources import SOURCES,parse,title_window,collect

NOW=datetime(2026,11,27,18,tzinfo=timezone.utc)
class ServiceSourcesTests(unittest.TestCase):
    def test_actual_zju_public_row_and_unknown_end(self):
        html="""<h1>班车信息</h1><li><a href="/2026/1106/c68136a3223868/page.htm">关于2026年冬学期班车运行安排的通知 （11月9日开始）</a><time>2026.11.06</time></li>
        <li><a href="https://pi.zju.edu.cn.evil.test/2026/1106/c68136a3223868/page.htm">伪造班车时刻</a></li>"""
        rows=parse(html,SOURCES[0],NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["published_at"],"2026-11-06")
        self.assertEqual(rows[0]["effective_from"],"2026-11-09")
        self.assertIsNone(rows[0]["effective_until"])
        self.assertEqual(rows[0]["availability"],"verify")
        self.assertNotIn("content",rows[0])
    def test_unverified_year_and_expired_explicit_range(self):
        self.assertEqual(title_window("关于11月7日开始的班车通知"),(None,None))
        html='<h1>班车信息</h1><a href="/2026/0914/c68136a3202662/page.htm">班车2026年9月14日至2026年11月8日运行</a>'
        self.assertEqual(parse(html,SOURCES[0],NOW)[0]["availability"],"expired")
    def test_reference_no_guessed_effective_date_or_hours(self):
        row=parse("<h1>Forms &amp; Petitions</h1>",SOURCES[3],NOW)[0]
        self.assertEqual(row["detail"],"official_reference_only")
        self.assertIsNone(row["published_at"]);self.assertIsNone(row["effective_from"])
        self.assertEqual(row["availability"],"verify")
        with self.assertRaises(ValueError):parse("<h1>Login</h1>",SOURCES[3],NOW)
    def test_unavailable_preserves_cached_only_and_marks_failure(self):
        row=parse("<h1>Forms</h1>",SOURCES[3],NOW)[0]
        def offline(*a):raise TimeoutError()
        d=collect({"services":[row],"sources":[]},offline)
        self.assertEqual(d["status"],"degraded")
        self.assertTrue(d["services"][0]["stale"])
        self.assertTrue(all(x["status"]=="error" for x in d["sources"]))
