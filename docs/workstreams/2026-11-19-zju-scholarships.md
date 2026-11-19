# 浙大奖助与博士申请相关公开通知覆盖增强 [Task spec only]

> Status: Draft · TASK SPEC ONLY · Implementation: NOT DONE
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
- [ ] 至少两处新检验的公开官方资助栏目有 2 次独立采集/同一版本的固定 fixture，或明确记录实际不可访问的阻碍而不宣称交付。
- [ ] 比较旧校级搜索前 10 条与新增直连来源的最近公告覆盖，给出有依据的增量/已知漏项；未发现新公告不能仅靠搜索没有结果就判定不存在。
- [ ] Python 单元和 GitHub-hosted 工作流检查通过，新 JSON 能被现有站点读取并保持 `partial/ok/error` 等准确含义。
- [ ] 人名公示/人员名单仅标题和官方链接；日期候选不自动称为截止，所有条目带原始 URL。
- [ ] 无 school SSO/WebVPN，资源与失败说明留在数据仓 README。

## 安全、隐私、资源与恢复
只抓公开网站，遵循站点规则与合理频率，不更改历史 Git 对象或公开个人申请记录。Github Actions 免费公开仓；不申请第三方 API Key。

## 证据与进度
- 规格审查：根据现有 `zju-scholarships-search` 与用户产品愿望整理。
- 实施：NOT DONE；真覆盖率与来源名单需下一位 Agent 实测。
- 集成验收：NOT RUN
- 最近核对：2026-11-19 PT；head 由 GitHub PR 负责。
