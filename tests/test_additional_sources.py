import unittest
from unittest.mock import patch
from scripts.additional_sources import (
    QUERIES, parse_source, official, clean_title,
    collect_additional, topics
)

class AdditionalSourcesTests(unittest.TestCase):
    def test_only_official_article_links(self):
        self.assertTrue(official("http://www.cs.zju.edu.cn/csen/2026/0914/c27006a3202278/page.htm"))
        self.assertFalse(official("https://example.com/2026/0914/c27006a3202278/page.htm"))
        self.assertFalse(official("javascript:alert(1)"))

    def test_cs_public_search_filters_domain(self):
        html = """<div><a href='http://www.cs.zju.edu.cn/csen/2026/0914/c27006a3202278/page.htm'>计算机 科学 与 技术学院 2027年招生复试公告</a>
        <span>发布时间：2026-09-14 | 信息来源：计算机学院</span></div>
        <div><a href='http://example.com/2026/0914/c100a200/page.htm'>恶意链接</a></div>
        <div><a href='http://www.cst.zju.edu.cn/2026/0914/c32178a3201870/page.htm'>软件学院新闻</a></div>"""
        data = parse_source(html,QUERIES[0])
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["department_id"],"zju-cs")
        self.assertIn("计算机科学与技术学院",data[0]["title"])
        self.assertEqual(data[0]["published_at"],"2026-09-14")
        self.assertFalse(data[0]["date_inferred"])

    def test_scholarship_topic(self):
        html = """<div><a href='http://www.cst.zju.edu.cn/2026/0911/c36224a3201709/page.htm'>研究生竺可桢奖学金通知</a></div>
        <div><a href='http://www.cst.zju.edu.cn/2026/0912/c36224a3201900/page.htm'>无关新闻</a></div>"""
        data = parse_source(html,QUERIES[2])
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["topics"],["scholarships"])
        self.assertEqual(data[0]["published_at"],"2026-09-11")
        self.assertTrue(data[0]["date_inferred"])

    def test_collector_marks_source_errors_not_fabricates(self):
        html = "<a href='/2026/1119/c51031a3229169/page.htm'>关于开展学业优秀奖助金评选工作的通知</a>"
        def mock_fetch(url):
            if url.startswith("https://mse."):
                return html
            raise TimeoutError("source offline")
        with patch("scripts.additional_sources.fetch_public_html",side_effect=mock_fetch):
            notices,sources,errors = collect_additional()
        self.assertEqual(len(notices),1)
        self.assertEqual(sum(s["status"]=="error" for s in sources),3)
        self.assertEqual(len(errors),3)
        self.assertEqual(sources[-1]["status"],"ok")

    def test_personal_list_title_only(self):
        html = """<a href='/2026/0916/c51031a3204160/page.htm'>2026年学生推免入围名单公示</a>"""
        rows=parse_source(html,QUERIES[3])
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["personal_list"])
        self.assertFalse(rows[0]["content"])
        self.assertFalse(rows[0]["attachments"])

if __name__=="__main__":
    unittest.main()
