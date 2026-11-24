# 清华大学可公开访问的院系通知源 [Task spec only]

> Status: Draft · TASK SPEC ONLY · Implementation: NOT DONE
> Workstream: tsinghua-public-notices · Size: M · Confidence: 低

## 目标及原因
在不接入清华校园身份认证、不尝试抓取校内非公开“清小搭”知识库的前提下，收录可以从校外直接访问的官方院系招生与奖学金通知。

## 来源与当前事实
- 来源：[Campus Agent 总索引](https://github.com/mykcs/campus-agent/issues/5)、[公开通知产品愿望](https://github.com/mykcs/campus-agent/blob/main/docs/wish/PRODUCT-WISHES.md)。
- 已有：清华“清小搭”是独立校内服务，不等于有第三方官方公开通知 API；当前数据仓只接入浙大。
- 未证实：哪些清华官网/院系列表在当前 GitHub-hosted CI 位置稳定公开；部分校园信息仅限校内访问，不能伪装成 public feed。

## 范围
- 包含：至少一个经校外匿名实际验证的清华公开招生或资助源；UTF-8/GBK 页面解析、分页/时间、去重、可信官方原文、数据合同与覆盖率标记。
- 不包含：清小搭内部数据、校内微信/清华账号、WebVPN/CAS、校园网代理、爬取整校所有院系、用户个人资格判断。

## 规模、依赖与顺序
- M，confidence 低：页面编码、院系入口和公开可读性存在重大未知；单独于 MIT 拆分，避免 MIT 成功被误当成清华交付。
- 依赖：公共来源健康状态合同；多学校 UI 工作线消费后才有前端完整用户成果。
- 下一个动作：建立一张候选源验证表，按 **匿名 HTTP → HTML/RSS 解析 → 官方原文链接 → 两次可复核** 顺序排除登录依赖。

## 预计实施方案
1. 查官方站点目录与院系公开公告，只保留明确可匿名访问的 URLs；记录 `blocked/campus_only/partial/ok` 等来源事实，不试图穿越权限。
2. 以新来源配置复用 MIT/浙大已有的 source schema，专门回归简体中文编码、发布时间与多页索引。
3. 将官方 URL 和证据写入测试 fixture，覆盖错误主机、网页替换为认证页、没有通知但无报错的假成功。

## 验收（DoD）
- [ ] 至少一个清华官方公开院系栏目真实匿名可访问，源条目具有官网 URL、来源部门、日期/待核对状态，能在不同运行中读回；未成功时如实记为 blocker/partial 而非“已监控清华”。
- [ ] 不请求/保存清华账号、Cookie、代理或校园网资源；用户公示名单仅标题与官方链接。
- [ ] 官方身份/URL白名单校验和编码/分页/故障测试通过；对现有浙大和将来 MIT data schema 无回归。
- [ ] CI 运行和 JSON 来源 status 读回可追溯；对来源“只覆盖部分公开栏”有明确文案。
- [ ] 给站点 UI 一个带 `school:清华大学` 的无密钥测试样本。

## 安全、隐私、资源与恢复
仅公开学校网页；不调用“清小搭”私有能力、不使用学校 VPN、不开第三方付费爬虫。若所有候选需要校内权限，停止采集并保留事实证据，不能擅自绕行。

## 证据与进度
- 规格审查：依据项目 Wish 与目前无清华适配器的源码状态；官网入口和公开程度需真正实施时验证。
- 实施：NOT DONE
- 集成验收：NOT RUN
- 最近核对：2026-11-19 PT；以当前 PR head 为准。

## 2026-11-24 implementation

Added the anonymous official [SIGS public admissions list](https://www.sigs.tsinghua.edu.cn/_s3/7770/list.psp), bounded to recent list items and the verified column URL pattern. Metadata only; explicit per-row publication dates take precedence over URL-inferred dates, no eligibility or deadline inference. The source is partial, not university-wide. The live local collection on 2026-11-24 16:46 UTC returned 113 total entries from 10 source identities, including 8 SIGS items, zero errors. 37/37 unit tests passed. Central graduate admissions and other departments are not claimed as covered. GitHub read-only live smoke and main readback are release gates.
