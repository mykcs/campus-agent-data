"""Public campus-service metadata, not a live timetable or transaction service."""
import argparse
import hashlib
import json
import re
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

if __package__:
    from .international_sources import fetch_public_list
    from .additional_sources import get_row_date
else:
    from international_sources import fetch_public_list
    from additional_sources import get_row_date

SOURCES = (
    dict(id="zju-engineering-shuttles",school="浙江大学",kind="shuttle",name="工程师学院班车公告",url="https://pi.zju.edu.cn/68136/list.htm",host="pi.zju.edu.cn",column="68136",zone="Asia/Singapore",marker="班车信息"),
    dict(id="zju-engineering-procedures",school="浙江大学",kind="documents",name="工程师学院公开办事流程",url="https://pi.zju.edu.cn/67008/list.htm",host="pi.zju.edu.cn",column="67008",zone="Asia/Singapore",marker="办事流程"),
    dict(id="mit-transport-reference",school="MIT",kind="shuttle",name="MIT 官方班车与实时查询入口",url="https://web.mit.edu/facilities/transportation/shuttles/",host="web.mit.edu",zone="America/New_York",marker="Shuttle"),
    dict(id="mit-forms-reference",school="MIT",kind="documents",name="MIT Registrar Forms & Petitions",url="https://registrar.mit.edu/forms",host="registrar.mit.edu",zone="America/New_York",marker="Forms"),
    dict(id="tsinghua-transport-reference",school="清华大学",kind="shuttle",name="清华大学官方校园交通入口",url="https://www.tsinghua.edu.cn/info/1212/81971.htm",host="www.tsinghua.edu.cn",zone="Asia/Singapore",marker="校园交通"),
)

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def valid_date(y,m,d):
    try:return date(int(y),int(m),int(d)).isoformat()
    except (TypeError,ValueError):return None

def title_window(title):
    # Only explicit full-date ranges or a year in the same title plus an
    # explicit "(month/day starts)" clause. Never infer the year from URL.
    full=re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(?:至|—|－|-)\s*(20\d{2})年(\d{1,2})月(\d{1,2})日",title)
    if full:
        a=valid_date(*full.groups()[:3]);b=valid_date(*full.groups()[3:])
        return (a,b) if a and b and a<=b else (None,None)
    year=re.search(r"(20\d{2})年",title)
    start=re.search(r"[（(]\s*(\d{1,2})月(\d{1,2})日开始\s*[）)]",title)
    return (valid_date(year[1],start[1],start[2]),None) if year and start else (None,None)

def service_record(spec,url,title,published_at=None,inferred=False,now=None):
    a,b=title_window(title) if spec["kind"]=="shuttle" else (None,None)
    today=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(spec["zone"])).date().isoformat()
    availability="expired" if b and b<today else "future" if a and a>today else "verify"
    return {"id":hashlib.sha256(url.encode()).hexdigest()[:16],"source_id":spec["id"],"school":spec["school"],"kind":spec["kind"],
        "title":title[:220],"url":url,"published_at":published_at,"date_inferred":inferred,"effective_from":a,"effective_until":b,
        "timezone":spec["zone"],"availability":availability,"detail":"official_reference_only"}

def allowed(url,spec):
    try:
        u=urlsplit(url)
        if u.scheme!="https" or u.hostname!=spec["host"] or u.username or u.password or u.port or u.query or u.fragment:return False
        if "column" not in spec:return url==spec["url"]
        return bool(re.fullmatch(r"/20\d{2}/\d{4}/c"+spec["column"]+r"a\d+/page\.htm",u.path))
    except (TypeError,ValueError):return False

def parse(html,spec,now=None):
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    if spec["marker"] not in text:raise ValueError("public source marker absent")
    if "column" not in spec:
        return [service_record(spec,spec["url"],spec["name"],now=now)]
    out={}
    for a in soup.select("a[href]"):
        url=urljoin(spec["url"],a.get("href",""))
        if not allowed(url,spec) or url in out:continue
        title=" ".join((a.get("title") or a.get_text(" ",strip=True)).split())
        if len(title)<6:continue
        day,inferred=get_row_date(a,url)
        if day:
            try:day=date.fromisoformat(day).isoformat()
            except ValueError:day=None;inferred=False
        out[url]=service_record(spec,url,title,day,inferred,now)
        if len(out)>=20:break
    if not out:raise ValueError("no allowed public entries")
    return list(out.values())

def collect(previous=None,fetcher=fetch_public_list):
    previous=previous or {}
    records=[];sources=[]
    for spec in SOURCES:
        at=utc_now()
        old=next((s for s in previous.get("sources",[]) if s.get("id")==spec["id"]),{})
        try:
            rows=parse(fetcher(spec["url"],spec),spec)
            records.extend(rows);state="partial";success=utc_now()
        except Exception:
            rows=[{**r,"availability":"verify","stale":True} for r in previous.get("services",[]) if r.get("source_id")==spec["id"] and allowed(r.get("url"),spec)]
            records.extend(rows);state="error";success=old.get("last_success_at")
        sources.append({"id":spec["id"],"school":spec["school"],"kind":spec["kind"],"name":spec["name"],"url":spec["url"],
            "status":state,"count":len(rows),"last_checked_at":at,"last_success_at":success})
    return {"version":1,"checked_at":utc_now(),"status":"degraded" if any(s["status"]=="error" for s in sources) else "healthy",
            "sources":sources,"services":records,"limitations":"Public metadata and official reference links only; current timetable, access eligibility and form validity require checking the official page."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    old={}
    if args.output.exists():old=json.loads(args.output.read_text(encoding="utf-8"))
    result=collect(old)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    temp=args.output.with_suffix(".tmp")
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({"checked_at":result["checked_at"],"status":result["status"],"records":len(result["services"]),"sources":[[s["id"],s["count"],s["status"]] for s in result["sources"]]}))
    return 0 if result["status"]=="healthy" else 2

if __name__=="__main__":raise SystemExit(main())
