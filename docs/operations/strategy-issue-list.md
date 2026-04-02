# 第一版策略问题清单

## 结论先行

当前还不能根据 `tradesv3.sqlite` 里的累计盈亏，直接评价 `MultiLsV2Strategy` 的真实表现。

原因很简单：

- 库里共有 `13` 笔已平交易
- 其中 `12` 笔来自 `VolumeRatioStrategy`
- 只有 `1` 笔来自 `MultiLsV2Strategy`
- 这 `1` 笔还是人工 `force-enter / force-exit` 验证单，不是自然信号驱动样本

所以现在最重要的不是“继续调参数”，而是先明确证据边界。

## 当前证据边界

已确认事实：

- 当前默认主线策略是 `MultiLsV2Strategy`
- 当前运行基线是 `dry_run + REST`
- 模拟盘开仓、平仓、持仓和订单落库链路已验证通过
- 数据库中的历史策略样本主要是旧的 `VolumeRatioStrategy`

因此当前可下的结论是：

- 可以评价执行链路
- 可以评价当前运行方式
- 不能用现有历史成交直接评价 `MultiLsV2Strategy` 的优劣

## 高优先级问题

### 1. 当前主策略缺少自然交易样本

这是最优先的问题。

没有足够的 `MultiLsV2Strategy` 自然成交样本，就无法回答这些核心问题：

- 它是否真的会稳定出信号
- 它的盈亏分布是否合理
- 它的退出逻辑是否有效
- 它的 long / short 表现是否失衡

这意味着：

- 当前最应该补的是“持续运行样本”，不是先继续拍脑袋改参数

### 2. 运行参数与策略源码默认值存在明显分离

策略源码 [auto_multi_ls_v2.py](/Users/wangjiangtao/Documents/AI/AI-OuYi/strategies/auto_multi_ls_v2.py) 里的默认值较保守：

- `stoploss = -0.05`
- `minimal_roi = {"0": 0.02}`
- `trailing_stop_positive = 0.02`

但运行时实际加载的 [auto_multi_ls_v2.json](/Users/wangjiangtao/Documents/AI/AI-OuYi/strategies/auto_multi_ls_v2.json) 参数明显更激进：

- `stoploss = -0.251`
- `roi` 首段 `0.253`
- `trailing_stop_positive = 0.147`

这会带来两个风险：

- 阅读源码的人容易误判真实运行逻辑
- 如果参数快照质量一般，运行表现会被超大止损和超大 ROI 目标扭曲

### 3. 当前运行参数看起来不像 15m 均值回归/趋势混合策略的稳健配置

从当前参数组合看：

- `ma_period = 276`
- `rsi_period = 15`
- `rsi_oversold = 26.6`
- `rsi_overbought = 78.6`
- `stoploss = -25.1%`
- `roi(0) = 25.3%`

这组参数更像是“极低频、极宽容持仓”的组合，而不是一个典型的 15m 合约策略稳健基线。

潜在问题：

- 入场可能过少
- 出场依赖极宽的利润区间
- 单笔风险容忍过大
- 在模拟盘里不容易快速积累有效样本

## 中优先级问题

### 4. 当前入场逻辑偏严格，可能造成低样本

当前 long 条件是：

- `close > ma`
- `ma_slope > 0`
- `rsi < oversold`

当前 short 条件是：

- `close < ma`
- `ma_slope < 0`
- `rsi > overbought`

这本质上是在“趋势方向里等极端反向摆动”。

问题不一定是错，但它天然会让信号变少。  
在 15m 级别，如果再叠加较长均线和较严格 RSI 阈值，很容易导致：

- 信号过 sparse
- 样本积累很慢
- 调参反馈周期过长

### 5. 当前退出条件可能过于粗糙

当前 long 退出：

- `rsi > rsi_overbought` 或 `close < ma`

当前 short 退出：

- `rsi < rsi_oversold` 或 `close > ma`

这套退出逻辑比较直接，但没有细分：

- 趋势继续时的持仓管理
- 回撤保护
- 震荡环境下的快速止盈止损

如果未来自然样本跑出来后发现大部分交易都由 `exit_signal` 平掉，这里大概率会成为重点优化区。

## 当前不能直接下的结论

下面这些判断，当前证据还不够：

- `MultiLsV2Strategy` 盈利能力差
- `MultiLsV2Strategy` 做空失效
- `exit_signal` 是当前主策略最大亏损来源
- 当前主策略只会做多不会做空

这些结论现在都更像是在描述旧的 `VolumeRatioStrategy` 样本，而不是当前主策略。

## 建议顺序

下一步最合理的顺序是：

1. 继续让 `MultiLsV2Strategy` 在当前 REST 基线下跑出自然样本
2. 等累计到第一批真实样本后，再看：
   - `pair-stats`
   - `exit-reason-stats`
   - `direction-stats`
3. 在样本足够后，再决定先动：
   - 入场阈值
   - 退出条件
   - ROI / trailing / stoploss

## 当前最可信的一句话

当前已经验证的是“执行链路可用”，还没有验证出“主策略有效”。
