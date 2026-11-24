import unittest

from scripts.date_evidence import extract_date_events
from scripts.collect import article_data

URL = "https://ai.zju.edu.cn/2026/1020/c90497a3216866/page.htm"


class DateEvidenceTests(unittest.TestCase):
    def events(self, text):
        rows = extract_date_events(text, URL)
        self.assertTrue(all(x["verified"] is False and x["source_url"] == URL for x in rows))
        return rows

    def test_public_admissions_multiple_scopes_and_same_day(self):
        # Synthetic wording with the two distinct workflows found in the
        # official October 20 admissions notice. No applicant records.
        rows = self.events("春季硕博连读考生报名：2026年10月20日9:00-2026年11月20日20:00；"
                           "秋季普通招考报名：2027年3月1日9:00至2027年3月20日20:00；"
                           "纸质材料请在2026年11月25日前寄出；邮寄以2026年11月25日之前邮戳为准。")
        self.assertEqual([(x["type"], x["value"]) for x in rows[:4]], [
            ("open", "2026-10-20T09:00"), ("close", "2026-11-20T20:00"),
            ("open", "2027-03-01T09:00"), ("close", "2027-03-20T20:00")])
        self.assertEqual(rows[0]["scope_text"], rows[1]["scope_text"])
        self.assertNotEqual(rows[0]["scope_text"], rows[2]["scope_text"])
        self.assertEqual([x["value"] for x in rows[-2:]], ["2026-11-25", "2026-11-25"])
        self.assertEqual(rows[-1]["type"], "postmark")

    def test_yearless_midnight_not_guessed(self):
        rows = self.events("2026年8月10日9:00开始，截止时间9月10日24：00，请提交申请。")
        self.assertEqual(rows[0]["type"], "open")
        self.assertEqual(rows[1]["type"], "close")
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[1]["resolution"], "unresolved_time")
        self.assertTrue(rows[1]["has_time"])
        clue = self.events("报名截止时间9月10日20:00。")[0]
        self.assertIsNone(clue["value"])
        self.assertEqual(clue["resolution"], "missing_year")

    def test_specific_date_types_and_explicit_zone(self):
        rows = self.events("学院内部截止时间：2026年11月20日17:00 UTC+08:00；"
                           "推荐截止时间：2026年11月21日；"
                           "奖学金材料请在2026年11月22日前提交。")
        self.assertEqual([x["type"] for x in rows], ["internal", "recommendation", "close"])
        self.assertEqual(rows[0]["timezone"], "UTC+08:00")
        self.assertIsNone(rows[1]["timezone"])
        self.assertFalse(rows[1]["has_time"])

    def test_unknown_and_invalid_not_confirmed(self):
        self.assertEqual(self.events("学校成立于2025年7月1日。"), [])
        rows = self.events("申请流程说明：2026年2月30日；综合考核通知：2026年7月11日。")
        self.assertEqual(rows[0]["resolution"], "invalid_date")
        self.assertIsNone(rows[0]["value"])
        self.assertEqual(rows[1]["type"], "unknown")
        self.assertNotIn("eligible", rows[1])

    def test_attachment_not_parsed_and_legacy_compatible(self):
        html = ("<div class='wp_articlecontent'><p>报名截止时间：2026年11月20日20:00。</p>"
                "<a href='/_upload/article/files/a.docx'>申请材料及其他期限见附件</a></div>")
        data = article_data(html, URL)
        self.assertEqual(data["date_candidates"][0]["value"], "2026-11-20T20:00")
        self.assertEqual(len(data["date_events"]), 1)
        self.assertEqual(data["date_events"][0]["type"], "close")
        self.assertFalse(data["date_events"][0]["verified"])
        self.assertEqual(len(data["attachments"]), 1)


if __name__ == "__main__":
    unittest.main()
