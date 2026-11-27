#!/usr/bin/env python3
"""One-shot public-data probe suitable for an independently authorized host.

No cron install, account, secret, external notification or Git write. The
output is an observation/transition, not evidence of delivery or scheduling.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler

if __package__:
    from .source_health import freshness_issues
else:
    from source_health import freshness_issues

API = "https://api.github.com/repos/mykcs/campus-agent-data/commits/main"
RAW = "https://raw.githubusercontent.com/mykcs/campus-agent-data/"
MAX_BYTES = 4 * 1024 * 1024

class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unexpected redirect")

def fetch_json(url):
    # Only the fixed public repository HEAD and its immutable data files.
    if url != API and not re.fullmatch(re.escape(RAW)+r"[0-9a-f]{40}/data/(notices|health-checks)\.json",url):
        raise ValueError("unapproved URL")
    with build_opener(RejectRedirect()).open(Request(url,headers={"User-Agent":"CampusAgentPublicHealthProbe/1","Accept":"application/json"}),timeout=12) as res:
        raw=res.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError("oversized response")
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError("invalid response")
    return obj

def inspect(snapshot,history,now,max_age_hours=6):
    try:
        latest=history["checks"][-1]
        if not isinstance(latest,dict) or not isinstance(snapshot.get("notices"),list) or not isinstance(snapshot.get("sources"),list):
            return ["malformed-health-input"]
        codes=freshness_issues(snapshot,history,now=now,max_age_hours=max_age_hours)
        if snapshot.get("health",{}).get("status")!="healthy":
            codes.append("snapshot_not_healthy")
        if latest.get("attempted_at")!=snapshot.get("health",{}).get("assessed_at") or latest.get("notices")!=len(snapshot["notices"]):
            codes.append("snapshot_receipt_mismatch")
        if not snapshot["sources"] or any(not isinstance(s,dict) or s.get("status") not in {"ok","partial"} for s in snapshot["sources"]):
            codes.append("source_unhealthy")
        return sorted(set(codes))
    except (KeyError,IndexError,TypeError,AttributeError,ValueError):
        return ["malformed-health-input"]

def observe(fetcher=fetch_json,*,now,max_age_hours=6):
    sha=None
    try:
        sha=fetcher(API).get("sha")
        if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{40}",sha):raise ValueError("invalid commit")
        snapshot=fetcher(RAW+sha+"/data/notices.json")
        history=fetcher(RAW+sha+"/data/health-checks.json")
        codes=inspect(snapshot,history,now,max_age_hours)
        return {"status":"failed" if codes else "healthy","codes":codes,"sha":sha,"checked_at":snapshot.get("checked_at")}
    except Exception as exc:
        # Don't copy raw network response or exception text into receipts.
        return {"status":"failed","codes":["public_health_input_unavailable"],"sha":sha,"exception_type":type(exc).__name__}

def transition(previous,observation,now):
    old=previous.get("status") if isinstance(previous,dict) else None
    status=observation["status"]
    event="incident" if status=="failed" and old!="failed" else "recovered" if status=="healthy" and old=="failed" else "none"
    return {**observation,"observed_at":now.isoformat(timespec="seconds").replace("+00:00","Z"),"event":event}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state",required=True,type=Path,help="Private local state file outside Git")
    p.add_argument("--max-age-hours",type=int,default=6)
    args=p.parse_args()
    if not 1<=args.max_age_hours<=24:p.error("max-age-hours must be 1..24")
    now=datetime.now(timezone.utc)
    old={}
    if args.state.exists():
        try:
            old=json.loads(args.state.read_text())
            if not isinstance(old,dict) or old.get("status") not in {"healthy","failed"}:raise ValueError()
        except (OSError,ValueError):
            print(json.dumps({"status":"failed","codes":["invalid_local_monitor_state"],"event":"unknown"}))
            return 2
    result=transition(old,observe(now=now,max_age_hours=args.max_age_hours),now)
    try:
        args.state.parent.mkdir(parents=True,exist_ok=True)
        tmp=args.state.with_suffix(args.state.suffix+".tmp")
        tmp.write_text(json.dumps({"status":result["status"],"observed_at":result["observed_at"]})+"\n")
        tmp.replace(args.state)
    except OSError:
        print(json.dumps({"status":"failed","codes":["local_monitor_state_write_failed"],"event":"unknown"}))
        return 2
    print(json.dumps(result))
    return 0 if result["status"]=="healthy" else 2

if __name__=="__main__":raise SystemExit(main())
