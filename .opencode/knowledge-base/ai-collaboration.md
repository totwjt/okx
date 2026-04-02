# AI 协作说明

## 目标

让 OpenCode、Codex 以及后续接手的 AI 在这个仓库里基于同一组事实工作，避免重复犯以下错误：

- 把模板目录误当成当前运行目录
- 把本地 `strategies/` 误当成容器内已经生效的策略
- 把回测脚本结论误当成可直接实盘的执行结论
- 把文档中的旧策略名误当成当前真实策略名

## 单一事实来源

涉及运行状态时，优先级如下：

1. `execution/freqtrade/docker-compose.yml`
2. `execution/freqtrade/user_data/config.json`
3. `strategies/`
4. 最近的 `execution/freqtrade/user_data/backtest_results/`
5. 说明性文档

## 目录角色

- `strategies/`: 本地研发与 Docker 实际执行共用目录
- `research/`: 研究型验证脚本与报告，不等于 Freqtrade 官方回测结果
- `apps/prototypes/freqtrade_bot/`: 原型级实时机器人，不是成熟 OMS/EMS

## AI 修改原则

- 如果任务是分析或审计，先核对目录和类名，再下判断。
- 如果任务是改文档，只更新文档，不顺手改策略逻辑。
- 如果任务是改策略，直接修改 `strategies/`，它会同步影响 Docker 运行态。
- 如果发现文档和代码冲突，先保留冲突事实，再修正文档，不要掩盖。

## 专业交易语境提醒

OKX 永续合约策略不能只看方向信号，至少还要考虑：

- 手续费与滑点
- 资金费率
- 杠杆与仓位限制
- 最小下单量和精度
- 触发器延迟与网络抖动
- 连续亏损和风控熔断

## 推荐 AI 工作流

1. 识别本次任务是否允许改功能代码
2. 读取当前运行配置与最近回测结果
3. 核对 Docker 是否仍在挂载本地 `strategies/`
4. 再提出建议或修改
