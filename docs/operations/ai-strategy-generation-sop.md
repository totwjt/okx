# AI 策略生成操作 SOP

更新: 2026-05-26

## 核心结论

AI 生成策略时，系统 API 只负责固定、机械、可审计的流程动作；需要发散思维和专业策略知识的环节必须由 AI 主动完成，并写清判断依据。

换句话说：

- API 负责登记、保存、生成产物、记录证据、推进生命周期。
- AI 负责提出交易假设、设计 spec、设定参数边界、判断风险、解释结果、发现系统级问题。
- 不能把 Web scaffold 当成最终策略。scaffold 只用于打通流程。
- 不能只生成 `.py`。完整策略最小闭环是 hypothesis -> spec -> profile -> registry -> materialize -> static check。
- 发现问题时先判断作用域：如果影响一类策略或生成链路，必须上升为系统级问题；如果只影响当前参数或当前策略，才作为策略级问题处理。

每次 AI 生成策略，开工前必须明确声明：

```text
本次按 docs/operations/ai-strategy-generation-sop.md 执行。
当前 Step: 1/10 策略假设登记。
```

执行中每完成一步，必须推进 Step，并说明：

- 本步 AI 做了什么专业判断。
- 本步调用了哪些 API 或 CLI。
- 本步产物在哪里。
- 是否发现策略级或系统级问题。

## 角色分工

| 类型 | 由谁完成 | 说明 |
|---|---|---|
| 策略假设、市场结构、交易逻辑 | AI | 必须体现专业判断，不能只复述用户标题 |
| spec 设计、指标组合、入出场条件 | AI | 必须给出合理参数、风险边界、失效条件 |
| profile 参数档案 | AI + API | AI 设计参数，API/CLI 写入注册表 |
| 注册表建档 | API | 固定机械步骤 |
| 生成运行产物 | API/CLI | 固定机械步骤，可由终端命令辅助完成 |
| 静态校验 | AI + 命令 | AI 判断校验项，命令执行编译/检查 |
| 数据准备 | Web Job API | 固定动作，但 AI 要判断数据是否足够 |
| 回测和 evidence gate | Web Job API | 固定动作，AI 解释结果 |
| 晋级决策 | AI + 人工确认 | AI 给建议，paper/live 必须人工确认 |
| 系统缺陷识别 | AI | 影响流程一致性的必须上升为系统优化点 |

## 标准 Step

### Step 1: 策略假设登记

目标：把用户的策略想法转成可研究的交易假设。

AI 必须完成：

- 明确交易市场：交易所、品种、合约/现货、方向限制。
- 明确策略类型：趋势、均值回归、网格、突破、急跌反弹、套利等。
- 写出可证伪假设，不允许只有“赚钱”目标。
- 写出适用市场环境和失效环境。
- 写出主要风险：单边下跌、震荡磨损、滑点、流动性、资金费率、过拟合等。
- 给出初始研究边界：timeframe、样本区间、是否允许做空、最大持仓数。

可用 API：

```text
POST /api/strategies
GET  /api/strategies
GET  /api/strategies/{slug}
```

登记内容建议：

```json
{
  "slug": "okx_sol_crash_rebound_v1",
  "name": "OKX SOL 急跌抄底策略",
  "description": "面向 OKX SOL/USDT 永续合约的急跌反弹研究策略。",
  "profile_name": "default",
  "thesis": {
    "market": "OKX SOL/USDT:USDT futures",
    "hypothesis_zh": "短时急跌后，在放量恐慌和超卖条件共同确认时存在均值回归反弹。",
    "invalidation_zh": "如果样本外成交过少、连续止损或回撤超限，应降级或废弃。",
    "risk_note_zh": "研究策略，非实盘建议。"
  }
}
```

禁止：

- 直接跳到写 Python 策略。
- 只写策略名，不写 thesis。
- 未明确 `can_short`、交易模式和目标市场。

### Step 2: 生成或补齐策略 spec

目标：由 AI 根据专业策略知识生成可执行、可审计、可验证的 spec。

AI 必须完成：

- 选择合理指标和派生指标。
- 设计入场条件、出场条件、止损、ROI、追踪止盈。
- 设计风险模型：最大持仓、最大回撤、连续亏损冷却、单日亏损边界。
- 明确 train / validation / test 区间，且不能用 test 调参。
- 明确参数范围，避免只写固定值。
- 明确是否允许做空，并保证生成器应尊重该字段。
- 检查指标是否由生成器支持；不支持时要么扩展生成器，要么调整 spec。

当前可用 API：

```text
POST /api/strategies/{slug}/definition/scaffold
PUT  /api/strategies/{slug}/definition
```

