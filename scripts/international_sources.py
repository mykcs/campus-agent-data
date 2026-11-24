"""Fixed, public-only university adapters. Never download article bodies."""
from datetime import date, datetime
import hashlib
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from bs4 import BeautifulSoup

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
        records[url] = {
            "id": hashlib.sha256(url.encode()).hexdigest()[:16],
            "url":url, "title":title[:190], "school":spec["school"],
            "department":spec["department"], "department_id":spec["department_id"],
            "source_id":spec["id"], "category":"奖助" if spec["kind"]=="oge" else "通知",
            "topics":["scholarships"] if spec["kind"]=="oge" else [],
            "published_at":published, "date_inferred":False, "timezone":spec["timezone"],
            "excerpt":"仅提供学校公开原文入口；申请日期与适用条件须核对原文。",
            "content":"", "attachments":[], "date_candidates":[], "date_events":[],
            "personal_list":False,
        }
        if len(records)>=15:
            break
    return list(records.values())
