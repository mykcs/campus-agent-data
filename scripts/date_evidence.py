"""Conservative public date evidence. Never an eligibility or task decision."""
from __future__ import annotations

from datetime import date
import re

# Full dates and yearless clues; do not guess a year from publication time.
DATE = re.compile(
    r"(?<!\d)(?:(?P<year>20\d{2})\s*年\s*)?"
    r"(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*日"
    r"(?:\s*(?P<hour>\d{1,2})\s*[:：]\s*(?P<minute>\d{2})(?!\d))?"
)
BOUNDARY = re.compile(r"[。；;！？\n，,]")
ACTION = re.compile(r"报名|申请|提交|递交|材料|上传|网申|网报|截止|开始|邮戳|邮寄|推荐|考核")
RANGE = re.compile(r"\s*(?:[-—–－~～]|至|到)\s*")
OPEN = re.compile(r"(?:开始|起始|开放)(?:时间|日期)?(?:为|是|[:：])?\s*$")
CLOSE = re.compile(r"(?:截止|截至|最迟)(?:时间|日期)?(?:为|是|到|至|[:：])?\s*$")
TZ = re.compile(r"^\s*(?:[（(]\s*)?(UTC(?:[+-]\d{2}:\d{2})?|SGT)(?![A-Za-z0-9:+-])")


def _parts(text, match):
    start = max(0, match.start() - 100)
    stop = min(len(text), match.end() + 100)
    left = BOUNDARY.split(text[start:match.start()])[-1].strip()
    right = BOUNDARY.split(text[match.end():stop])[0].strip()
    return left, right


def _classify(left, right):
    # Use only the adjacent clause, not a neighbouring applicant's deadline.
    if re.search(r"邮戳(?:日期|时间)?(?:为|以|截至|[:：])?\s*$", left) or re.match(r"(?:前|之前)?\s*邮戳(?:为准)?", right):
        return "postmark"
    if re.search(r"推荐(?:材料)?(?:截止|截至)(?:时间|日期)?(?:为|[:：])?\s*$", left):
        return "recommendation"
    if re.search(r"(?:院系|学院|校内|内部).{0,12}(?:截止|截至)(?:时间|日期)?(?:为|[:：])?\s*$", left):
        return "internal"
    if OPEN.search(left) or re.match(r"^(?:开始|开放|起\b)", right):
        return "open"
    if CLOSE.search(left) or re.match(r"^(?:报名|申请|提交)?截止(?:时间|后|前|$)", right):
        return "close"
    if ACTION.search(left) and re.match(r"^(?:之前|前)\s*(?:完成|提交|上传|递交|报名|申请)", right):
        return "close"
    return "unknown"


def _scope(left):
    # Preserve a literal adjacent heading, never infer an applicant's identity.
    match = re.search(r"([^：:]{1,80})[:：]\s*$", left)
    if not match:
        return None
    label = match.group(1).strip()
    if ACTION.search(label) and not DATE.search(label):
        return label
    return None


def _value(match):
    year, month, day = match.group("year", "month", "day")
    hour, minute = match.group("hour", "minute")
    # The leap year 2000 is used only to validate a yearless month/day.
    try:
        value = date(int(year) if year else 2000, int(month), int(day))
    except ValueError:
        return None, "invalid_date"
    if hour is not None and not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
        return None, "unresolved_time"
    if not year:
        return None, "missing_year"
    return (value.isoformat() + (f"T{int(hour):02}:{int(minute):02}" if hour is not None else ""), "explicit")


def extract_date_events(text: str, source_url: str) -> list[dict]:
    """Extract bounded literal clues; no inferred year, timezone or eligibility.

    Multiple occurrences of the same date are kept separate. Range semantics
    apply only to adjacent dates within a labelled application window.
    """
    matches = list(DATE.finditer(text))
    parts = [_parts(text, match) for match in matches]
    roles = {}
    scopes = {}
    for i in range(len(matches) - 1):
        first, second = matches[i:i+2]
        left, _ = parts[i]
        gap = text[first.end():second.start()]
        if RANGE.fullmatch(gap) and re.search(r"报名|申请|网报|网申", left[-80:]):
            roles[i], roles[i+1] = "open", "close"
            scopes[i] = scopes[i+1] = _scope(left)

    events = []
    for i, match in enumerate(matches):
        left, right = parts[i]
        if i not in roles and not ACTION.search(left[-50:] + " " + right[:40]):
            continue
        kind = roles.get(i, _classify(left, right))
        value, resolution = _value(match)
        # Store only a small adjacent quote and the official page URL.
        tz_match = TZ.match(text[match.end():match.end()+35])
        events.append({
            "type": kind,
            "value": value,
            "raw": match.group(0).strip(),
            "resolution": resolution,
            "has_time": match.group("hour") is not None,
            "timezone": tz_match.group(1) if tz_match else None,
            "scope_text": scopes.get(i, _scope(left)),
            "context": (left[-55:] + " " + match.group(0) + " " + right[:45]).strip()[:135],
            "source_url": source_url,
            "verified": False,
        })
        if len(events) >= 20:
            break
    return events
