# 多申请路径的截止日期证据模型与反误报测试 [Implementation candidate]

> Status: Draft · implementation candidate · exact-head CI and live collection pending
> Workstream: typed-deadline-evidence · Size: M · Confidence: 中

## 目标及原因
一份博士招生或奖学金通知常同时含报名开始、网上申请截止、推荐截止、寄出/收件日期和不同申请类别。系统不能只提取一个日期就称“你还能申请”，也不能自动认定用户符合要求。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)；现有 [任务合同](https://github.com/mykcs/campus-agent/blob/main/docs/dev/TASK-STATE-AND-ICS.md) 明确 `date_candidates` 不是用户确认截止日。
- 已有：`scripts/collect.py::extract_dates` 将带上下文的中文日期以 `verified:false` 提供给前端，`taskboard.js` 需要用户核对才创建任务；`tests/test_collect.py` 有少量合成日期断言。
- 未证实：各校跨页和附件中的截止日结构化准确率，系统从未被独立验证为可以自动匹配某个学生的资格。

## 范围
- 包含：支持多个日期类型、每条适用对象与证据出处的结构化候选（`open/close/internal/recommendation/postmark/unknown` 等稳定枚举）；来源段落/URL、时区与是否含小时；对既有 `date_candidates` 兼容。
- 不包含：真人资格自动判定、招生文件代填、自动把候选写入个人 Progress、模型自动决策/提交。

## 规模、依赖与顺序
- M：确定 JSON 合同、提取/回归规则、历史公告样本与数据验收；若需 Word/PDF 深解析单列后续方案，不扩大此 PR。
- 依赖：无硬依赖，优先在「采集健康」之后合并以减少接口漂移；站点今后消费新字段为独立后续任务，当前UI必须保持兼容。
- 下一个动作：打开固定的公开2027年 AI 学院博士招生简章与奖学金通知，只记录**不含私人名单**的发布日期、流程段落、不同截止日期及来源链接；建立人工核实测试表。

## 预计实施方案
1. 定义 `date_events` 的语义字段与 `verified:false` 不变量；时间/时区可空，不默认北京、PT 或 UTC。
2. 从正反样本完善规则提取；同篇多申请类别不合并一个「最终截止日」；保留旧字段。
3. 在单元测试中针对多截止/开始日/跨时区/含年份缺失/附件未读取等做负例。

## 验收（DoD）
- [ ] 至少覆盖博士报名开始与结束、推荐/学院内部期限、奖学金提交与邮寄期限的正例；无足够证据时标记 unknown。
- [ ] 错误判定“不适用学生符合条件”的测试为 0；数据结果仍不得包含确认证书或个人资格结论。
- [ ] 新 JSON schema 可被旧站点读取（回归 `date_candidates`）；官方 URL/原文片段可逐项追踪；无跨申请类别日期合并。
- [ ] Python 单元测试与在现有公开源的只读采样成功，记录可复现实测差异；单元 fixture 不含个人数据。
- [ ] 与申请 Progress 的手动日期确认保持独立，禁止任何后端自动修改浏览器个人状态。

## 安全、隐私、资源与恢复
仅处理无需登录的公告和已公开的招生/奖学金规则段落；不储存人的名单，不调用模型或付费 API，不扩大爬取频率。变更可回滚到兼容 schema。

## 证据与进度
- 规格审查：根据 `extract_dates` 源码和项目 Wish；需实施前复核真实当前来源。
- 实施：新增 `scripts/date_evidence.py`、兼容 `date_events`、保留 `date_candidates` 和用户人工确认；无年份或非法/未解析的小时分钟保留原始线索且 `value:null`。
- 集成验收：候选分支待 GitHub exact-head tests 和公开源采集；无生产发布。
- 最近核对：2026-11-19 PT；head 由 PR 读回。

## 2026-11-24 · implementation scope

`date_events` fields: `type` (open/close/internal/recommendation/postmark/unknown), `value` (ISO date or local date-time, null if unresolved), `raw`, `resolution`, `has_time`, explicit `timezone` or null, literal `scope_text` or null, bounded `context`, `source_url`, `verified:false`. No guessed year, assumed timezone, user eligibility or confirmed deadlines. The old candidate contract remains intact. Multiple same-day occurrences are retained. Title-only auxiliary sources need not supply this optional field. Attachments are linked but not parsed. Synthetic fixtures include cases from the two public notices at https://ai.zju.edu.cn/2026/1020/c90497a3216866/page.htm and https://ai.zju.edu.cn/2026/0810/c90497a3194262/page.htm; real-world extraction accuracy remains unverified until a separate sample run.
