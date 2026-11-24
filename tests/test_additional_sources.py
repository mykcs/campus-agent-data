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
        self.assertEqual(sum(s["status"]=="error" for s in sources),len(QUERIES)-1)
        self.assertEqual(len(errors),len(QUERIES)-1)
        self.assertEqual(next(s["status"] for s in sources if s["id"]=="zju-mse-student"),"ok")

    def test_personal_list_title_only(self):
        html = """<a href='/2026/0916/c51031a3204160/page.htm'>2026年学生推免入围名单公示</a>"""
        rows=parse_source(html,QUERIES[3])
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["personal_list"])
        self.assertFalse(rows[0]["content"])
        self.assertFalse(rows[0]["attachments"])

    def test_two_real_public_funding_college_source_contracts(self):
        history=next(q for q in QUERIES if q["id"]=="zju-history-aid")
        engineering=next(q for q in QUERIES if q["id"]=="zju-engineering-aid")
        history_html = """
        <section><div><a href='/2026/1108/c65208a3224085/page.htm'>研究生助学金推荐评定 2026-11-08</a></div>
        <div><a href='/2026/1101/c65208a3221286/page.htm'>历史学院圆梦助学金申请 2026-11-01</a></div></section>
        """
        rows=parse_source(history_html,history)
        self.assertEqual(len(rows),2)
        self.assertEqual([x["published_at"] for x in rows],["2026-11-08","2026-11-01"])
        self.assertTrue(all("scholarships" in x["topics"] for x in rows))
        self.assertFalse(any(x["date_inferred"] for x in rows))
        self.assertNotIn("2026-11-01",rows[1]["title"])
        engineering_html = """
        <div><a href='/2026/1119/c67027a3229397/page.htm'>工程师学院研究生奖学金评选通知</a></div>
        <div><a href='/2026/1118/c67027a3228740/page.htm'>学业优秀奖助金评选</a></div>
        <div><a href='/2026/1119/c67027a3229100/page.htm'>2026校园体育节活动</a></div>"""
        eng=parse_source(engineering_html,engineering)
        self.assertEqual(len(eng),2)
        self.assertTrue(all(x["department_id"]=="zju-engineering" for x in eng))
        self.assertTrue(all(x["topics"]==["scholarships"] for x in eng))
        self.assertTrue(all(x["content"]=="" and x["attachments"]==[] for x in eng))

    def test_sibling_publication_date_cannot_contaminate_item(self):
        source=next(q for q in QUERIES if q["id"]=="zju-history-aid")
        html = """
        <div class="common-list">
          <div><a href="/2026/1108/c65208a3224085/page.htm">2026年研究生助学金通知</a>
               <time>发布时间：2026-11-08</time></div>
          <div><a href="/2026/1101/c65208a3221286/page.htm">2026学年奖学金申请通知</a></div>
        </div>"""
        rows=parse_source(html,source)
        self.assertEqual([x["published_at"] for x in rows],["2026-11-08","2026-11-01"])
        self.assertFalse(rows[0]["date_inferred"])
        self.assertTrue(rows[1]["date_inferred"])

    def test_new_source_allowlist_never_accepts_similar_hostnames(self):
        source=next(q for q in QUERIES if q["id"]=="zju-engineering-aid")
        html = """
        <a href='https://notpi.zju.edu.cn/2026/1119/c67027a3229397/page.htm'>研究生奖学金通知</a>
        <a href='https://pi.zju.edu.cn/2026/1119/c67027a3229397/page.htm'>研究生奖学金通知</a>"""
        rows=parse_source(html,source)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"].split("/")[2],"pi.zju.edu.cn")

if __name__=="__main__":
    unittest.main()
