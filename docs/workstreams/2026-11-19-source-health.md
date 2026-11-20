# 公开通知采集健康与漏报风险可视化 [Implementation in progress]

> Status: Draft · IMPLEMENTATION CANDIDATE · GitHub scheduled integration: NOT VERIFIED
> Workstream: data-source-health · Size: M · Confidence: 高

## 目标及原因
学生不能因为定时工作流被跳过、网页改版或部分来源读取失败，就收到误导性的“没有新通知”。每个来源应有可核验的检查记录和失败证据，系统应明确何时数据可能过期。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)，产品 [Wish](https://github.com/mykcs/campus-agent/blob/main/docs/wish/PRODUCT-WISHES.md)。
- 基线问题（PR 建立前）：`.github/workflows/refresh.yml` 每两小时定时抓取；采集器原先只要通知数≥3便返回成功，部分来源失败可能让 Actions 仍为绿色。**本分支已修改此路径**，但正式 GitHub Actions 调度行为仍待验证。
- 未证实：GitHub cron 每次都能按时执行；所有来源每次抓取完整。GitHub 官方说明定时任务可能延迟甚至丢失：https://docs.github.com/en/actions/how-tos/troubleshoot-workflows

## 范围
- 包含：来源级 `last_checked_at/last_success_at/status/error` 的一致约定；新旧数据快照比对；严重失败或超时显式提示；公开最小化的审计证据；干净的重试与不覆盖旧数据策略；防止误报健康。
- 不包含：学生个人推送、学校私有登录、付费监控、重写历史 Git、保证绝对零漏报。

## 规模、依赖与顺序
- M：Python 采集器、Actions 和回归测试三个改动面，故障注入只在合成环境；独立可合并。
- 依赖：无。其他采集/推送工作应以此来源健康合同为前提。
- 下一个动作：读取 `scripts/collect.py`、`scripts/additional_sources.py` 和 `.github/workflows/refresh.yml`；先写“一个公开来源失败而其它成功”的 deterministic fixture。

## 预计实施方案
1. 设计每来源状态与全局 `checked_at` 的不变量：`partial` 表示覆盖有限，但不能表示这轮抓取失败；`error` 标记本轮失效；`last_success_at` 不因失败前移。
2. 引入统一健康报告/可审计输出；在合成失败或 stale 时 workflow 明确失败或输出 GitHub annotation，且绝不丢弃最后的有效公共快照。
3. 设计独立于同一个可能丢失的 cron 的最小缺跑核验方案，若无免费可靠途径，明确披露无法主动发现“整个 scheduler 未触发”而非承诺修好。

## 验收（DoD）
- [x] 本地 23 项单元测试覆盖成功、partial、故障注入、旧数据保留、全流程中断、重复运行幂等；失败不伪造成功时间。
- [x] 模拟来源失败、采集总中断与异常骤降；分别落地 degraded/failed 收据、非零退出码及原快照保留。
- [x] 本地 `uv run --with beautifulsoup4==4.14.2 python -m unittest discover -s tests -v` 23/23 通过；实际只读浙大5个源采集到临时目录65条，状态 healthy/0 errors。**GitHub-hosted PR CI 另行验收。**
- [ ] GitHub workflow 执行记录、JSON 健康样本、失败复现和修复后读回证据；更新 README 对部分覆盖/cron 丢失的真实边界。
- [x] 新健康收据只有来源 ID、时间、状态、计数、固定故障代码，不包含学生名单正文、密钥或 Session；实际代码仍仅读取已配置公开页面。

## 安全、隐私、资源与恢复
只读访问官方公开来源；不向用户邮箱/短信发送未经许可通知，不触碰现有 Vercel 部署与代理；运行在 GitHub-hosted Actions 可用配额内。改动可通过回滚本仓代码恢复；若需第三方监控服务或新凭据，先停在评估/申请阶段。

## 证据与进度
- 规格审查：按现有源码、Issue #5 拟定；需要实现者复核最新 head。
- 实施：本地候选代码已经完成；新 `scripts/source_health.py`、`scripts/check_freshness.py`、新增 PR checks/watchdog Actions 与 refresh fail-after-commit；**尚未合并**。
- 本地实测：2026-11-20 07:03 UTC，5个来源、65条、health=healthy，23/23 单测通过；1个来源失效时退化路径由合成故障注入证明。
- 集成验收：GitHub-hosted PR CI **待运行**；正式 schedule / watchdog 在 main 上尚未验收。系统仍受 GitHub 同平台 Cron 停摆风险，尚无外部独立 heartbeat。
- 最近核对：2026-11-20 UTC；当前 PR head 请以 GitHub 读回为准，main 会继续由定时任务更新。