注意：

- 这个 API 只能生成保守通用模板。
- 如果用户给的是具体策略，例如“急跌抄底”“资金费率套利”“趋势突破”，AI 必须补齐专业 spec，不能把 scaffold 当最终结果。
- AI 补齐专业 spec 后，应优先用 `PUT /api/strategies/{slug}/definition` 写入注册表，而不是手工写 YAML 后再导入。
- `PUT /api/strategies/{slug}/definition` 会做保存前校验：必备字段、条件表达式、生成器产物编译。校验失败时必须先修复 spec，不能绕回手工 YAML。

完整 spec 写入示例：

```json
{
  "spec": {
    "name": "OKX SOL 超卖反弹确认策略 V3",
    "description": "完整策略说明",
    "timeframe": "15m",
    "trading_mode": "futures",
    "can_short": false,
    "factors": {},
    "entry_conditions": {},
    "exit_conditions": {},
    "risk_model": {}
  },
  "profile_name": "default",
  "profile_overrides": {},
  "profile_status": "candidate",
  "source": "ai_generated_spec",
  "activate_profile": true
}
```

过渡期备份文件方式：

```text
strategies/spec/<slug>.yaml
strategies/profiles/<slug>/default.yaml
strategies/profiles/<slug>/_active.yaml
```

仅当 API 不可用或需要批量恢复时，用 CLI 导入注册表：

```bash
DATABASE_URL=postgresql://<user>:<password>@127.0.0.1:5432/ouyi_db \
  .venv/bin/python strategies/cli.py registry import-files
```

spec 必备字段：

```text
name
description
version
status
market
timeframe
trading_mode
margin_mode
can_short
train_timerange
validation_timerange
test_timerange
cost_model
risk_model
minimal_roi
stoploss
trailing_stop
optimization
factors
derived_indicators
entry_conditions
exit_conditions
```

### Step 3: 生成 profile 参数档案

目标：把策略默认参数和候选参数作为 profile 管理，而不是散落在代码中。

AI 必须完成：

- 说明 default profile 是保守、激进还是均衡。
- 写出核心参数 overrides。
- 写出参数设计理由。
- 明确 profile 状态，通常从 `draft` 或 `candidate` 开始。
- 如果从优化结果导入 profile，必须记录来源和时间。

可用 API：

```text
POST /api/strategies/{slug}/profiles
POST /api/strategies/{slug}/profiles/{profile_name}/defaults
PUT  /api/strategies/{slug}/profiles/{profile_name}/overrides
GET  /api/strategies/{slug}/profiles
```

过渡期可用 CLI：

```bash
.venv/bin/python strategies/cli.py profile list <slug>
.venv/bin/python strategies/cli.py profile show <slug> <profile>
```

### Step 4: 写入或同步注册表

目标：让 Web 控制台、生命周期、materialize 都从同一份注册表读取策略。

AI 必须完成：

- 确认注册表中只有目标策略或目标策略状态正确。
- 确认 active profile 正确。
- 确认 spec JSON 与预期一致。

可用 API：

```text
GET /api/strategies
GET /api/strategies/{slug}
GET /api/strategies/{slug}/profiles
```

可用 CLI：

```bash
.venv/bin/python strategies/cli.py registry list
.venv/bin/python strategies/cli.py registry show <slug> --profile <profile>
.venv/bin/python strategies/cli.py registry import-files
```

### Step 5: 生成运行产物

目标：从注册表生成 Freqtrade 可运行的 Python 策略和参数 JSON。

AI 必须完成：

- 使用 API 或 CLI materialize，不手工编辑 runtime 产物。
- 记录生成文件路径和 artifact hash。
- 生成失败时判断是 spec 问题、profile 问题，还是生成器系统问题。

可用 API：

```text
POST /api/runtime/materialize
GET  /api/runtime/artifacts
```

可用 CLI：

```bash
.venv/bin/python strategies/cli.py registry materialize <slug> --profile <profile>
```

运行产物目录：

```text
execution/freqtrade/user_data/runtime_strategies/
execution/freqtrade/user_data/runtime_params/
```

禁止：

- 手工修改 `auto_<slug>.py`。
- 把 runtime 产物当长期源码维护。
- 单独维护 Docker 策略副本。

### Step 6: 静态校验

目标：在回测前发现明显错误。

AI 必须检查：

- 生成代码可以编译。
- `class_name` 正确。
- `timeframe` 正确。
- `can_short` 与 spec 一致。
- entry/exit 引用的 dataframe 字段都已生成。
- 参数名与生成器输出一致。
- 只做多策略不得生成真实 short 入场。
- 风控 protections 是否符合 spec。

建议命令：

