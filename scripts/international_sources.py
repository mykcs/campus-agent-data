"""Fixed, public-only university adapters. Never download article bodies."""
from datetime import date, datetime
import hashlib
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from bs4 import BeautifulSoup

if __package__:
    from .topic_contract import topics, category
else:
    from topic_contract import topics, category

GLOBAL_SOURCES = [
    dict(id="mit-hst-bulletin", school="MIT", department="Harvard-MIT Health Sciences and Technology",
         department_id="mit-hst", name="MIT HST · TWiHST 公共通讯",
         url="https://hst.mit.edu/news-events/twihst", host="hst.mit.edu",
         timezone="America/New_York", status="partial", kind="hst",
         note="Only recent dated issues from the public HST archive; individual opportunities require opening the original newsletter."),
    dict(id="mit-oge-funding", school="MIT", department="Office of Graduate Education",
         department_id="mit-oge", name="MIT OGE · 研究生资助官方入口",
         url="https://oge.mit.edu/fellowships/", host="oge.mit.edu",
         timezone="America/New_York", status="partial", kind="oge",
         note="Public funding reference pages; no publication date or open-application status is assumed."),
    dict(id="tsinghua-sigs-admissions", school="清华大学", department="深圳国际研究生院",
         department_id="tsinghua-sigs", name="清华大学深圳国际研究生院 · 招生公告",
         url="https://www.sigs.tsinghua.edu.cn/_s3/7770/list.psp", host="www.sigs.tsinghua.edu.cn",
         timezone="Asia/Singapore", status="partial", kind="sigs",
         note="Only the recent public admissions list, not all Tsinghua departments."),
]
OGE_PATHS = {
    "/fellowships/oge-fellowships-and-awards/",
    "/fellowships/presidential-graduate-fellowship-program/",
    "/fellowships/hugh-hampton-young-fellowship/",
    "/fellowships/nsf/",
    "/fellowships/external-fellowships/",
}
HST = re.compile(r"^/news-events/twihst/volume-\d+-number-\d+/?$")
EN_DATE = re.compile(r"^([A-Za-z]+ \d{1,2}, 20\d{2})\s*-\s*Volume \d+, Number \d+$")
MONTHS = {name: n for n,name in enumerate(("January","February","March","April","May","June","July","August","September","October","November","December"),1)}


def allowed_article(url, spec):
    try:
        u = urlsplit(url)
        if u.scheme != "https" or u.hostname != spec["host"] or u.username or u.password or u.port or u.query or u.fragment:
            return False
        if spec["kind"] == "hst":
            return bool(HST.fullmatch(u.path))
        if spec["kind"] == "oge":
            return u.path in OGE_PATHS
        if spec["kind"] == "sigs":
            return bool(re.fullmatch(r"/20\d{2}/\d{4}/c7770a\d+/page\.htm",u.path))
        return False
    except (ValueError, TypeError):
        return False


def fetch_public_list(url, spec):
    # Only the configured list can be requested; redirects must stay on its
    # exact public host and path. Do not follow login or external redirects.
    if url != spec["url"]:
        raise ValueError("Unregistered public list URL")
    class SameList(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if newurl.rstrip("/") != url.rstrip("/"):
                raise ValueError("Unapproved public-list redirect")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    with build_opener(SameList()).open(Request(url, headers={"User-Agent":"CampusAgentPublicNotices/0.3 (+https://github.com/mykcs/campus-agent-data)","Accept":"text/html"}), timeout=20) as response:
        data = response.read(1_200_001)
    if len(data) > 1_200_000:
        raise ValueError("Oversized public list")
    return data.decode("utf-8", "replace")


def parse_public_list(html, spec):
    soup = BeautifulSoup(html, "html.parser")
    records = {}
    for a in soup.select("a[href]"):
        url = urljoin(spec["url"], a.get("href",""))
        if not allowed_article(url, spec) or url in records:
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        if len(title) < 8:
            continue
        published = None
        inferred = False
        if spec["kind"] == "hst":
            m = EN_DATE.fullmatch(title)
            if not m:
                continue
            try:
                month, day, year = m.group(1).replace(",","").split()
                published = date(int(year), MONTHS[month], int(day)).isoformat()
            except (ValueError, KeyError):
                continue
            title = "TWiHST · " + title
        elif spec["kind"] == "oge":
            if title.lower() in {"learn more", "read more"}:
                continue
        elif spec["kind"] == "sigs":
            # Read the date only from a row containing this exact article;
            # a link to the same article may occur more than once in that row.
            for node in list(a.parents)[:4]:
                links = {urljoin(spec["url"], l.get("href","")) for l in node.select("a[href]")}
                if len({link for link in links if allowed_article(link,spec)}) > 1:
                    break
                matches = set(re.findall(r"20\d{2}-\d{2}-\d{2}",node.get_text(" ",strip=True)))
                if len(matches)==1:
                    try:
                        published = date.fromisoformat(matches.pop()).isoformat()
                    except ValueError:
                        pass
                    if published:
                        break
            if not published:
                m = re.match(r"/(20\d{2})/(\d{2})(\d{2})/",urlsplit(url).path)
                try:
                    published = date(*map(int,m.groups())).isoformat()
                    inferred = True
                except (ValueError, AttributeError):
                    continue
        forced = ("scholarships",) if spec["kind"]=="oge" else ("admissions",) if spec["kind"]=="sigs" else ()
        tags = topics(title, forced)
        records[url] = {
            "id": hashlib.sha256(url.encode()).hexdigest()[:16],
            "url":url, "title":title[:190], "school":spec["school"],
            "department":spec["department"], "department_id":spec["department_id"],
            "source_id":spec["id"], "category":"奖助" if spec["kind"]=="oge" else "招生" if spec["kind"]=="sigs" else category(title),
            "topics":tags,
            "published_at":published, "date_inferred":inferred, "timezone":spec["timezone"],
            "excerpt":"仅提供学校公开原文入口；申请日期与适用条件须核对原文。",
            "content":"", "attachments":[], "date_candidates":[], "date_events":[],
            "personal_list":False,
        }
        if len(records)>=15:
            break
    return list(records.values())
