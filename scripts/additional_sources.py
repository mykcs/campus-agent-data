"""Public-only auxiliary sources for Campus Agent.

University-wide search is not an official per-department feed: mark it partial.
Never download member rosters, private documents or login-required resources.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ARTICLE = re.compile(r"/20\d{2}/\d{4}/c\d+a\d+/(?:page|pagem)\.htm$", re.I)
DATE = re.compile(r"20\d{2}[-./]\d{1,2}[-./]\d{1,2}")
PUBLISHED = re.compile(r"发布时间[:：]?\s*(20\d{2}[-./]\d{1,2}[-./]\d{1,2})")
PRIVATE_LIST = re.compile(r"名单|公示|拟录取|入围|评选结果|导师资格目录")
SCHOLARSHIP = re.compile(r"奖学金|助学金|奖助|资助|评奖|助学|经济困难|励志奖|外设奖")
ADMISSIONS = re.compile(r"博士|硕士|招生|推免|申请考核|夏令营")
TEACHING = re.compile(r"课程|调课|教学|培养|考试安排")
HEADERS = {"User-Agent": "CampusAgentPublicNotices/0.2 (+https://github.com/mykcs/campus-agent-data)",
           "Accept": "text/html,application/xhtml+xml"}
QUERIES = [
    {
        "id":"zju-cs-search", "department_id":"zju-cs", "name":"计算机学院 · 校级公开搜索",
        "url":"https://s2.zju.edu.cn/search/info.do?words="+quote("计算机科学与技术学院"),
        "status":"partial", "host":"cs.zju.edu.cn", "kind":"search",
        "note":"浙江大学校级搜索提供的部分结果，不代表学院全部通知"
    },
    {
        "id":"zju-software-search", "department_id":"zju-software", "name":"软件学院 · 校级公开搜索",
        "url":"https://s2.zju.edu.cn/search/info.do?words="+quote("软件学院"),
        "status":"partial", "host":"cst.zju.edu.cn", "kind":"search",
        "note":"浙江大学校级搜索提供的部分结果，不代表学院全部通知"
    },
    {
        "id":"zju-scholarships-search", "department_id":"zju-other", "name":"全校奖学金 · 校级公开搜索",
        "url":"https://s2.zju.edu.cn/search/info.do?words="+quote("奖学金"),
        "status":"partial", "host":None, "kind":"search",
        "note":"仅是校级公开关键词搜索的部分结果，并非全校奖助公告清单"
    },
    {
        "id":"zju-mse-student", "department_id":"zju-mse", "name":"材料学院 · 公开学生事务",
        "url":"https://mse.zju.edu.cn/51031/list.htm",
        "status":"ok", "host":"mse.zju.edu.cn", "kind":"list",
        "note":"学院公开学生事务栏目"
    },
    {
        "id":"zju-history-aid", "department_id":"zju-history",
        "name":"历史学院 · 学生资助公开栏", "department":"历史学院",
        "url":"https://ls.zju.edu.cn/65208/list.htm",
        "status":"ok", "host":"ls.zju.edu.cn", "kind":"list",
        "force_scholarship_topic":True,
        "note":"只覆盖历史学院公开学生资助栏目，不能代表全校奖学金"
    },
    {
        "id":"zju-engineering-aid", "department_id":"zju-engineering",
        "name":"工程师学院 · 奖助通知公开栏", "department":"工程师学院",
        "url":"https://pi.zju.edu.cn/67027/list.htm",
        "status":"partial", "host":"pi.zju.edu.cn", "kind":"list",
        "scholarships_only":True,
        "note":"从工程师学院公开学生工作栏目仅筛选标题含奖助关键词的通知"
    }
]

def official(url: str) -> bool:
    try:
        u=urlparse(url)
        return (u.scheme in ("http","https") and
                (u.hostname=="zju.edu.cn" or u.hostname.endswith(".zju.edu.cn")) and
                not u.username and not u.password and bool(ARTICLE.search(u.path)))
    except Exception:
        return False

def fetch_public_html(url: str) -> str:
    u=urlparse(url)
    # The source list is a fixed allowlist; no arbitrary user-supplied URLs.
    if u.scheme!="https" or u.hostname not in {"s2.zju.edu.cn","mse.zju.edu.cn","ls.zju.edu.cn","pi.zju.edu.cn"}:
        raise ValueError("Public-source allowlist violation")
    with urlopen(Request(url,headers=HEADERS),timeout=20) as res:
        if res.url!=url:
            actual=urlparse(res.url)
            if actual.scheme!="https" or actual.hostname not in {"s2.zju.edu.cn","mse.zju.edu.cn","ls.zju.edu.cn","pi.zju.edu.cn"}:
                raise ValueError("Unexpected external redirect")
        data=res.read(1_200_001)
    if len(data)>1_200_000:
        raise ValueError("Oversized notice list")
    return data.decode("utf-8","replace")

def clean_title(text: str) -> str:
    text=" ".join(text.split())
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])","",text)

def date_from_url(url: str) -> str|None:
    m=re.search(r"/(20\d{2})/(\d{2})(\d{2})/",url)
    if not m:return None
    try:
        return datetime(int(m[1]),int(m[2]),int(m[3])).date().isoformat()
    except ValueError:
        return None

def get_row_date(a, url: str) -> tuple[str|None,bool]:
    """Only trust a date within the current item, never from sibling notices."""
    path_day = date_from_url(url)
    # Some CMS sites put the publication date inside the notice link. Only
    # accept that date when it agrees with this article\'s dated URL path.
    suffix = DATE.search(a.get_text(" ",strip=True)[-24:])
    if suffix and path_day and suffix.group().replace(".","-").replace("/","-") == path_day:
        return path_day, False
    node=a
    for depth in range(5):
        node=node.parent
        if not node:
            break
        # A common parent with multiple articles is a list, not this article
        # row; its first date belongs to another notice. Fall back to URL.
        article_link_count=sum(
            bool(ARTICLE.search(urlparse(href.get("href","")).path))
            for href in node.select("a[href]")
        )
        if article_link_count>1:
            break
        txt=node.get_text(" ",strip=True)
        if len(txt)>3000:
            break
        m=PUBLISHED.search(txt)
        if m:
            return m.group(1).replace(".","-").replace("/","-"),False
        # List pages sometimes display dates in an immediate row without
        # "发布时间"; only trust them when that row contains one article.
        if depth>=1 and len(txt)<850:
            m=DATE.search(txt)
            if m:
                return m.group().replace(".","-").replace("/","-"),False
    return date_from_url(url),True

def topics(title: str) -> list[str]:
    ids=[]
    if SCHOLARSHIP.search(title):ids.append("scholarships")
    if ADMISSIONS.search(title):ids.append("admissions")
    if TEACHING.search(title):ids.append("teaching")
    return ids

def category(title: str) -> str:
    if SCHOLARSHIP.search(title):return "奖助"
    if "博士" in title:return "博士招生"
    if ADMISSIONS.search(title):return "招生"
    if TEACHING.search(title):return "教学"
    return "通知"

def parse_source(html: str, config: dict) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    items=[]
    seen=set()
    for a in soup.select("a[href]"):
        link=urljoin(config["url"],a.get("href",""))
        if not official(link) or link in seen:
            continue
        parsed_host = (urlparse(link).hostname or "")
        permitted_host = config.get("host")
        if permitted_host and not (parsed_host == permitted_host or parsed_host.endswith("." + permitted_host)):
            continue
        title=clean_title(a.get("title") or a.get_text(" ",strip=True))
        # The History School template appends publication date inside the link;
        # strip only a trailing ISO-style date, not dates mentioned in titles.
        title = re.sub(r"\s+20\d{2}[-./]\d{2}[-./]\d{2}$", "", title)
        if len(title)<8:
            continue
        if (config["id"]=="zju-scholarships-search" or config.get("scholarships_only")) and not SCHOLARSHIP.search(title):
            continue
        # Only store links and short titles from the university-wide search,
        # never body excerpts or student lists.
        date,estimated=get_row_date(a,link)
        seen.add(link)
        items.append({
            "id":hashlib.sha256(link.encode("utf-8")).hexdigest()[:16],
            "url":link,
            "title":title[:190],
            "school":"浙江大学",
            "department":config.get("department") or {
                "zju-cs-search":"计算机科学与技术学院",
                "zju-software-search":"软件学院",
                "zju-scholarships-search":"校级公开奖学金索引",
                "zju-mse-student":"材料科学与工程学院",
            }[config["id"]],
            "department_id":config["department_id"],
            "source_id":config["id"],
            "category":category(title),
            "topics":sorted(set(topics(title) + (["scholarships"] if config.get("force_scholarship_topic") else []))),
            "published_at":date,
            "date_inferred":estimated,
            "excerpt":"仅提供官方标题与原文入口；请打开学校官网核对要求。",
            "content":"",
            "attachments":[],
            "date_candidates":[],
            "personal_list":bool(PRIVATE_LIST.search(title)),
        })
        if len(items)>=20:break
    return items

def collect_additional(previous: dict|None=None) -> tuple[list[dict],list[dict],list[str]]:
    previous=previous or {}
    prior={x.get("id"):x for x in previous.get("notices",[]) if isinstance(x,dict)}
    notices=[]
    sources=[]
    errors=[]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    for spec in QUERIES:
        source_id=spec["id"]
        try:
            rows=parse_source(fetch_public_html(spec["url"]),spec)
            if not rows:
                raise ValueError("No verified public article URLs in this source")
            notices.extend(rows)
            sources.append({
                "id":source_id,"name":spec["name"],"url":spec["url"],
                "status":spec["status"],"note":spec["note"],
                "count":len(rows),"last_checked_at":now,"last_success_at":now
            })
        except Exception as exc:
            cached=[x for x in prior.values() if x.get("source_id")==source_id]
            # Cached records may be stale but should not disappear silently.
            for x in cached:
                if official(x.get("url","")):
                    y=dict(x)
                    y["stale"]=True
                    notices.append(y)
            sources.append({
                "id":source_id,"name":spec["name"],"url":spec["url"],
                "status":"error","note":spec["note"],
                "count":len(cached),"last_checked_at":now,
                "last_success_at":next((s.get("last_success_at") for s in previous.get("sources",[]) if s.get("id")==source_id),None),
            })
            errors.append(source_id+": "+type(exc).__name__+": "+str(exc)[:120])
    return notices,sources,errors