```bash
python3 -m py_compile execution/freqtrade/user_data/runtime_strategies/auto_<slug>.py
rg -n "can_short|enter_short|entry_condition|exit_condition" execution/freqtrade/user_data/runtime_strategies/auto_<slug>.py
```

问题分级：

- 如果只是当前 spec 条件写错，修当前策略。
- 如果生成器无视 spec、漏生成指标、参数 JSON 不完整，升级为系统级问题并修生成器。

### Step 7: 数据准备

目标：保证回测数据足够覆盖 train / validation / test。

AI 必须完成：

- 检查目标 pair/timeframe 数据是否存在。
- 检查数据覆盖区间是否匹配 timerange。
- 对合约策略，检查 mark、funding、leverage tiers 等是否需要。
- 明确数据缺口是否会阻塞回测。

优先使用 Web Job API：

```text
POST /api/data/ensure
GET  /api/jobs/{job_id}
GET  /api/factors/health
```

示例 payload：

```json
{
  "strategy_slug": "okx_sol_crash_rebound_v1",
  "profile_name": "default",
  "timerange": "20250101-20260526",
  "no_parallel_download": true,
  "timeout_seconds": 1800
}
```

说明：

- 不传 `pair` 时使用 `spec.market.pair`。
- 不传 `timeframe` 时使用 `spec.timeframe`。
- 不传 `trading_mode` 时使用 `spec.trading_mode`。
- 不传 `timerange` 时，系统会从 train / validation / test 推导需要的数据区间。
- API 底层可使用 Docker/Freqtrade 命令，但 AI 不应把它作为人工终端步骤暴露给用户。

常见检查路径：

```text
execution/freqtrade/user_data/data/okx/
execution/freqtrade/user_data/external_data/
```

### Step 8: 回测与验证

目标：用固定样本推进证据，不用测试集反复调参。

AI 必须完成：

- train 只用于调参或初筛。
- validation 用于 gate。
- test 只做最后留出确认。
- 解释收益、回撤、交易数、利润因子、胜率、平均收益。
- 如果交易数太少，不能把高收益当有效结论。

优先使用 Web Job API：

```text
POST /api/jobs
GET  /api/jobs/{job_id}
GET  /api/backtests/results
GET  /api/validation/results
```

Backtest 示例：

```json
{
  "job_type": "backtest",
  "payload": {
    "strategy_slug": "okx_sol_crash_rebound_v1",
    "profile_name": "default",
    "phase": "validation",
    "timerange": "20251001-20251130",
    "force": true,
    "timeout_seconds": 900
  }
}
```

Validation 示例：

```json
{
  "job_type": "validation",
  "payload": {
    "strategy_slug": "okx_sol_crash_rebound_v1",
    "profile_name": "default",
    "timerange": "20251001-20251130",
    "min_trades": 5,
    "min_profit_factor": 1.0,
    "force": true,
    "timeout_seconds": 900
  }
}
```

保留 CLI 作为故障排查和本地调试工具，不作为标准流程入口。

### Step 9: 生命周期推进

目标：状态晋级必须有证据和事件。

AI 必须完成：

- 给出是否晋级的建议和理由。
- 不得自动把未验证策略推进到 paper/live。
- `paper_active`、`live_candidate`、`live_active` 必须要求人工确认。

可用 API：

```text
POST /api/lifecycle/{strategy_slug}/profiles/{profile_name}/evidence-check
POST /api/lifecycle/{strategy_slug}/profiles/{profile_name}/promote
POST /api/lifecycle/paper-runs
POST /api/lifecycle/paper-runs/{run_id}/review
```

### Step 10: 收尾与报告

目标：让下一位 AI 或人工能接手。

AI 必须报告：

- 当前 Step 完成到哪里。
- 生成了哪些文件和 API 记录。
- Web 控制台能看到什么。
- 哪些验证已完成，哪些因为数据或环境未完成。
- 策略级问题清单。
- 系统级优化点清单。

## API 与 AI 分工总表

| 流程 | 是否必须 | API 是否可做 | AI 专业判断是否必须 | 备注 |
|---|---:|---:|---:|---|
| 策略假设登记 | 是 | 是 | 是 | API 存储，AI 设计 thesis |
| spec 生成/补齐 | 是 | 部分 | 是 | scaffold 不能替代专业 spec |
| profile 生成 | 是 | 是 | 是 | AI 设计参数，API 保存 |
| 注册表同步 | 是 | 是 | 否 | 机械步骤 |
| materialize | 是 | 是 | 否 | 机械步骤，优先使用 Web job |
| 静态校验 | 是 | 部分 | 是 | AI 判断一致性 |
| 数据准备 | 回测前必须 | 是 | 是 | `POST /api/data/ensure`，AI 判断数据是否足够 |
| train 回测 | 验证前必须 | 是 | 是 | `POST /api/jobs`，AI 解释结果 |
| validation gate | 晋级前必须 | 是 | 是 | API 检查阈值，AI 判断质量 |
| test 留出 | 实盘前必须 | 是 | 是 | `POST /api/jobs`，禁止用来调参 |
| paper run | 实盘前必须 | 是 | 是 | 人工确认 |
| promote | 生命周期必须 | 是 | 是 | paper/live 必须人工确认 |

