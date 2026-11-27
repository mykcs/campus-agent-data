import unittest
from scripts.topic_contract import topics, category, TOPIC_IDS
from scripts.additional_sources import QUERIES, parse_source
from scripts.international_sources import GLOBAL_SOURCES, parse_public_list

class TopicContractTest(unittest.TestCase):
    def test_stable_multilabel_and_negative(self):
        self.assertEqual(TOPIC_IDS,("scholarships","admissions","teaching","activities"))
        self.assertEqual(topics("博士招生夏令营奖学金"),["scholarships","admissions","activities"])
        self.assertEqual(topics("Graduate funding workshop and course planning"),["scholarships","teaching","activities"])
        self.assertEqual(topics("Annual report / administrative update"),[])
        self.assertEqual(topics("TWiHST · November 20, 2026 - Volume 28, Number 10"),[])
        self.assertEqual(topics("Presidential Graduate Fellowship Program"),["scholarships"])
        self.assertEqual(category("校园体育节活动报名"),"活动")

    def test_real_index_title_and_personal_list_stays_title_only(self):
        # Official public index title and URL, observed from the 2026-11-27 main snapshot.
        spec=next(q for q in QUERIES if q["id"]=="zju-mse-student")
        html="""<a href='/2026/1115/c51031a3227447/page.htm'>关于开展浙江大学材料学院“材暖人心·团聚同行”党团班一体化特色实践活动申报工作</a>
        <a href='/2026/1127/c51031a3229000/page.htm'>校园活动入围名单公示</a>"""
        rows=parse_source(html,spec)
        self.assertEqual(rows[0]["topics"],["activities"])
        self.assertEqual(rows[0]["url"],"https://mse.zju.edu.cn/2026/1115/c51031a3227447/page.htm")
        self.assertTrue(rows[1]["personal_list"])
        self.assertEqual(rows[1]["topics"],["activities"])
        self.assertFalse(rows[1]["content"] or rows[1]["attachments"] or rows[1]["date_candidates"])

    def test_international_reference_and_multiple_labels(self):
        oge=next(q for q in GLOBAL_SOURCES if q["kind"]=="oge")
        rows=parse_public_list('<a href="/fellowships/nsf/">NSF Graduate Research Fellowship Program</a>',oge)
        self.assertEqual(rows[0]["topics"],["scholarships"])
        self.assertIsNone(rows[0]["published_at"])
        self.assertFalse(rows[0]["date_events"])
        sigs=next(q for q in GLOBAL_SOURCES if q["kind"]=="sigs")
        rows=parse_public_list('<a href="/2026/1109/c7770a294243/page.htm">2027年研究生招生夏令营活动通知</a>',sigs)
        self.assertEqual(rows[0]["topics"],["admissions","activities"])
        self.assertFalse(rows[0]["content"])

if __name__=="__main__":unittest.main()
