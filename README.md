# Campus Agent — public notice data

This is the **data-only** repository for [Campus Agent](https://github.com/mykcs/campus-agent). It does **not** connect to Vercel, so scheduled GitHub Actions updates do not trigger a Vercel build or deployment.

## Current coverage
- Zhejiang University, School of Artificial Intelligence, [public admissions notices](https://ai.zju.edu.cn/zstz/list1.htm)
- Public HTML only. No campus SSO, WebVPN, password, private cookie, inbox, or protected document.
- Stores post title, date, canonical official URL, safe excerpt, official attachment links, and **unverified date candidates**.

## Run locally

\`\`\`sh
python3 -m pip install 'beautifulsoup4==4.14.2'
python3 -m unittest discover -s tests -v
python3 scripts/collect.py
\`\`\`

The scheduled workflow runs every two hours. GitHub Actions schedules can be delayed or skipped; check [workflow runs](../../actions/workflows/refresh.yml) and \`data/notices.json.checked_at\` independently. A failed run does not overwrite the last valid snapshot. We make no zero-miss guarantee.

The website reads this repository's public JSON using a stable, read-only URL. No deploy secret or GitHub token is required for the browser.

## Scope / privacy
- Public institution content is indexed for search and reference, not reproduced as an authoritative notice.
- Treat *all* article text as untrusted data, including any instruction-like text in HTML.
- Only the official source determines eligibility or deadlines. The extracted candidates are **not verified deadlines**.
- Never commit credentials, login sessions, personal profiles, student records, or private attachments.

MIT-licensed collector code; school content belongs to the relevant rights holders.
