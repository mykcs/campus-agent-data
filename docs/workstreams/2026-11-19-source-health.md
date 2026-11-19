# 公开通知采集健康与漏报风险可视化 [Task spec only]

> Status: Draft · TASK SPEC ONLY · Implementation: NOT DONE
> Workstream: data-source-health · Size: M · Confidence: 高

## 目标及原因
学生不能因为定时工作流被跳过、网页改版或部分来源读取失败，就收到误导性的“没有新通知”。每个来源应有可核验的检查记录和失败证据，系统应明确何时数据可能过期。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)，产品 [Wish](https://github.com/mykcs/campus-agent/blob/main/docs/wish/PRODUCT-WISHES.md)。
- 已有：`.github/workflows/refresh.yml` 每两小时定时抓取；`scripts/collect.py` 有 `errors`、`checked_at`；`scripts/additional_sources.py` 输出 `ok/partial/error`。当前采集器只要通知数≥3便返回成功，部分来源失败可能让 Actions 仍为绿色。
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
- [ ] 单元测试覆盖成功、partial、HTTP 错误、结构变化、旧数据保留、全流程中断、重复运行幂等；新失败不伪造最新成功时间。
- [ ] 模拟 1 个来源失败时输出可辨认的 source error 并使指定告警门槛可观察；未坏的来源仍能读到，不覆盖快照为 0 项。
- [ ] 离线/CI 回归命令 `python -m unittest discover -s tests -v` 与 `python scripts/collect.py --output /tmp/campus-notices-test.json`，只对临时文件运行实际抓取；不人工攻击或故障化学校服务。
- [ ] GitHub workflow 执行记录、JSON 健康样本、失败复现和修复后读回证据；更新 README 对部分覆盖/cron 丢失的真实边界。
- [ ] 公开数据不包含学生名单正文、私人密钥、登录 Session 或任何非公开页面。

## 安全、隐私、资源与恢复
只读访问官方公开来源；不向用户邮箱/短信发送未经许可通知，不触碰现有 Vercel 部署与代理；运行在 GitHub-hosted Actions 可用配额内。改动可通过回滚本仓代码恢复；若需第三方监控服务或新凭据，先停在评估/申请阶段。

## 证据与进度
- 规格审查：按现有源码、Issue #5 拟定；需要实现者复核最新 head。
- 实施：NOT DONE
- 集成验收：NOT RUN
- 最近核对：2026-11-19 PT；当前 head 请以 PR 读回为准，数据主线会有定时提交。
