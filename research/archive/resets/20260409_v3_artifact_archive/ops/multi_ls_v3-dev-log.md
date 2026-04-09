# MultiLsV3 开发文档（2026-04-09）

## 1. 目标

将 `MultiLsV2Strategy` 从“单层信号策略”升级为“结构化多层策略”：

- Regime 市场状态识别
- 双模型入场（趋势突破 + 震荡反转）
- 分层退出（信号退出 + 时间退出 + ATR 目标退出）
- 动态止损（ATR）
- 动态仓位（波动率目标化）

本次开发按主线链路落地：

`spec -> profile -> generated -> auto_json -> docker运行`

## 2. 影响层说明

本次改动影响三层：

1. Freqtrade 策略层：新增 `MultiLsV3Strategy`。
2. 主线策略定义层：新增 `spec/profiles`。
3. Docker 运行同步层：新增 `auto_multi_ls_v3.py` 与 `auto_multi_ls_v3.json`。

未修改执行容器镜像与交易所连接配置。

## 3. 新增文件

- `strategies/spec/multi_ls_v3.yaml`
- `strategies/profiles/multi_ls_v3/default.yaml`
- `strategies/profiles/multi_ls_v3/paper_baseline.yaml`
- `strategies/profiles/multi_ls_v3/_active.yaml`
- `strategies/generated/multi_ls_v3.py`
- `strategies/auto_multi_ls_v3.py`
- `strategies/auto_multi_ls_v3.json`

## 4. 策略结构

### 4.1 Regime

使用以下指标识别市场状态：

- 趋势态：`EMA 结构 + ADX + BB 宽度`
- 震荡态：`ADX 低 + BB 宽度低`
- 高噪音态：`ATR% 高于阈值`

### 4.2 Entry

- 趋势模型：Donchian 突破 + retest + RSI 过滤 + 流动性过滤。
- 震荡模型：BB 上下轨反转 + RSI 超买超卖 + RSI slope 反转。
- 全局过滤：高噪音禁入。

### 4.3 Exit

- `populate_exit_trend`: 趋势回落/反弹、震荡回中轨、高噪音退出。
- `custom_exit`: 时间止损、ATR 目标止盈、ATR 触发利润保护退出。

### 4.4 风险与仓位

- `custom_stoploss`: 基于 ATR 的动态止损，利润扩张后自动收紧。
- `custom_stake_amount`: 基于 ATR% 的动态仓位缩放，并在高噪音环境降仓。

## 5. 回测与验证步骤

### 5.1 启动环境

```bash
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade
```

### 5.2 基础回测（V3）

```bash
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s MultiLsV3Strategy
```

### 5.3 参数优化（建议）

```bash
docker exec freqtrade freqtrade hyperopt \
  -c /freqtrade/user_data/config.json \
  -s MultiLsV3Strategy \
  --spaces buy sell roi stoploss \
  --epochs 200
```

### 5.4 分段验证（建议）

- Train: `20250101-20250930`
- Validation: `20251001-20251130`
- Test: `20251201-`

要求至少满足：

- profit factor > 1.2
- max drawdown < 0.25
- validation 和 test 不出现明显坍塌

## 6. 已知限制

- `custom_stake_amount` 使用波动率缩放，不等价于完整 Kelly/组合优化。
- 相关性限仓（跨品种净暴露约束）暂未在策略内实现，建议在执行层补充。
- funding/slippage 仍建议在研究层追加保守扣减复核。

## 7. 下一步

1. 先跑 1 轮基础回测确认是否有交易与是否触发自定义退出。
2. 再跑超参并输出 topN 参数组合，导入新 candidate profile。
3. 通过验证集 gate 后，再在 OKX 模拟盘做 48-72 小时 shadow 观察。
