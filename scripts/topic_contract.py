"""Stable public title-only, multi-label topic contract (Issue #11).

A topic is a discovery hint, not an open application, eligibility decision,
or verified event date. Sources may contribute an explicit scope label.
"""
import re

TOPIC_IDS = ("scholarships", "admissions", "teaching", "activities")
SCHOLARSHIP = re.compile(r"奖学金|助学金|奖助|资助|评奖|助学|经济困难|励志奖|外设奖|\b(?:fellowships?|scholarships?|financial aid|student funding|graduate funding|grants?)\b", re.I)
ADMISSIONS = re.compile(r"博士|硕士|招生|推免|申请考核|夏令营|\b(?:admissions?|doctoral application|graduate application|application for admission)\b", re.I)
TEACHING = re.compile(r"课程|调课|教学|培养|考试安排|\b(?:course(?:s|work)?|teaching|class schedule|exam schedule)\b", re.I)
ACTIVITY = re.compile(r"活动|讲座|论坛|研讨会|交流会|报告会|学术报告|开放日|夏令营|冬令营|竞赛|比赛|运动会|体育节|志愿服务|工作坊|\b(?:workshops?|seminars?|lectures?|symposi(?:um|a)|forums?|open house|summer camp|winter camp|competitions?|volunteer event|campus event|student event)\b", re.I)
RULES = (SCHOLARSHIP, ADMISSIONS, TEACHING, ACTIVITY)

def topics(title: str, explicit=()) -> list[str]:
    """Keep original stable IDs; allow overlapping labels and no classification."""
    if not isinstance(title, str):
        title = ""
    return [name for name, rule in zip(TOPIC_IDS, RULES)
            if name in explicit or rule.search(title)]

def category(title: str) -> str:
    tags = topics(title)
    if "scholarships" in tags:return "奖助"
    if "博士" in title:return "博士招生"
    if "admissions" in tags:return "招生"
    if "teaching" in tags:return "教学"
    if "activities" in tags:return "活动"
    return "通知"
