# Strategy Lifecycle Workspace 专项任务

更新: 2026-05-25

## 目标

建设一个独立的“策略生命周期工作台”，把单个 strategy/profile 从策略假设、策略定义、参数档案、运行产物、train 调优、validation 验证、test 留出测试、paper 模拟盘、live 候选到归档的全过程串联起来。

这个文件只管理策略生命周期相关任务。Web 通用脚手架、基础 API、页面布局仍以 `docs/tasks/TASKS.md` 为准。

## 核心原则

- 每个状态必须有中文语境解释、输入、输出、通过条件和阻塞原因。
- 每个 step 必须能对应到真实代码、数据库记录、runtime artifact 或 Freqtrade 执行动作。
- 晋级不是按钮行为，而是证据链通过后的状态流转。
- 调优过程必须有系统辅助，避免人工只凭最高收益选参数。
- `train / validation / test / custom` 必须作为数据用途区分，不能混用。
- `paper_active / live_candidate / live_active` 必须有审计、回滚和风险检查。

---

# STRATEGY-TASK-001

状态: done
负责人: codex
依赖: TASK-005, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012
优先级: P0
模块: strategy-lifecycle

目标:
- 新增策略生命周期工作台页面，按 strategy/profile 展示完整生命周期进度。

范围:
- 新增 `/lifecycle` 页面。
- 支持选择 strategy 和 profile。
- 展示生命周期主 step 和子 step。
- 展示当前状态、下一步建议、阻塞原因。
- 展示每个状态的中文解释。

不包含:
- 不做 profile 编辑。
- 不做自动调参。
- 不直接执行 live 操作。

验收:
- 页面能展示 `draft/generated/backtested/validated/paper_active/live_candidate/live_active/archived`。
- 每个状态能显示中文含义、实际关联文件/表/运行内容。
- 当前 profile 能显示已完成、待执行、阻塞、锁定四类 step 状态。
- 页面不读取 generated/runtime Python 正文。
- desktop/mobile 不出现横向溢出。

