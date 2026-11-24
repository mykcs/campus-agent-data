"""Fail-closed, credential-free health receipts for public notice collection.

The check history is public and limited to source identifiers, statuses, counts,
timestamps and stable failure codes. No user data or raw request errors.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MAX_CHECKS = 120
VALID_STATES = {"ok", "partial", "degraded", "error"}
UNHEALTHY_STATES = {"degraded", "error"}
STALE_SNAPSHOT_HOURS = 6


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def assess_snapshot(current: dict, previous: dict | None = None) -> dict:
    """Evaluate data quality without modifying current/previous snapshots."""
    previous = previous or {}
    issues: list[dict] = []
    rows = current.get("notices", [])
    sources = current.get("sources", [])
    if not isinstance(rows, list) or not isinstance(sources, list) or not sources:
        issues.append({"code": "invalid_snapshot", "source_id": "*", "severity": "fatal"})
        return {"status": "failed", "issues": issues}

    if len(rows) < 3:
        issues.append({"code": "too_few_notices", "source_id": "*", "severity": "fatal"})

    source_ids: set[str] = set()
    record_ids: set[str] = set()
    counted: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            issues.append({"code": "invalid_notice_record", "source_id": "*", "severity": "fatal"})
            continue
        rid = row["id"]
        if rid in record_ids:
            issues.append({"code": "duplicate_notice_id", "source_id": "*", "severity": "fatal"})
        record_ids.add(rid)
        source_id = row.get("source_id")
        if isinstance(source_id, str) and source_id:
            counted[source_id] = counted.get(source_id, 0) + 1
        else:
            issues.append({"code": "notice_source_missing", "source_id": "*", "severity": "fatal"})

    prev_sources = {
        row["id"]: row for row in previous.get("sources", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    for src in sources:
        if not isinstance(src, dict) or not isinstance(src.get("id"), str):
            issues.append({"code": "invalid_source", "source_id": "*", "severity": "fatal"})
            continue
        sid = src["id"]
        if sid in source_ids:
            issues.append({"code": "duplicate_source", "source_id": sid, "severity": "fatal"})
        source_ids.add(sid)
        status = src.get("status")
        if status not in VALID_STATES:
            issues.append({"code": "unknown_source_status", "source_id": sid, "severity": "fatal"})
            continue
        if status in UNHEALTHY_STATES:
            issues.append({"code": "source_read_failed", "source_id": sid, "severity": "warning"})
        last_check = parse_utc(src.get("last_checked_at"))
        last_success = parse_utc(src.get("last_success_at"))
        if last_check is None:
            issues.append({"code": "source_check_time_missing", "source_id": sid, "severity": "warning"})
        if status in {"ok", "partial"} and last_success is None:
            issues.append({"code": "source_success_time_missing", "source_id": sid, "severity": "fatal"})
        if last_check and last_success and last_success > last_check:
            issues.append({"code": "future_success_time", "source_id": sid, "severity": "fatal"})
        old = prev_sources.get(sid, {})
        old_success = parse_utc(old.get("last_success_at"))
        if status in UNHEALTHY_STATES and old_success and last_success and last_success > old_success:
            issues.append({"code": "failed_source_advanced_success_time", "source_id": sid, "severity": "fatal"})
        current_count = counted.get(sid, 0)
        declared = src.get("count")
        # Published notices are de-duplicated across overlapping source feeds;
        # a source may have discovered more URLs than it owns after merging.
        if not isinstance(declared, int) or declared < current_count or declared < 0:
            issues.append({"code": "source_count_mismatch", "source_id": sid, "severity": "warning"})
        previous_count = sum(
            n.get("source_id") == sid for n in previous.get("notices", [])
            if isinstance(n, dict)
        )
        # A major drop could indicate a replaced/shortened index. Stop publishing
        # rather than silently erasing prior public notices. This is a review
        # trigger, not a claim that the removed entries should stay public forever.
        if status in {"ok", "partial"} and previous_count >= 8 and current_count * 2 < previous_count:
            issues.append({
                "code": "suspicious_source_drop",
                "source_id": sid,
                "severity": "fatal",
                "before": previous_count,
                "after": current_count,
            })

    # Every published notice must be attributable to a registered source.
    # Do not echo unexpected IDs into the public health receipt.
    if set(counted) - source_ids:
        issues.append({"code": "notice_source_unknown", "source_id": "*", "severity": "fatal"})

    missing = set(prev_sources) - source_ids
    for sid in sorted(missing):
        issues.append({"code": "source_disappeared", "source_id": sid, "severity": "fatal"})

    if current.get("errors"):
        issues.append({"code": "collector_reported_errors", "source_id": "*", "severity": "warning"})

    if any(i["severity"] == "fatal" for i in issues):
        state = "failed"
    elif issues:
        state = "degraded"
    else:
        state = "healthy"
    return {"status": state, "issues": issues}


def receipt(
    status: str, *, current: dict | None, issues: list[dict],
    attempted_at: str | None = None
) -> dict:
    if status not in {"healthy", "degraded", "failed"}:
        raise ValueError("Unknown health status")
    out = {
        "attempted_at": attempted_at or utc_now(),
        "status": status,
        "notices": len(current.get("notices", [])) if isinstance(current, dict) else None,
        "sources": [
            {
                "id": s.get("id"),
                "status": s.get("status"),
                "count": s.get("count"),
                "last_success_at": s.get("last_success_at"),
            }
            for s in (current or {}).get("sources", [])
            if isinstance(s, dict) and isinstance(s.get("id"), str)
        ],
        "issues": issues[:25],
    }
    return out


def append_receipt(path: Path, item: dict) -> None:
    history: list = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing.get("checks"), list):
                history = existing["checks"]
        except (ValueError, TypeError, OSError, AttributeError):
            history = []
    # Deduplicate replays of an identical receipt and bound public Git size.
    history = [
        h for h in history if isinstance(h, dict) and not (
            h.get("attempted_at") == item.get("attempted_at") and h.get("status") == item.get("status")
        )
    ]
    history.append(item)
    history = history[-MAX_CHECKS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"version": 1, "checks": history}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def freshness_issues(snapshot: dict, history: dict, *, now: datetime, max_age_hours: int = STALE_SNAPSHOT_HOURS) -> list[str]:
    """Independent watchdog: checks GitHub snapshot/receipt timestamps."""
    problems = []
    if now.tzinfo is None:
        raise ValueError("now must have timezone")
    for label, value in [
        ("snapshot", snapshot.get("checked_at")),
        ("health_receipt", (history.get("checks") or [{}])[-1].get("attempted_at")),
    ]:
        timestamp = parse_utc(value)
        if timestamp is None:
            problems.append(label + "_timestamp_invalid")
        elif (now - timestamp).total_seconds() > max_age_hours * 3600:
            problems.append(label + "_stale")
        elif timestamp > now:
            problems.append(label + "_timestamp_in_future")
    if history.get("checks"):
        if history["checks"][-1].get("status") != "healthy":
            problems.append("latest_collection_not_healthy")
    return problems
