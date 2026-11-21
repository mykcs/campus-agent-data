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
