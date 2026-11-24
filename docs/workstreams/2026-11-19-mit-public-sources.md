# MIT 公开招生、研究生资助与校园通知源 [Task spec only]

> Status: Draft · TASK SPEC ONLY · Implementation: NOT DONE
> Workstream: mit-public-notices · Size: M · Confidence: 中

## 目标及原因
让 Campus Agent 读取 MIT 无需登录的学校/学院公告、研究生资助机会，给学生可追踪的官方来源，成为独立于浙大网络与网站模板的第一所跨国样本。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)、[产品愿望](https://github.com/mykcs/campus-agent/blob/main/docs/wish/PRODUCT-WISHES.md)。
- 已有：当前 collector 的固定域名白名单和 `zju-` 字段是浙大专用；MIT Mobile、OGE 与学院页面在产品调研中被列为候选，并未入公开数据 JSON。
- 待核实：哪些 MIT/学院官方 RSS、财务资助公开栏目目前无需 MIT Touchstone；不将任何私有 Pivot、Atlas 或 Sloan 账号页面当成公开 feed。

## 范围
- 包含：核实至少一个 MIT 官方公告/资助类别的公开稳定列表，优先研究生资助；建立来源登记、栏目分页/增量抓取、发布时间、官方链接、School/Department/category/topic、状态与地区时区。
- 不包含：MIT 身份认证、私人课程/财务记录、美国全部大学收录、自动判资格或跨学校前端完整 UI（后续 site 工作线）。

## 规模、依赖与顺序
- M：首个非 ZJU 来源的数据合同泛化/抓取适配器/fixture 是中等规模，真实来源接口未知；在单个 PR 内完成一个 MIT 学校级公共入口，不顺带做清华。
- 依赖：源健康工作线确定的状态/告警合同；站点多学校选择 PR 才能完成最终用户界面。
- 下一个动作：验证 MIT 官方公开栏目/RSS URL、robots/许可、最近真实公告样本；记录 `public yes/no` 后选择首个来源。

## 预计实施方案
1. 核实官方 https 站点及公开栏目，不从 Google 搜索摘要当作全部公告，也不抓校内私有系统。
2. 最小泛化来源注册机制；每来源固定允许的主机、标题/日期/官方 URL 与 source status；保留非公开地址的拒绝行为。
3. 用真实截取的公开 fixture 与只读 GitHub-hosted 检查验证去重、内容权利/敏感信息最小化。

## 验收（DoD）
- [ ] 至少一个真实 MIT 官方公开来源在 CI/授权真实环境可重复访问（不同日期两次或可重复 fixture + 一次在线核验），至少两个具备真实官方 URL 的公告项；否则保持 blocker，不宣称已接入。
- [ ] 公开 JSON 新增 `mit` 所属的 source/notice ID、官方 URL、主题与精确 status；不影响现有浙大 5 源状态。
- [ ] URL 主机/跳转检查、重复 ID、发布时间与时区、无登录/无私人数据负例有自动化测试。
- [ ] Actions 与 Python 测试通过；来源 coverage、抓取失败/partial 明确写入 README。
- [ ] 给 site 多校前端一个无密钥可消费的样本 JSON contract。

## 安全、隐私、资源与恢复
仅公开 MIT 官方来源，限制频率和页面大小，不调用模型和付费数据平台。不凭大学账号私自登录，不变更 Vercel 项目。可回滚 adapter 配置，不清除历史数据。

## 证据与进度
- 规格审查：根据项目现状与产品需求；真实 MIT URL 和公开可访问性 **未在本任务规格中验证**。
- 实施：NOT DONE
- 集成验收：NOT RUN
- 最近核对：2026-11-19 PT；PR 当前 head 需复核。

## 2026-11-24 implementation and evidence

Implemented two fixed MIT public source adapters: HST TWiHST dated newsletter issues, and OGE official funding reference pages. Both are partial: the newsletter is not an opportunity-level complete feed, and funding references have no assumed publication date, deadline, or open application status. Source timestamps, region, department and canonical MIT URL remain separate. No article bodies, rosters or MIT login are fetched.

Local live run 2026-11-24 16:43 UTC: **105 notices / 9 sources / 0 errors**; 15 HST issues + 5 OGE references, prior seven ZJU sources retained. 36/36 unit tests pass, including strict host/path, duplicate links, no inferred funding deadline and stale-cache on error. GitHub manual read-only smoke uses temporary output, not branch or production data commits. Production readback remains an independent gate.