交付:
- `web/frontend/src/views/LifecycleView.vue`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/components/AppShell.vue`
- `web/frontend/src/api/lifecycle.ts`
- `web/backend/app/routers/lifecycle.py`
- `web/backend/app/services/lifecycle_service.py`

建议接口:
- `GET /api/lifecycle/strategies`
- `GET /api/lifecycle/{strategy_slug}`
- `GET /api/lifecycle/{strategy_slug}/profiles/{profile_name}`

备注:
- 第一版可以从 registry、jobs、validation、runtime artifacts、paper summary、risk summary、factors health 聚合数据。

---

# STRATEGY-TASK-002

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P0
模块: strategy-lifecycle

目标:
- 建立生命周期 step/substep 数据模型，让每一步有明确输入、输出、证据和 gate。

生命周期主 step:
- 策略假设
- 策略定义
- 参数档案
- 生成运行产物
- train 调优
- validation 验证
- test 留出测试
- paper 模拟盘
- live_candidate 实盘候选
- live_active 实盘生效
- archived 归档

每个 step 字段:
- `key`
- `title_zh`
- `description_zh`
- `required`
- `status`
- `inputs`
- `outputs`
- `evidence`
- `gate_checks`
- `blocked_reasons`
- `next_actions`

验收:
- 后端能返回统一 JSON。
- 前端能按 step/substep 渲染。
- 每个 step 至少有 1 个 evidence 或 blocked reason。
- 当前策略缺少数据时显示“缺失什么”，而不是空白。

交付:
- `web/backend/app/services/lifecycle_service.py`
- `web/frontend/src/api/lifecycle.ts`
- `web/frontend/src/views/LifecycleView.vue`

---

# STRATEGY-TASK-003

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P0
模块: strategy-evidence

目标:
- 新增 Strategy Evidence Gate，防止证据不足的 profile 被误晋级。

检查项:
- 最小回测交易数。
- 最小 validation 交易数。
- train/validation/test 区间是否分离。
- 最大回撤是否超过阈值。
- profit factor 是否达标。
- long/short 是否严重失衡。
- exit reason 是否过度集中。
- 是否存在数据缺口。
- 是否存在 runtime artifact drift。
- 是否有足够 paper 自然成交样本。
- 是否混入 force-enter / force-exit 样本。

验收:
- `validated` 晋级必须通过 validation evidence。
- `paper_active` 晋级必须通过 validation + test 基础检查。
- `live_candidate` 晋级必须通过 paper evidence。
- 未通过时返回明确 failed checks。
- Web 显示每条 failed check 的中文解释。

交付:
- `web/backend/app/services/evidence_gate_service.py`
- `web/backend/app/routers/lifecycle.py`
- `web/frontend/src/views/LifecycleView.vue`

建议接口:
- `POST /api/lifecycle/{strategy_slug}/profiles/{profile_name}/evidence-check`

---

# STRATEGY-TASK-004

状态: done
负责人: codex
依赖: STRATEGY-TASK-003
优先级: P0
模块: strategy-promotion

目标:
- 补齐 profile 从 `validated` 到 `paper_active/live_candidate/live_active` 的 Web 晋级流程。

范围:
- 显示晋级前置检查。
- 必填晋级 reason。
- 写入 `strategy_promotion_events`。
- 晋级前执行 evidence gate。
- 对 `paper_active/live_active` 做唯一性约束。
- 支持降级到 `validated` 或 `archived`。

不包含:
- 第一版不执行真实实盘开关。
- 第一版不提供 force-enter/force-exit。

验收:
- 未通过 gate 不允许晋级。
- 晋级成功后 profile 状态更新。
- promotion event 可回查。
- Web 清晰显示“为什么不能晋级”。

交付:
- `web/backend/app/routers/lifecycle.py`
- `web/backend/app/services/lifecycle_service.py`
- `web/frontend/src/views/LifecycleView.vue`

建议接口:
- `POST /api/lifecycle/{strategy_slug}/profiles/{profile_name}/promote`
- `POST /api/lifecycle/{strategy_slug}/profiles/{profile_name}/demote`

---

# STRATEGY-TASK-005

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P0
模块: strategy-runtime

目标:
- 新增 runtime alignment & drift check，确保数据库声明、runtime artifact 和 Freqtrade 实际运行一致。

检查项:
- 当前 active profile。
- 最新 runtime artifact hash。
- Freqtrade 当前 strategy。
- Freqtrade 当前 config。
- `max_open_trades` 是否一致。
- strategy/profile/config/artifact 是否属于同一生命周期版本。

验收:
- Lifecycle 页面顶部显示 alignment 状态。
- drift 时显示红色阻塞原因。
- drift 时禁止晋级到 `paper_active/live_candidate/live_active`。

交付:
- `web/backend/app/services/runtime_alignment_service.py`
- `web/backend/app/services/lifecycle_service.py`
- `web/frontend/src/views/LifecycleView.vue`

---

# STRATEGY-TASK-006

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P0
模块: strategy-paper

目标:
- 新增 Paper Run Ledger，把模拟盘运行变成可追踪证据，而不是只看当前 Freqtrade 状态。

字段:
- run name
- started_at
- ended_at
- strategy_slug
- profile_name
- artifact_hash
- config_hash
- dry_run mode
- start_balance
- current_balance
- natural_closed_trades
- force_trades
- pnl
- max_drawdown
- status
- review_conclusion

状态建议:
- `collecting_samples`
- `ready_for_review`
- `review_failed`
- `review_passed`
- `stopped`

验收:
- Web 能展示当前 paper run。
- 能区分自然成交和人工 force 交易。
- 样本不足时显示 `COLLECT_MORE_SAMPLES`。
- 样本达到阈值后显示 `READY_FOR_REVIEW`。

交付:
- `web/backend/app/services/paper_run_service.py`
- `web/backend/app/routers/lifecycle.py`
- `web/frontend/src/views/LifecycleView.vue`

建议接口:
- `POST /api/lifecycle/paper-runs`
- `GET /api/lifecycle/paper-runs/current`
- `POST /api/lifecycle/paper-runs/{run_id}/review`

---

# STRATEGY-TASK-007

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P1
模块: strategy-optimization

目标:
- 设计并实现调优助手第一版，帮助用户生成、比较和筛选候选 profile。

范围:
- 显示可调参数列表。
- 显示参数合理边界。
- 支持基于 baseline 生成候选 profile 草案。
- 对候选 profile 展示 diff。
- 对 train 回测结果做综合评分。
- 标记低样本、过高回撤、参数极端、train/validation 衰减。

不包含:
- 第一版不强制接入完整 hyperopt。
- 第一版可以先支持人工候选 + 系统评分。

评分维度:
- total profit
- max drawdown
- profit factor
- trades
- winrate
- trades per day
- long/short balance
- train-to-validation decay

验收:
- 页面能解释“为什么推荐/不推荐某个候选”。
- 候选不能只按收益排序。
- 低交易数候选必须被标记。
- 可以把候选保存为 draft profile。

交付:
- `web/backend/app/services/optimization_service.py`
- `web/backend/app/routers/optimization.py`
- `web/frontend/src/api/optimization.ts`
- `web/frontend/src/views/LifecycleView.vue`

---

# STRATEGY-TASK-008

状态: done
负责人: codex
依赖: STRATEGY-TASK-007
优先级: P1
模块: strategy-optimization

目标:
- 接入自动调优任务，支持 train 区间批量生成候选参数。

范围:
- 支持 grid search / random search / Freqtrade hyperopt 其中一种或多种。
- 每次调优必须绑定 train timerange。
- 输出候选 profile。
- 自动跑候选 train backtest。
- 根据评分规则排序。

风险控制:
- 参数范围必须来自 spec/profile schema 或人工配置。
- 禁止在 test 区间调参。
- 禁止把 custom 区间结果默认作为晋级证据。

验收:
- 能从 baseline 生成至少 3 个候选 profile。
- 每个候选都有 diff、指标、评分、风险提示。
- 调优结果不会自动晋级，只进入候选池。

交付:
- `web/backend/app/services/optimization_service.py`
- `web/backend/app/services/jobs_service.py`
- `web/frontend/src/views/LifecycleView.vue`

---

# STRATEGY-TASK-009

状态: done
负责人: codex
依赖: STRATEGY-TASK-003
优先级: P1
模块: strategy-backtest

目标:
- 建立 train / validation / test / custom 回测用途管控。

规则:
- `train`: 可以调参，不可单独晋级。
- `validation`: 用于 `validated` gate。
- `test`: 用于进入 `paper_active/live_candidate` 前的留出检查。
- `custom`: 用于诊断，默认不参与晋级。

验收:
- Web 发起回测时必须选择 phase。
- phase 有中文解释。
- `test` 结果被使用过后，页面提示避免反复调参污染。
- `custom` 结果不能默认作为 promotion evidence。

交付:
- `web/frontend/src/views/BacktestsView.vue`
- `web/frontend/src/views/LifecycleView.vue`
- `web/backend/app/services/evidence_gate_service.py`

---

# STRATEGY-TASK-010

状态: done
负责人: codex
依赖: STRATEGY-TASK-001
优先级: P1
模块: strategy-thesis

目标:
- 为每个 strategy/profile 增加策略假设与复盘记录。

字段:
- 策略一句话描述。
- 收益来源假设。
- 适用市场状态。
- 不适用市场状态。
- 失效条件。
- 观察指标。
- 复盘结论。
- 下一步动作。

验收:
- Lifecycle 页面能展示 thesis。
- 缺少 thesis 时阻塞进入 `live_candidate`。
- 每次 promotion 必须关联一条 reason 或 review note。

交付:
- `web/backend/app/services/lifecycle_service.py`
- `web/frontend/src/views/LifecycleView.vue`

备注:
- 如果数据库暂时没有表，第一版可以先存在 profile `validation` JSON 的 `thesis` 字段，后续再迁移独立表。

---

# 推荐执行顺序

```text
STRATEGY-TASK-001 生命周期工作台页面
STRATEGY-TASK-002 step/substep 数据模型
STRATEGY-TASK-003 evidence gate
STRATEGY-TASK-005 runtime drift check
STRATEGY-TASK-004 promotion workflow
STRATEGY-TASK-006 paper run ledger
STRATEGY-TASK-009 回测用途管控
STRATEGY-TASK-007 调优助手第一版
STRATEGY-TASK-008 自动调优任务
STRATEGY-TASK-010 策略假设与复盘记录
```

## 新线程启动提示词

```text
请读取 docs/tasks/TASK_STRATEGY.md，先实现 STRATEGY-TASK-001 和 STRATEGY-TASK-002。
目标是新增策略生命周期工作台，让每个 strategy/profile 的状态、step、substep、证据、阻塞原因、下一步动作都能在 Web 中清晰展示。
实现前先阅读 docs/tasks/STRATEGY_WEB_FLOW_REVIEW.md、docs/web-management/PRODUCT_PLAN.md、strategies/STRATEGY_LIFECYCLE.md。
```
