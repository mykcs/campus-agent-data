#!/usr/bin/env python3
"""Read publicly accessible ZJU AI admissions notices; never access authenticated pages."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

SOURCE_ID = "zju-ai-admissions"
BASE = "https://ai.zju.edu.cn"
SOURCE_URL = f"{BASE}/zstz/list1.htm"
INDEX_PAGES = [SOURCE_URL, f"{BASE}/zstz/list2.htm"]
ARTICLE_PATH = re.compile(r"^/\d{4}/\d{4}/c\d+a\d+/page\.htm$")
DAY = re.compile(r"20\d{2}-\d{2}-\d{2}")
CHINESE_DATE = re.compile(
    r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
    r"(?:\s*(\d{1,2})\s*[:：]\s*(\d{2}))?"
)
DEADLINE_HINT = re.compile(r"报名|截止|递交|提交|寄出|邮寄|材料|申请|上传|网报|考核")
ATTACHMENT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip)(?:$|[?#])", re.I)
HEADERS = {
    "User-Agent": "CampusAgentPublicNotices/0.1 (+https://github.com/mykcs/campus-agent-data)",
    "Accept": "text/html,application/xhtml+xml",
}

def fetch_html(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "ai.zju.edu.cn":
        raise ValueError("Unexpected host; only public ai.zju.edu.cn pages are allowed")
    with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
        data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError("HTML page too large")
        return data.decode("utf-8", "replace")

def parse_index(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    found = []
    seen = set()
    for a in soup.select("a[href]"):
        path = urlparse(a.get("href", "")).path
        if not ARTICLE_PATH.fullmatch(path):
            continue
        url = urljoin(BASE, path)
        if url in seen:
            continue
        title = a.get("title") or a.get_text(" ", strip=True)
        if len(title.strip()) < 6:
            continue
        parent = a.find_parent("div", class_=lambda v: v and "group" in str(v).split())
        date_match = DAY.search(parent.get_text(" ", strip=True)) if parent else None
        seen.add(url)
        found.append({
            "id": hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
            "url": url,
            "title": " ".join(title.split()),
            "published_at": date_match.group() if date_match else None,
        })
    return found

def extract_dates(text: str) -> list[dict]:
    """Candidate dates, not claims of eligibility or definitive deadlines."""
    candidates = []
    seen = set()
    for m in CHINESE_DATE.finditer(text):
        before = text[max(0, m.start()-82):m.start()]
        after = text[m.end():m.end()+64]
        if not DEADLINE_HINT.search(before[-45:] + after[:35]):
            continue
        try:
            date = datetime(int(m[1]), int(m[2]), int(m[3])).date().isoformat()
        except ValueError:
            continue
        value = date + (f"T{int(m[4]):02}:{int(m[5]):02}" if m[4] else "")
        if value in seen:
            continue
        seen.add(value)
        context = (before[-55:] + m.group() + after[:45]).strip()
        candidates.append({"value": value, "context": context[:135], "verified": False})
        if len(candidates) >= 10:
            break
    return candidates

def article_data(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".wp_articlecontent")
    if body is None:
        raise ValueError("Expected public article body was not found")
    full_text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
    if len(full_text) < 8:
        return {
            "excerpt": "官方网页没有可提取的文字正文，请打开官方原文核对。",
            "content": "",
            "content_sha256": hashlib.sha256(full_text.encode()).hexdigest(),
            "attachments": [], "date_candidates": [], "text_unavailable": True,
        }
    files = []
    urls = set()
    for anchor in body.select("a[href]"):
        link = urljoin(url, anchor.get("href", ""))
        parsed = urlparse(link)
        if parsed.scheme != "https" or not parsed.hostname or not ATTACHMENT.search(parsed.path):
            continue
        if link in urls:
            continue
        urls.add(link)
        files.append({
            "title": (anchor.get_text(" ", strip=True) or parsed.path.split("/")[-1])[:100],
            "url": link,
        })
    return {
        "excerpt": full_text[:420],
        "content": full_text[:14000],
        "content_sha256": hashlib.sha256(full_text.encode()).hexdigest(),
        "attachments": files[:25],
        "date_candidates": extract_dates(full_text),
    }

def classify(title: str) -> str:
    for word, tag in [
        ("奖学金", "奖助"), ("资助", "奖助"), ("博士", "博士招生"),
        ("推免", "推免"), ("硕士", "硕士招生"), ("公示", "公示"),
    ]:
        if word in title:
            return tag
    return "招生通知"

def collect(previous: dict | None = None, delay: float = 0.6) -> dict:
    entries = []
    seen = set()
    errors = []
    for index in INDEX_PAGES:
        try:
            for item in parse_index(fetch_html(index)):
                if item["id"] not in seen:
                    entries.append(item)
                    seen.add(item["id"])
        except Exception as exc:
            errors.append(f"Index {index}: {type(exc).__name__}: {exc}")
    if len(entries) < 3:
        raise RuntimeError(f"Index returned only {len(entries)} articles; refuse to overwrite data. {errors}")
    previous_items = {
        x["id"]: x for x in (previous or {}).get("notices", [])
        if isinstance(x, dict) and isinstance(x.get("id"), str)
    }
    notices = []
    for item in entries[:30]:
        try:
            details = article_data(fetch_html(item["url"]), item["url"])
            item.update(details)
        except Exception as exc:
            if item["id"] in previous_items:
                details = {
                    k: previous_items[item["id"]].get(k)
                    for k in ("excerpt", "content", "content_sha256", "attachments", "date_candidates")
                }
                item.update(details)
            else:
                errors.append(f"Article {item['url']}: {type(exc).__name__}: {exc}")
                continue
            errors.append(f"Stale cached article {item['url']}: {type(exc).__name__}: {exc}")
        item["school"] = "浙江大学"
        item["department"] = "人工智能学院"
        item["category"] = classify(item["title"])
        item["source_id"] = SOURCE_ID
        notices.append(item)
        time.sleep(delay)
    if len(notices) < 3:
        raise RuntimeError(f"Only {len(notices)} readable articles; refuse to overwrite")
    notices.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "version": 1,
        "checked_at": checked_at,
        "timezone": "Asia/Shanghai",
        "sources": [{
            "id": SOURCE_ID,
            "name": "浙江大学人工智能学院 · 招生通知",
            "url": SOURCE_URL,
            "last_checked_at": checked_at,
            "status": "degraded" if errors else "ok",
            "count": len(notices),
        }],
        "notices": notices,
        "errors": errors[:20],
        "limitations": [
            "仅覆盖浙江大学人工智能学院公开招生通知栏目，不能证明全校通知完整。",
            "日期为规则抽取候选，需结合官方原文核对适用报名类别。",
            "无须登录的公开网页可能改版、暂时不可用或撤稿。",
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/notices.json")
    parser.add_argument("--fast", action="store_true", help="Use only for local verification")
    args = parser.parse_args()
    out = Path(args.output)
    old = None
    if out.exists():
        try:
            old = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            pass
    snapshot = collect(previous=old, delay=0 if args.fast else 0.6)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "notice_count": len(snapshot["notices"]),
        "checked_at": snapshot["checked_at"],
        "status": snapshot["sources"][0]["status"],
        "errors": snapshot["errors"][:2],
    }, ensure_ascii=False))
    return 0 if not snapshot["errors"] else 2

if __name__ == "__main__":
    sys.exit(main())
