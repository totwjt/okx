# AI-OuYi Web 管理系统规划

## 目标

建设一个 AI-OuYi 管理系统，用 Web 界面验证：

```text
策略资产数据库化
  -> runtime 生成物隔离
  -> 回测 / validation
  -> dry-run 模拟盘监控
  -> 风控与审计
```

第一阶段不是完整交易平台，而是验证当前 AI-OuYi 的 PostgreSQL strategy registry 和 Freqtrade 执行链路。

## 模块优先级

```text
P0: 策略管理
P0: 回测 / validation
P0: 运行产物与任务系统
P1: 实盘模拟 / dry-run 监控
P1: 风控系统
P2: 因子管理
P3: 用户模块
```

说明：用户原始优先级是 `策略管理 -> 回测 -> 实盘模拟 -> 风控 -> 因子 -> 用户`。这里补入“运行产物与任务系统”为 P0，因为它是数据库策略注册表和 Freqtrade 执行之间的连接层。

## 功能清单

### 策略管理

- 策略列表：读取 `strategy_specs`
- 策略详情：展示 spec JSON 摘要、状态、更新时间
- Profile 列表：读取 `strategy_profiles`
- Active profile 标识
- 晋级操作：写入 `strategy_promotion_events`
- 旧资产导入：触发 `registry import-files --source-dir ...`

验收：

- 所有策略事实来自 PostgreSQL
- 页面不读取 `strategies/generated/`、`strategies/auto_*`
- paper/live active 状态清晰可见

### 回测 / Validation

- 选择 strategy/profile/timerange
- 发起 backtest job
- 展示任务状态、日志、耗时
- 展示收益、最大回撤、交易数、胜率、profit factor
- Validation gate 展示 PASS/FAIL、failed checks、warnings
- 通过后允许 promote 到 `validated`

验收：

- 回测异步执行
- 结果可回查
- 不用 test timerange 调参

### 运行产物与任务系统

- Materialize：触发 `registry materialize <strategy_slug>`
- Runtime artifact 列表：读取 `strategy_runtime_artifacts`
- 展示文件路径、hash、artifact type、profile、生成时间
- Job 列表：导入、materialize、backtest、paper report 统一记录

验收：

- runtime 产物进入 `execution/freqtrade/user_data/runtime_strategies/`
- runtime 产物不进入 Git，不作为 AI 默认上下文

### 实盘模拟 / Dry-run 监控

- Freqtrade 状态、API 可达性
- 当前策略、runtime artifact、active profile 对齐检查
- 余额、持仓、最近交易
- daily report、pair stats、direction stats、exit reason stats

验收：

- 当前阶段只支持 `dry_run = true`
- 页面明确显示 REST baseline / WebSocket disabled 等运行状态

### 风控系统

- 风控规则展示
- 当前风险暴露
- 风控事件列表
- profile 晋级前置检查
- 异常提示：无自然样本、回撤超限、连续亏损、artifact 不匹配

### 因子管理

- funding rate 覆盖范围
- OHLCV 覆盖范围
- 数据缺口扫描
- 因子字典
- 因子与策略依赖关系

### 用户模块

- 登录
- 角色权限
- 高危操作确认
- 操作审计

## MVP 范围

- 策略注册表列表
- Profile 列表与状态
- Runtime materialize
- Runtime artifact 列表
- Backtest job 发起与结果占位
- 系统检查页：PostgreSQL、Docker、Freqtrade API、runtime 目录

