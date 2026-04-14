# 激进策略梳理（2026-04-10）

## 结论先行

当前仓库里“激进策略”有两种表达：

1. 名义上的激进分支：`scalping_v1`
2. 实际更接近当前主线的激进版本：`grid_ls_v1` + 激进 profile 链

从仓库现状看，真正需要梳理的主对象不是单独的 `scalping_v1`，而是：

- 基础 spec：`grid_ls_v1`
- 当前激活 profile：`candidate_pf_20260409_w`
- 运行快照：`auto_grid_ls_v1.py` / `auto_grid_ls_v1.json`

也就是说，当前混乱并不主要是“代码写错了”，而是“策略定义层”和“运行层”表达不一致，导致阅读成本很高。

## 当前真实运行主线

当前 `grid_ls_v1` 的 active profile 是：

- `strategies/profiles/grid_ls_v1/_active.yaml`
- 值：`candidate_pf_20260409_w`

该 profile 的核心参数是：

- `timeframe`: `15m`
- `stoploss`: `-0.11`
- `minimal_roi`: `{"0": 0.0322, "60": 0.0118, "240": 0.0}`
- `trailing_stop_positive`: `0.012`
- `trailing_stop_positive_offset`: `0.02`
- `ma_period`: `54`
- `rsi_period`: `11`
- `rsi_oversold`: `34`
- `rsi_overbought`: `66`
- `bb_period`: `38`
- `bb_std`: `1.9`
- `volume_ratio_threshold`: `0.9`

这套参数已经不是基础 spec 默认值，而是 profile 覆盖后的结果。

## 当前策略逻辑的实际结构

### 1. 策略定位

`grid_ls_v1` 本质上不是纯网格，也不是纯趋势。

它是一个双入口模型：

- 模型 A：低 ADX 下的布林带边缘均值回归
- 模型 B：顺趋势方向上的回撤抄底 / 反弹做空

因此它更准确的名字应该是：

- `Range Reversion + Trend Pullback`

而不是狭义“网格策略”。

### 2. Long 入场

当前 long 入场可以拆成两类：

1. 震荡均值回归多头
   - `adx <= 23`
   - `close <= bb_lower * 1.002`
   - `rsi <= oversold`

2. 趋势回撤多头
   - `ema_fast > ema_slow`
   - `zscore <= -0.9`
   - `atr_pct <= 0.032`

再叠加一个全局过滤：

- `volume_ratio >= threshold`

### 3. Short 入场

当前 short 入场与 long 对称：

1. 震荡均值回归空头
   - `adx <= 23`
   - `close >= bb_upper * 0.998`
   - `rsi >= overbought`

2. 趋势反弹空头
   - `ema_fast < ema_slow`
   - `zscore >= 0.9`
   - `atr_pct <= 0.032`

再叠加：

- `volume_ratio >= threshold`

### 4. Exit 逻辑

当前退出也是对称的，但比较粗：

long 退出：

- 回到 `bb_middle`
- 或 RSI 修复到中性偏强
- 或波动率过高：`atr_pct >= 0.045`

short 退出：

- 回到 `bb_middle`
- 或 RSI 修复到中性偏弱
- 或波动率过高：`atr_pct >= 0.045`

### 5. 风控结构

策略层自带三类保护：

- `CooldownPeriod`
- `StoplossGuard`
- `MaxDrawdown`

同时交易所主配置还有一层运行约束：

- `config.json` 里 `max_open_trades = 3`

这和 profile / spec 里的 `max_open_trades = 4` 不一致，最终以运行配置为准。

## 当前混乱的根源

### 1. “激进策略”被拆散在两条线里

现在仓库里有一条显式命名为激进的 `scalping_v1`，但当前运行主线不是它。

同时 `grid_ls_v1` 的激进化又是通过 profile 链逐步演化出来的。

结果就是：

- 看 spec 的人以为主线是一个 15m 网格回归策略
- 看 `scalping_v1` 的人以为主线是一个 5m 超短线策略
- 看 active profile 的人才知道当前真正跑的是哪套参数

这会直接导致认知分裂。

### 2. “基础逻辑”和“运行参数”不在一个地方

当前主线逻辑分散在四层：

1. `spec/*.yaml`
2. `profiles/*/*.yaml`
3. `generated/*.py`
4. `auto_*.json`

其中：

- `spec` 定义结构
- `profile` 改参数
- `generated` 落最终代码
- `auto_json` 再写运行参数快照

这是合理的工程分层，但目前缺少“当前运行画像”的统一视图，所以读起来像四套系统。

### 3. 策略名字不能准确表达行为

`grid_ls_v1` 这个名字会误导人以为它是：

