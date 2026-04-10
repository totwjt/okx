# 多空策略管理系统

## 概述

AI 量化交易策略管理工具，当前聚焦 OKX 合约多空切换策略，支持通过 YAML 配置文件定义策略，自动生成代码，一键回测和参数优化。

当前 `docker compose up` 默认运行策略为 `GridLsV1Strategy`（SOL 网格均值回归基线），但仓库当前并不只有这一条策略生成链。

当前已存在的主线策略 slug 包括：

- `grid_ls_v1`
- `multi_ls_v2`
- `multi_ls_v3`

当前主线唯一允许的策略接入方式是：

`spec -> profile -> generated -> auto_json -> docker运行`

因此：

- `strategies/spec/` 是唯一主线策略定义入口
- `strategies/profiles/` 是唯一主线参数入口
- `strategies/generated/`、`strategies/auto_*.py`、`strategies/auto_*.json` 都是生成产物
- 独立实验策略不得再直接放在 `strategies/` 主目录
- 历史实验策略已移入 `research/archive/`

当前参数治理采用 `Spec + Profile + Promotion`：

1. `spec/`
定义策略结构、因子空间、表达式与默认值。
2. `profiles/`
定义具体参数档案，例如 `default`、`paper_baseline`、`candidate_xxx`。
3. `promotion`
通过 CLI 把 profile 从 `candidate` 晋级到 `validated` / `paper_active` / `live_active`。

推荐候选参数流程：

1. `profile create` 创建 candidate
2. `profile validate` 在 `validation_timerange` 上回测 candidate
3. 查看 PASS / FAIL 和写回 profile 的 `validation.last_result`
4. 通过后用 `--promote-on-pass` 或手动 `profile promote ... validated`
5. 再按需要晋级到 `paper_active` / `live_active`

## 目录结构

```
strategies/
├── spec/                      # 策略配置文件 (YAML)
│   ├── multi_ls_v2.yaml     # 多空切换策略 V2
│   ├── multi_ls_v3.yaml     # 多空结构化策略 V3
│   └── grid_ls_v1.yaml      # 网格均值回归策略 V1
├── profiles/                  # 参数档案与激活指针
│   ├── multi_ls_v2/
│   └── grid_ls_v1/
│       ├── default.yaml
│       ├── paper_baseline.yaml
│       └── _active.yaml
├── generated/                 # 自动生成的策略代码
│   ├── grid_ls_v1.py
│   ├── multi_ls_v2.py
│   └── multi_ls_v3.py
├── templates/                # 策略模板
│   └── base_strategy.py
├── cli.py                    # 策略管理 CLI 工具
└── auto_*.py                 # 自动复制到 freqtrade 的策略
```

补充约束：

- `strategies/` 主目录只保留主线生成链相关文件
- 历史策略与旧规范移入 `research/archive/`
- 新实验应放到 `research/experiments/`

## 快速开始

### 在 Docker 内操作

所有操作都在 freqtrade Docker 容器内完成：

```bash
# 启动主执行环境
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade

# 查看策略列表
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py list

# 查看 profiles
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile list multi_ls_v2

# 查看当前 active profile
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile show multi_ls_v2

# 从当前 active profile 复制创建 candidate
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile create multi_ls_v2 candidate_rsi_soften --from-profile paper_baseline

# 激活某个 profile
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile activate multi_ls_v2 paper_baseline

# 晋级 profile
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile promote multi_ls_v2 paper_baseline paper_active

# 对 candidate profile 跑 validation gate
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile validate multi_ls_v2 candidate_test

# 自定义 gate，并在通过时自动晋级到 validated
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py profile validate multi_ls_v2 candidate_test \
  --min-trades 10 \
  --min-profit 0.02 \
  --min-profit-factor 1.1 \
  --min-winrate 0.45 \
  --min-trades-per-day 0.5 \
  --max-drawdown 0.20 \
  --promote-on-pass

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
- `profile validate` 只针对 `validation_timerange` 跑 gate，适合 candidate profile 快速筛选

`profile validate` 当前会：

- 使用目标 profile 覆盖 spec 并同步运行参数快照
- 调用 Freqtrade 在 validation timerange 上回测
- 解析回测 zip 内 JSON 指标
- 输出 `PASS` / `FAIL`
- 把最近一次验证结果写回对应 profile 的 `validation.last_result`
- 在传入 `--promote-on-pass` 且通过时自动把 profile 状态更新为 `validated`

默认 gate 阈值：

- `--min-trades 1`
- `--min-profit 0.0`
- `--min-profit-factor 1.0`
- `--min-winrate 0.0`
- `--min-avg-profit 0.0`
- `--min-trades-per-day 0.0`
- `--max-drawdown 0.30`

`profile validate` 现在还会输出：

- `failed_checks`，明确指出是哪条 gate 没过
- `warnings`，例如 `0 trades` 这种只能算冒烟通过、不能算策略证据的情况
- `validation_days` 与 `trades_per_day`，用于识别“虽然通过但样本太稀薄”的 profile

返回码约定：

- `0`: 校验通过
- `2`: 校验未通过 gate
- 其他非 `0`: 命令执行失败，例如回测失败或结果解析失败

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
- `execution/freqtrade/user_data/config.json` 已加入 `CooldownPeriod` / `StoplossGuard` / `MaxDrawdown`

当前仍未完整自动接入：

- 单日亏损熔断
- 连续亏损后冷却
- 基于回测结果自动停止后续流程

所以现阶段风控解读原则是：

- 先把风险约束显式化，作为研发和审查边界
- `Freqtrade protections` 已接入部分通用保护
- 真正执行级日内熔断仍需在线上执行层或更细粒度风控逻辑继续落地

## 参数优先级

当前参数采用单一事实来源：

1. `spec/<strategy>.yaml`
2. `generated/<strategy>.py` 与 `auto_<strategy>.py` 由策略定义生成
3. `profiles/<strategy>/*.yaml` 管理具体运行参数组合
4. `execution/configs/strategy_config.snapshot.json` 仅作为运行说明和参数快照，不是主参数源

推荐做法：

- 修改默认参数时，优先更新 `spec/<strategy>.yaml`
- 修改候选运行参数时，优先新建或更新 `profiles/`
- 使用 `profile activate` / `profile promote` 切换当前 active profile
- 然后重新执行 `generate`
- 不要把新的独立实验策略文件直接放进 `strategies/` 主目录

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
