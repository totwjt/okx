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
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py backtest multi_ls_v2

# 参数优化
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py optimize multi_ls_v2 --epochs 200

# 运行完整流程
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py run multi_ls_v2
```

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
  timerange: "20250101-20251101"
  hyperopt_loss: "ShortTradeDurHyperOptLoss"

# 测试时间范围
test_timerange: "20251101-"

# 运行时参数覆盖
config_overrides:
  ma_period: 204
  rsi_period: 18
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
| 回测 | `cli.py backtest` | 历史数据验证 |
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
