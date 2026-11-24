# ZJU public student funding source audit — 2026-11-20 UTC

> Workstream: [campus-agent-data PR #4](https://github.com/mykcs/campus-agent-data/pull/4).
> Evidence: real anonymous HTTP/HTML reads and deterministic Python tests. No school login, applicant names, private attachments or paid model API.

## Verified public sources

| Official list | Anonymous Mac HTTP | Actual parsed items | Coverage |
| --- | --- | --- | --- |
| [History School — student funding](https://ls.zju.edu.cn/65208/list.htm) | 200 | 14 first-page articles | Direct public aid list; **not whole-ZJU coverage** |
| [Engineering College — student affairs](https://pi.zju.edu.cn/67027/list.htm) | 200 | 6 first-page award/aid titles | **Partial** scholarship keyword filter in broader public list |
| [Existing ZJU scholarship public search](https://s2.zju.edu.cn/search/info.do?words=%E5%A5%96%E5%AD%A6%E9%87%91) | Prior configured source | 10 ranked results at baseline | Incomplete search, not a deadline alert feed |
| [Existing Materials School student affairs](https://mse.zju.edu.cn/51031/list.htm) | Prior configured source | 20 records at baseline | Direct college list, not entire school |

### Read-only collection: 2026-11-20 07:19 UTC

Against the prior 65-item, 5-source snapshot, the new code returned **85 unique notices across 7 source identities**, errors **0**; 14 History and 6 Engineering source entries, with **no mirrored article body strings** for either. Comparing snapshot IDs: 21 newly present and 1 previously present absent (ranked search results rotate), net **+20**. Do not label these 20 as newly issued university publications.

**Date parsing incident fixed:** in History School's list, the old parser accidentally attributed a 2026-11-08 sibling's displayed date to a notice whose URL and own date show 2026-11-01. The new code only uses within-item dates and checks article URL dates, else falls back to an explicitly inferred date. Tests include this regression, host-allowlist negatives and the existing privacy/failure cases; **13/13 local tests passed**.

The two hosts returned HTTP 404 for `robots.txt` during this check; that is **not blanket authorization** to harvest content. Use modest requests, public title/URL/date only, and stop on site-imposed restrictions.

### Remaining integration checks

- Run `refresh.yml` in GitHub-hosted Actions for the exact implementation branch; local Mac access does not guarantee CI-hosted access.
- Read back the resulting JSON and source statuses at that exact head; reconcile with scheduled `main` data changes.
- Current website has a hardcoded 5-source status panel. New scholarships will be visible through the cross-department topic filter, but displaying their per-source health cards belongs to a separate **site** PR; do not claim that frontend task is finished.
- No student-specific eligibility, complete scholarship coverage or confirmed official deadline has been established.
