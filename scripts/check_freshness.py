#!/usr/bin/env python3
"""Read-only watchdog: fail visibly if scheduled collection stopped or degraded.

Independent of the collection job but still hosted by GitHub Actions. It is
not an external uptime monitor and cannot guarantee notification delivery.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .source_health import freshness_issues
else:
    from source_health import freshness_issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="data/notices.json")
    parser.add_argument("--checks", default="data/health-checks.json")
    parser.add_argument("--max-age-hours", type=int, default=6)
    args = parser.parse_args()
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        history = json.loads(Path(args.checks).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({
            "status": "failed", "codes": ["health_input_unavailable"],
            "exception_type": type(exc).__name__,
        }), file=sys.stderr)
        return 2
    issues = freshness_issues(
        snapshot, history, now=datetime.now(timezone.utc),
        max_age_hours=args.max_age_hours,
    )
    print(json.dumps({
        "status": "healthy" if not issues else "failed",
        "codes": issues,
        "checked_at": snapshot.get("checked_at"),
        "most_recent_attempt_at": (history.get("checks") or [{}])[-1].get("attempted_at"),
    }))
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
