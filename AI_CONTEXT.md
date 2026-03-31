# OKX 超短线量化机器人

## 重要提示

**Freqtrade 通过 Docker 安装，运行目录: `/freqtrade/`**

策略文件位置: `/freqtrade/user_data/strategies/`

所有 freqtrade 命令需要在 Docker 容器内执行:
```bash
docker exec freqtrade freqtrade <command>
```

## 启动命令

```bash
# 回测策略1
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s EMARSIMomentumScalpingV1

# 回测策略2
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s VolumeRatioStrategyV1
```

## 策略对比汇总

### 策略1: EMA+RSI 动量剥头皮 (EMARSIMomentumScalpingV1)

| 属性 | 值 |
|------|-----|
| 类名 | `EMARSIMomentumScalpingV1` |
| 时间框架 | 1m / 5m |
| 核心指标 | EMA 9/21, RSI(14), 成交量 |
| 入场条件 | EMA金叉 + RSI>65 + 成交量放大 |
| 止损 | 0.8% |
| 止盈 | 2.5% (1:3盈亏比) |

**回测结果**:

| 时间框架 | 交易数 | 胜率 | 收益率 |
|----------|--------|------|--------|
| **1m** | 74 | 2.7% | **-7.04%** |
| 5m | 71 | 11.3% | -7.63% |

---

### 策略2: 量比策略 (VolumeRatioStrategyV1)

| 属性 | 值 |
|------|-----|
| 类名 | `VolumeRatioStrategyV1` |
| 时间框架 | 1m / 5m |
| 核心指标 | 成交量比率 |
| 入场条件 | 缩量(volume_ratio < 0.7) + 下跌 |
| 出场条件 | 放量(volume_ratio > 1.5) + 上涨 |
| 止损 | 3% |
| 止盈 | 2% |

**回测结果**:

| 时间框架 | 交易数 | 胜率 | 收益率 |
|----------|--------|------|--------|
| 1m | 6441 | 7.8% | **-99.85%** |
| 5m | 1801 | 7.8% | -84.11% |

---

## 结论

| 策略 | 1m收益 | 5m收益 | 状态 |
|------|--------|--------|------|
| EMA+RSI | -7.04% | -7.63% | ❌ 亏损 |
| 量比策略 | -99.85% | -84.11% | ❌ 严重亏损 |

**EMA+RSI 略优于量比策略**，但两者都亏损，不建议实盘。
