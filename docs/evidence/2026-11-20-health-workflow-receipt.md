# GitHub-hosted public source health receipt — 2026-11-20 UTC

> Workstream: [data PR #3](https://github.com/mykcs/campus-agent-data/pull/3)
> Run: [GitHub Actions #44693039901](https://github.com/mykcs/campus-agent-data/actions/runs/44693039901)
> Exact tested code head at dispatch: `8cb5b69a8b2c505f43a67f3474b8cbbb9f4e1545` (bot subsequently committed refreshed branch data).

## Verified against actual GitHub-hosted runner

All the following steps completed **successfully** on the PR's explicit branch, not a production main deployment:

1. `python -m unittest discover -s tests -v`: 23 tests passed.
2. `python scripts/collect.py`: read 5 ZJU public sources with **65 notices**, **0 errors**, `health=healthy`.
3. Workflow committed `data/notices.json` and `data/health-checks.json` in the experimental task branch.
4. The final `steps.collect.outcome` gate executed successfully.

The generated public health receipt used metadata-only source IDs, statuses, counts and UTC timestamps; no API key, campus credentials, student profile or notice body was introduced by the new audit schema.

**Important limitation:** This green run verifies the happy path and sequence of GitHub steps. Aborted, degraded and sudden-drop behavior was proven using **local deterministic failure injections**, not by intentionally breaking a real university source. Production default-branch scheduling and the new 6-hour watchdog have **not** been observed after merge. GitHub Actions schedule may delay or skip both runs; this is not an independent external heartbeat.

After branch validation the bot-generated data snapshot is intentionally removed from the proposed PR diff so normal scheduled `main` data updates do not create merge conflicts; the historical run and its GitHub commit remain reviewable in workflow logs.
