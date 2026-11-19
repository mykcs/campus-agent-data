import unittest
from unittest.mock import patch
from scripts.collect import parse_index, article_data, extract_dates, classify, collect

class ParserTests(unittest.TestCase):
    def test_index_date_and_dedupe(self):
        html = """<div class="group"><h3><a href='/2026/1020/c90497a3216866/page.htm' title='浙江大学人工智能学院2027年博士研究生招生简章'>招简</a></h3><span>2026-10-20</span></div>"""
        rows = parse_index(html + html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["published_at"], "2026-10-20")
        self.assertTrue(rows[0]["url"].startswith("https://ai.zju.edu.cn/"))
    def test_article_and_attachment(self):
        html = """<div class='wp_articlecontent'><p>博士招生报名时间：2026年11月20日20:00，截止后不予受理。</p><p>报名材料须准备齐全。</p><a href='/_upload/article/files/a.docx'>下载申请表</a></div>"""
        data = article_data(html, "https://ai.zju.edu.cn/2026/1020/c90497a3216866/page.htm")
        self.assertEqual(data["date_candidates"][0]["value"], "2026-11-20T20:00")
        self.assertEqual(len(data["attachments"]), 1)
        self.assertIn("ai.zju.edu.cn", data["attachments"][0]["url"])
    def test_no_false_date_without_context(self):
        self.assertEqual(extract_dates("学校成立于2025年7月1日。"), [])
    def test_categories(self):
        self.assertEqual(classify("2027博士招生简章"), "博士招生")
        self.assertEqual(classify("院设奖学金通知"), "奖助")

    def test_personal_lists_not_mirrored(self):
        def entry(i, title):
            return ("<div class='group'><h3><a href='/2026/1020/c90497a" + str(i) +
                    "/page.htm' title='" + title + "'>详情</a></h3>" +
                    "<span>2026-10-20</span></div>")
        index = (entry(3216866, "2027博士招生简章") +
                 entry(3216867, "2027博士入围名单") +
                 entry(3216868, "2027博士申请说明"))
        article = "<div class='wp_articlecontent'><p>这是公开的招生政策正文：报考条件、申请材料、报名流程请核对学校官方网站。</p></div>"
        def fetch(url):
            if '/zstz/' in url:
                return index
            if '3216867' in url:
                raise AssertionError('Must not fetch personal roster')
            return article
        with patch('scripts.collect.fetch_html', side_effect=fetch), \
                patch('scripts.collect.collect_additional', return_value=([], [], [])):
            snapshot = collect(delay=0)
        records = {item['title']:item for item in snapshot['notices']}
        roster = records['2027博士入围名单']
        self.assertTrue(roster['personal_list'])
        self.assertEqual(roster['content'], '')
        self.assertEqual(roster['attachments'], [])
        self.assertEqual(len(records), 3)

if __name__ == "__main__":
    unittest.main()