- 密集挂单
- 分层补仓
- 明确网格层级

但实际代码里并没有典型 grid engine。

它更像：

- 带布林极值触发的均值回归信号策略

名字和行为不一致，会放大理解偏差。

### 4. 激进程度主要体现在参数，不体现在结构说明

当前“激进”主要来自这些参数收紧 / 放宽：

- 更短的 RSI / MA 周期
- 更低的 volume 门槛
- 更高的 ROI 首段目标
- 更宽的 stoploss
- 更积极的 trailing

但仓库里缺少一份明确说明：

- 哪些参数代表“激进”
- 为什么这些参数会更激进
- 激进后换来了什么，牺牲了什么

所以现在只能靠猜。

## 专业化后的结构化理解

如果按策略工程视角重述，当前主线应该写成下面这套结构：

### 策略内核

- 类型：双边合约短中频信号策略
- 周期：`15m`
- 风格：激进型均值回归 + 趋势回撤混合
- 适用品种：高波动、高流动性永续合约，如 `SOL`

### 入场模块

- `Range Reversion`
  - 负责震荡市边缘反转
- `Trend Pullback`
  - 负责趋势中的反向回撤切入
- `Liquidity Filter`
  - 负责过滤低成交量时段

### 出场模块

- `Mean Reversion Exit`
  - 回到中轨就兑现
- `Momentum Repair Exit`
  - RSI / zscore 回归后兑现
- `Volatility Abort`
  - 波动恶化直接退出

### 风险模块

- 单笔风险：`stoploss`
- 收益锁定：`ROI + trailing`
- 组合保护：`Cooldown + StoplossGuard + MaxDrawdown`
- 运行上限：`config.json` 的 `max_open_trades`

## 我对当前策略的判断

### 优点

- 逻辑没有乱到不可用，核心框架是自洽的
- long / short 基本对称，便于做双边市场
- 通过 profile 可以快速切换标的适配版本
- 当前 active profile 有验证集结果，说明不是完全拍脑袋

### 真正的问题

真正乱的不是交易条件本身，而是“表达方式”：

- 策略命名不准
- 当前运行版本缺少总览文档
- spec/profile/runtime/config 存在多层覆盖
- 仓库里同时存在历史主线和实验分支，边界不够硬

### 风险点

1. `volume_ratio_threshold` 在生成代码里是 `DecimalParameter(1.0, 2.5, default=0.9, ...)`
   - 默认值低于下界，说明生成器参数边界和实际默认值存在不一致
2. `config.json` 的 `max_open_trades = 3` 与 spec/profile 的 `4` 不一致
   - 会让策略层风险设定和运行层结果不一致
3. `scalping_v1` 和 `grid_ls_v1` 共享相似信号骨架
   - 但仓库没有明确说明两者是“独立分支”还是“同一思想的不同周期实现”

## 建议的整理顺序

### 第一阶段：先统一认知，不急着改交易逻辑

建议先做三件事：

1. 给当前主线重新定义一句话描述
   - 例如：`15m 激进型 Range-Reversion / Trend-Pullback 混合策略`
2. 补一份“当前运行画像”
   - 明确 active profile、关键参数、运行 config 覆盖项
3. 明确 `scalping_v1` 和 `grid_ls_v1` 的关系
   - 是废弃分支、实验分支，还是待合并分支

### 第二阶段：再整理工程边界

建议把策略分层固定成：

1. `spec`
   - 只放结构，不表达“当前最佳参数”
2. `profile`
   - 只放标的适配和风格差异
3. `generated/auto`
   - 只作为产物，不作为阅读入口
4. `docs`
   - 单独维护“当前实盘/模拟盘实际运行版本”

### 第三阶段：最后再动逻辑

如果后续要继续专业化，我建议优先改这三处：

1. 把 entry 明确拆成两个布尔模块并打 tag
   - `range_revert_long`
   - `trend_pullback_long`
   - `range_revert_short`
   - `trend_pullback_short`
2. 把 exit 从“一个大 or 条件”拆成分层退出原因
   - 便于后续统计哪类退出最伤收益
3. 把激进版本做成单独 profile family
   - 例如 `sol_aggressive_v2`
   - 不要继续沿着 `candidate_pf_20260409_*` 链无限叠代

## 当前最适合你的下一步

如果你的目标是“把这套激进策略变得可维护”，那最该先做的不是继续调参数，而是先做：

- 命名澄清
- 分层澄清
- 当前运行画像固化

如果你的目标是“直接提升策略质量”，那下一步应该是我帮你把 `grid_ls_v1` 重构成更清晰的模块化 spec / generated 代码，让每个 entry / exit 子逻辑都能单独解释和统计。
