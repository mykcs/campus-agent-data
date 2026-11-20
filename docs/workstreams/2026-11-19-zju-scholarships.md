# 浙大奖助与博士申请相关公开通知覆盖增强 [Implementation in progress]

> Status: Draft · IMPLEMENTATION CANDIDATE · GitHub-hosted integration: NOT VERIFIED
> Workstream: zju-scholarship-coverage · Size: M · Confidence: 中

## 目标及原因
优先解决错过浙大奖学金申请这一真实痛点，不再只依赖校级搜索前 10 条结果。学生关注“奖学金/资助”时能看到更多**有证据的直接官方来源**，并能知道覆盖与漏报风险。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)、[公开来源现状](https://github.com/mykcs/campus-agent-data/blob/main/README.md)。
- 已有：`scripts/additional_sources.py` 的 `zju-scholarships-search` 在校级搜索中只保存部分结果，`zju-mse-student` 采材料学院公开栏目；人工智能学院招生列表可用。
- 未证实：研究生院各类资助、其它学院直接栏目是否当前稳定可抓、是否允许全文镜像；各院网页的实际发布时间和内部截止规则可能不同。

## 范围
- 包含：先列出奖学金与资助的公开官方来源清单并记录 accessability；至少验证两处具有独立来源身份的公开栏目，优先研究生资助/学院奖助；增量获取标题、原文 URL、发布时间、部门、主题和覆盖状态；基于固定历史快照评估发现率。
- 不包含：奖学金申请资格自动判定、材料代写、OA/ETA 登录、扫描非公开通知、复制候选人/推荐名单正文。

## 规模、依赖与顺序
- M：来源发现、不同列表解析、去重及测试；来源变动是主要未知。该任务可独立交付，不包含短信/推送。
- 依赖：优先复用「采集健康」工作线的 status 合同；正式写入前刷新此仓 `main`，避免与 GH scheduled data commits 冲突。
- 下一个动作：比较研究生院官方资助栏目、现有材料学院学生事务栏目与校级搜索的同日样本；记录可公开访问、是否站点允许以及重复 ASIN/通知 URL（应按 URL / article id 去重）。

## 预计实施方案
1. 固化有来源链接的真实样本与覆盖表，不把用户无法访问的校园网链接伪装成已接入。
2. 优先复用校方 RSS/公开目录/现有 parser，必要时按来源写小适配器；分类为奖学金/助学金/资助而不是盲目全文爬取。
3. 对相同公告跨不同列表去重，保留官方原文与来源集；给 UI 所需字段稳定 JSON schema。

## 验收（DoD）
- [x] 匿名 HTTP 200 + HTML 解析已实测历史学院资助14条、工程师学院奖助6条；还有合成 fixture 与 URL 校验。**独立 GitHub-hosted 再验待完成。**
- [x] 与既有快照比较：65 → 85 个唯一条目，21 个新出现、1 个不再出现（校级搜索榜单可轮换）；净增20不等于20篇新发布。完整证据见 `docs/evidence/2026-11-20-zju-student-funding-source-audit.md`。
- [x] 本地 Python 回归13/13、实际临时数据7来源85条0错误；[ ] GitHub-hosted 同版本实际采集待运行。网站跨学院奖学金主题能消费新数据，但当前来源状态面板仍固定5项，须由网站多校 UI 工作线实现动态渲染。
- [x] 新源仅保存学校公布的标题、URL、日期（明确 `date_inferred`）、来源与主题，不抓全文；人员名单不镜像，历史学院相邻条目日期污染回归已修。
- [x] 两处官网可匿名读取，无 school SSO/WebVPN；README 和审计证据记录只覆盖有限公开栏目。

## 安全、隐私、资源与恢复
只抓公开网站，遵循站点规则与合理频率，不更改历史 Git 对象或公开个人申请记录。Github Actions 免费公开仓；不申请第三方 API Key。

## 证据与进度
- 规格审查：根据现有 `zju-scholarships-search` 与用户产品愿望整理。
- 实施：新增两处公开来源与安全解析回归，**尚未合并**；不能宣称全校覆盖。
- 本地验收：2026-11-20 07:19 UTC，65 → 85 条、7来源、0错误，13/13 测试通过；真实 GitHub-hosted 来源访问仍待验证。
- 集成验收：GitHub-hosted PR branch workflow **NOT RUN**；当前 Vercel 网站未改动。
- 最近核对：2026-11-20 UTC；head 以 GitHub PR 读回为准。
