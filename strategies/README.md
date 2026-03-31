# 多空策略管理系统

## 概述

AI 量化交易策略管理工具，当前聚焦 OKX 合约多空切换策略，支持通过 YAML 配置文件定义策略，自动生成代码，一键回测和参数优化。

当前唯一主线策略为 `MultiLsV2Strategy`。

## 目录结构

```
strategies/
├── spec/                      # 策略配置文件 (YAML)
│   └── multi_ls_v2.yaml     # 多空切换策略 V2
├── generated/                 # 自动生成的策略代码
│   └── multi_ls_v2.py
├── templates/                # 策略模板
│   └── base_strategy.py
├── cli.py                    # 策略管理 CLI 工具
└── auto_*.py                 # 自动复制到 freqtrade 的策略
```

## 快速开始

### 在 Docker 内操作

所有操作都在 freqtrade Docker 容器内完成：

```bash
# 查看策略列表
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py list

# 查看策略配置
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py config multi_ls_v2 --list

# 修改参数
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py config multi_ls_v2 --set ma_period 180

# 重新生成策略代码
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py generate multi_ls_v2

# 运行回测
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py backtest multi_ls_v2 --phase train

# 跑完整的 train / validation / test 分段回测
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py validate multi_ls_v2

# 参数优化
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py optimize multi_ls_v2 --epochs 200

# 运行完整流程（生成 -> train hyperopt -> validation -> test）
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py run multi_ls_v2
```

## 回测规范

当前主线采用三段式验证：

1. `train_timerange`: 训练集，用于参数优化
2. `validation_timerange`: 验证集，用于筛选参数是否稳定
3. `test_timerange`: 测试集，用于最终观察样本外表现

推荐原则：

- 不要直接用测试集调参
- 每次调参先看 validation，再看 test
- `run` 命令默认执行完整三段流程

## 成本模型

当前策略规范会显式记录：

- `fee`
- `slippage_bps`
- `funding_rate_included`

当前 CLI 已接入：

- `fee`: 会自动传给 `freqtrade backtesting` / `freqtrade hyperopt`

当前仍未完整自动接入：

- `slippage_bps`
- `funding_rate`

所以现阶段回测解读原则是：

- 把结果视为“已包含手续费、但未完整包含滑点和资金费率”的中间结果
- 用于筛选策略方向可以
- 用于判断 OKX 永续真实可交易性仍然不够

## 风控模型

当前策略规范会显式记录：

- `max_open_trades`
- `max_daily_loss_pct`
- `max_drawdown_pct`
- `max_consecutive_losses`
- `cooldown_candles_after_loss_streak`

当前已接入：

- 风控边界进入 YAML
- CLI 在回测/优化时会打印当前风控边界

当前仍未完整自动接入：

- 单日亏损熔断
- 连续亏损后冷却
- 基于回测结果自动停止后续流程

所以现阶段风控解读原则是：

- 先把风险约束显式化，作为研发和审查边界
- 真正执行级熔断仍需在线上执行层或 Freqtrade config 继续落地

## 参数优先级

当前参数采用单一事实来源：

1. `spec/multi_ls_v2.yaml`
2. `generated/multi_ls_v2.py` 与 `auto_multi_ls_v2.py` 由 YAML 生成
3. `config/strategy_config.json` 仅作为运行说明和参数快照，不是主参数源

推荐做法：

- 修改默认参数时，优先更新 `spec/multi_ls_v2.yaml`
- 然后重新执行 `generate`

## 策略配置文件格式 (YAML)

### 完整示例

```yaml
name: "Multi-LS V2"
description: "多空切换策略 V2"
version: "2.0"

# 交易模式: spot(现货) / futures(合约)
trading_mode: "futures"
margin_mode: "isolated"

# 时间框架和做空
timeframe: "15m"
can_short: true

# 止盈止损
stoploss: -0.05
minimal_roi:
  "0": 0.02

trailing_stop: true
trailing_stop_positive: 0.02
trailing_stop_positive_offset: 0.025

# 成本模型
cost_model:
  fee: 0.001
  slippage_bps: 5
  funding_rate_included: false

# 因子配置 (可启用/禁用)
factors:
  # MA 因子
  ma:
    enabled: true
    type: "SMA"        # SMA, EMA, WMA
    period: 200
    range: [100, 300]
  
  # RSI 因子
  rsi:
    enabled: true
    period: 14
    range: [7, 21]
  
  # RSI 超卖阈值
  rsi_oversold:
    enabled: true
    value: 30
    range: [20, 35]
  
  # RSI 超买阈值
  rsi_overbought:
    enabled: true
    value: 70
    range: [65, 80]

# 入场条件 (Python 表达式)
entry_conditions:
  long: |
    (dataframe['close'] > dataframe['ma']) &
    (dataframe['ma_slope'] > 0) &
    (dataframe['rsi'] < rsi_oversold)

  short: |
    (dataframe['close'] < dataframe['ma']) &
    (dataframe['ma_slope'] < 0) &
    (dataframe['rsi'] > rsi_overbought)

# 出场条件
exit_conditions:
  long: |
    (dataframe['rsi'] > rsi_overbought) |
    (dataframe['close'] < dataframe['ma'])

  short: |
    (dataframe['rsi'] < rsi_oversold) |
    (dataframe['close'] > dataframe['ma'])

# 衍生指标
derived_indicators:
  - name: "ma_slope"
    formula: "dataframe['ma'].diff(3)"

# 优化配置
optimization:
  epochs: 200
  timerange: "20250101-20250930"
  hyperopt_loss: "ShortTradeDurHyperOptLoss"

# 风控模型
risk_model:
  max_open_trades: 3
  max_daily_loss_pct: 3.0
  max_drawdown_pct: 20.0
  max_consecutive_losses: 3
  cooldown_candles_after_loss_streak: 12

# 三段式时间范围
train_timerange: "20250101-20250930"
validation_timerange: "20251001-20251130"
test_timerange: "20251201-"

```

## 可用因子

| 因子 | 类型 | 参数 |
|------|------|------|
| MA | SMA/EMA/WMA | period, range |
| RSI | RSI | period, range |
| BB (布林带) | BB | period, std, std_range |
| Volume | Volume | ma_period, ratio_threshold |
| MACD | MACD | fast, slow, signal |

## 配置文件说明

### trading_mode
- `spot`: 现货交易
- `futures`: 合约交易

### margin_mode (仅合约)
- `isolated`: 逐仓
- `cross`: 全仓

### can_short
- `true`: 支持做空 (仅合约模式)
- `false`: 仅做多

## 运行模式

| 模式 | 命令 | 配置 |
|------|------|------|
| 单阶段回测 | `cli.py backtest --phase train|validation|test` | 分段验证 |
| 全部分段回测 | `cli.py validate` | train / validation / test |
| 模拟盘 | `freqtrade trade --dry-run` | dry_run: true |
| 实盘 | `freqtrade trade` | dry_run: false |

## 创建新策略

1. 在 `spec/` 目录创建新的 YAML 文件
2. 配置因子和条件
3. 使用 CLI 生成代码
4. 回测验证效果

## 目录同步

当前采用 Docker bind mount：

- 本地 `strategies/`
- 容器 `/freqtrade/user_data/strategies/`

因此策略开发、生成和修改默认都直接发生在本地 `strategies/`，无需额外执行 `docker cp`。