## 系统级问题判断标准

遇到问题时，AI 必须按以下标准判断是否上升为系统级问题：

| 现象 | 处理级别 |
|---|---|
| 某个参数阈值不合理 | 当前策略级 |
| 某个 entry/exit 条件过严或过松 | 当前策略级 |
| 生成器不尊重 spec 字段，例如 `can_short` | 系统级 |
| API scaffold 产物被误用为最终策略 | 系统级流程问题 |
| registry、runtime artifact、profile 状态不一致 | 系统级 |
| Web 无法展示必要证据或失败原因 | 系统级 |
| 数据缺失导致无法回测 | 先使用 `POST /api/data/ensure`；API 不足时上升为系统级 |
| test 结果被用于反复调参 | 流程违规 |

系统级问题必须输出：

- 问题描述。
- 影响范围。
- 当前是否已修。
- 推荐新增的 API、校验或 UI 提示。

## 当前系统优化点

### P0: 新增 AI spec 生成 API

建议新增：

```text
POST /api/strategies/{slug}/definition/ai-generate
```

作用：

- 输入 thesis、市场、策略类型、风险偏好。
- 输出完整 spec 草案。
- 明确标记哪些字段来自 AI 判断。

### P0: 新增 spec/code 一致性校验 API

建议新增：

```text
POST /api/strategies/{slug}/definition/validate
```

必须校验：

- `can_short` 一致性。
- `timeframe` 一致性。
- entry/exit 引用字段存在。
- derived indicators 能生成。
- profile overrides 可应用。
- futures/spot 字段合法。

### P0: 新增 materialize-and-check API

建议新增：

```text
POST /api/strategies/{slug}/pipeline/materialize-and-check
```

作用：

- materialize。
- 编译生成文件。
- 跑一致性校验。
- 返回 artifact hash 和检查结果。

### P1: Web scaffold 必须改名或加警告

当前“生成基础定义”容易被误认为“生成可用策略”。

建议 UI 文案改为：

```text
生成流程模板
```

并显示：

```text
该模板只用于打通流程，不代表 AI 专业策略设计。
```

### P1: 增加策略生成 Step 记录表

建议新增表：

```text
strategy_generation_steps
```

记录：

- strategy_slug
- step_name
- status
- ai_notes
- api_calls
- artifacts
- issues
- created_at / updated_at

这样 Web 可以显示“AI 当前推进到第几步”。

### P1: 数据覆盖检查 API

已完成基础数据确保接口：

```text
POST /api/data/ensure
```

仍建议新增覆盖检查接口：

```text
GET  /api/data/coverage
```

作用：

- 按 strategy/profile/timerange 检查 pair/timeframe 覆盖。
- 检查 futures、mark、funding_rate 是否齐全。
- 返回缺口、首尾时间、缺失 interval 样本。

### P1: Web Job API 已接入数据确保和回测

已完成：

```text
POST /api/data/ensure
POST /api/jobs        job_type=data_ensure
POST /api/jobs        job_type=backtest
POST /api/jobs        job_type=validation
GET  /api/jobs/{id}
```

说明：

- API/job 底层封装 Docker/Freqtrade 命令。
- 不要求 `freqtrade` 容器常驻运行。
- 终端命令保留为故障排查手段，不作为 AI 标准操作入口。

### P2: profile 参数编辑器增强

Web 需要支持结构化编辑：

- factor 参数。
- ROI 阶梯。
- stoploss。
- trailing。
- risk_model。

### P2: 回测结果解释层

Web 可以增加 AI summary 字段：

- 结果是否可信。
- 交易数是否足够。
- 是否过拟合。
- 下一步建议。

## 最小验收清单

AI 完成一次策略生成后，至少要能回答：

- 使用了本 SOP 的哪些 Step。
- 策略假设是什么，失效条件是什么。
- spec 在哪里，profile 在哪里。
- 注册表是否能查到。
- runtime artifact 是否生成。
- 静态校验是否通过。
- 是否有历史数据，是否完成回测。
- 哪些问题是当前策略级，哪些是系统级。
