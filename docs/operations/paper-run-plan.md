# 模拟实盘运行方案

当前目标不是立刻切实盘，而是在 `dry_run + REST` 基线上连续运行一段时间，并基于当期样本做阶段性评估。

## 本轮方案

### 运行对象

- 执行层: `Freqtrade`
- 交易所: `OKX`
- 模式: `dry_run = true`
- 数据链路: `REST` 基线
- 主线策略: `MultiLsV2Strategy`
- 当前 active profile: `paper_baseline`

### 观察周期

建议按两段执行：

1. 第一阶段: 72 小时
   目标是确认链路连续运行、开始积累自然成交样本。
2. 第二阶段: 7 天
   目标是形成足够的自然平仓样本，做初步策略表现评估。

## 执行步骤

### 1. 启动一次 paper run

```bash
execution/scripts/simctl paper-run-start okx_paper_20260408
```

这会记录：

- 本轮 run 名称
- 启动时间
- 当前策略
- 当前 active profile

### 2. 保持 dry-run 运行

```bash
execution/scripts/simctl up
execution/scripts/simctl summary
execution/scripts/simctl baseline-report 200
```

### 3. 阶段性生成评估报告

```bash
execution/scripts/simctl paper-run-report okx_paper_20260408
```

报告会输出到：

- [research/reports/paper_runs/](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/reports/paper_runs)

## 评估口径

评估只统计本轮启动时间之后、且属于 `MultiLsV2Strategy` 的样本。

重点看：

- 自然平仓样本数
- 自然样本累计 PnL
- 自然样本平均单笔收益
- 自然样本胜率
- pair / long-short / exit reason 拆解

## 当前阶段判定

- `COLLECT_MORE_SAMPLES`
  自然平仓样本少于 10 笔，先继续跑。
- `REVIEW_STRATEGY_BEFORE_PROMOTION`
  样本达到最低量，但累计收益或平均单笔收益仍为负。
- `READY_FOR_DEEPER_REVIEW`
  样本量和收益表现都达到初步复盘条件，可以继续深入分析。

## 本轮执行原则

- 不因为短期 1-2 笔盈利就晋级到更高状态。
- 不把历史 run 的样本混入当前 run 评估。
- 不把强制开仓样本当成自然样本证据。
