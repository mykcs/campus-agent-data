# Campus Agent — public university notices

This repository contains public university notice indexes, independent of [the website](https://github.com/mykcs/campus-agent) on Vercel Hobby. It updates every two hours through GitHub Actions and **never commits to the Vercel-connected website repo**. Changing notice data therefore does not invoke a Vercel build.

## Sources (current trial)

| Scope | Method | Confidence |
|---|---|---|
| ZJU School of Artificial Intelligence — admissions | [Public college notice index](https://ai.zju.edu.cn/zstz/list1.htm) | Direct public list |
| ZJU School of Computer Science and Technology | [ZJU official public search](https://s2.zju.edu.cn/search/info.do?words=%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%A7%91%E5%AD%A6%E4%B8%8E%E6%8A%80%E6%9C%AF%E5%AD%A6%E9%99%A2) | **Partial search results**, not full college monitoring |
| ZJU School of Software Technology | [ZJU official public search](https://s2.zju.edu.cn/search/info.do?words=%E8%BD%AF%E4%BB%B6%E5%AD%A6%E9%99%A2) | **Partial search results**, not full college monitoring |
| Scholarship notices across ZJU | [ZJU official public search](https://s2.zju.edu.cn/search/info.do?words=%E5%A5%96%E5%AD%A6%E9%87%91) | **Partial search results** |
| ZJU Materials School — student affairs | [Official public student notices](https://mse.zju.edu.cn/51031/list.htm) | Direct public list |
| ZJU History School — student aid | [Official student funding notices](https://ls.zju.edu.cn/65208/list.htm) | Direct public aid list; school-local scope only |
| ZJU College of Engineering — scholarships within student affairs | [Official student affairs notices](https://pi.zju.edu.cn/67027/list.htm) | **Partial**: keyword-filtered from a broader public list |

The college search hits may lag behind source publications, be ranked by relevance rather than chronology, and miss notices. The History School and Engineering College additions are **separate publicly readable college sources**; neither proves whole-ZJU scholarship coverage. They only store a public title, canonical university URL, date and source status; people-list bodies are not mirrored. The website exposes `status: partial` for this reason. When public portals refuse access, this scraper does not bypass campus restrictions.

## Run

~~~sh
uv run --with beautifulsoup4==4.14.2 python -m unittest discover -s tests -v
uv run --with beautifulsoup4==4.14.2 python scripts/collect.py
~~~

The index is `data/notices.json`. Source objects include monitored URL, status, count, check timestamp and last successful timestamp; notice objects include official URL, source ID, department ID, topic IDs, title and possibly a short excerpt. **Dates extracted from article text are unverified candidates; inferred publish dates are marked separately.** Any new source failure is reported in `sources[].status` and `errors`; cached records are marked stale.

The scheduler can be delayed or skipped; data freshness is not a guarantee. Verify [workflow runs](../../actions/workflows/refresh.yml) and the last check timestamp.

## Privacy / rights

Only public HTML and official URLs are accessed. No SSO, school password, session cookie, WebVPN or nonpublic attachments. Applicant rosters and other personal lists are not downloaded and only their title + official URL are indexed. Non-list articles are stored only as short extracts; search-derived entries contain titles and URLs only. Official university pages are authoritative for eligibility, dates and procedures; this project is an independent index, not a school service.

MIT licensed collector code; university content belongs to its respective owners. Never paste secrets, session tokens or personal student records into commits or issues.

## Collector health, audit receipts, and missed schedules

The collector publishes `data/notices.json` and a **bounded, metadata-only**
`data/health-checks.json` receipt (latest 120 attempts). There are three
independent ideas; they should not be conflated:

- **ok**: source was fetched and parsed on this run; **partial** means the
  underlying public search covers only some notices, not that it failed.
- **degraded/error**: a source failed or data quality is suspicious; the
  published notice snapshot retains last-known-good rows where available and
  includes per-source failure status. The collector exits nonzero.
- **fatal** (for example, a major unexplained count drop, duplicate identities,
  or an aborted complete collection): the previous `data/notices.json` remains
  unchanged. The failed attempt is recorded in `data/health-checks.json`.

The refresh workflow deliberately **commits the truthful health receipt
before failing the job** on a degraded collection. A green run means the
run's collector checks passed, not that every configured public feed is
complete or that the cron ran on schedule.

A separate read-only `health-watch.yml` checks both the last snapshot's
`checked_at` and the last recorded attempt every three hours, failing when
the record is more than six hours old or the latest attempt was unhealthy.
It is **still scheduled by GitHub Actions**: if GitHub stops firing both cron
workflows, neither can reliably notify users. This is a detection aid, not an
external uptime guarantee or opt-in student push notification.

Useful commands:

~~~sh
uv run --with beautifulsoup4==4.14.2 python -m unittest discover -s tests -v
python3 scripts/check_freshness.py --max-age-hours 6
# Test against real public sources without altering production data:
mkdir -p /tmp/campus-health-smoke
cp data/notices.json /tmp/campus-health-smoke/notices.json
uv run --with beautifulsoup4==4.14.2 python scripts/collect.py \
  --output /tmp/campus-health-smoke/notices.json \
  --checks-output /tmp/campus-health-smoke/health-checks.json --fast
~~~

GitHub workflow dispatch and scheduled runs are separate from a student's
actual push-notification experience. PR tasks for alert delivery remain
unfinished; no school credentials, student rosters, or BYOK keys enter the
public health receipt.

## MIT public sources

- [Harvard-MIT HST TWiHST archive](https://hst.mit.edu/news-events/twihst): up to 15 dated newsletter issues, partial coverage.
- [MIT OGE fellowships](https://oge.mit.edu/fellowships/): five official funding reference links, no inferred publication date, current availability or deadline. Partial coverage.

International sources use fixed HTTPS hosts and explicit link patterns; login/external redirects are rejected. Metadata only; no notice body copied. To independently verify a collector candidate in GitHub-hosted CI, manually dispatch `checks.yml` on that branch: it runs a public-source collection into temporary files without committing data.

## Tsinghua public source

[Shenzhen International Graduate School admissions notices](https://www.sigs.tsinghua.edu.cn/_s3/7770/list.psp): recent official public notice titles, URLs and row dates. Partial coverage; no school authentication or applicant details. URL-derived dates are explicitly marked inferred. The central admissions site and other departments are not included in this source.

## Topic contract (Issue #11)

`scripts/topic_contract.py` owns the stable title-based multi-label IDs
`scholarships`, `admissions`, `teaching`, `activities`. The first three
remain compatible with existing follow settings; an unknown title can retain
an empty array. Explicit official funding/admissions source scope may add a
label. A newsletter issue is not automatically an individual event, and an
undated funding reference is not an open opportunity. Activity is a discovery
hint only; official source, event time and eligibility still require review.
No new article-body scraping or school-wide activity coverage is implied.
Site consumption uses the same IDs; a new topic does not silently change
the user's previous selections. Personal-list records remain metadata only.
