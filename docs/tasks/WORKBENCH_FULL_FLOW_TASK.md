# 工作台全流程操作化任务

更新: 2026-05-25

## 背景

目标是让 Web 工作台从“策略创建”开始，能够操作并推进完整策略生命周期，而不是只展示已有策略的状态。

当前方向已经确定：

```text
策略假设
  -> 策略定义
  -> 参数档案
  -> 生成运行产物
  -> train 调优
  -> validation 验证
  -> test 留出测试
  -> paper 模拟盘
  -> live_candidate / live_active
  -> archived
```

工作台是主操作入口；任务历史、回测记录、运行产物、模拟盘记录可以跳转到专门路由查看。

## 当前已完成

1. `生命周期工作台` 已改为 `工作台`。
2. 工作台支持新增策略草稿。
3. 工作台支持新增参数档案草稿。
4. Thesis 已有编辑保存入口，并改为选填，不再阻塞流程。
5. 流程 step 内已经承载操作按钮，而不是集中在顶部操作区。
6. 已新增后端能力：
   - 生成基础策略定义 scaffold。
   - 生成默认 profile 参数。
   - 回测/验证任务重复限制。
   - 生命周期自动推进接口。
7. `test/draft` 验证过：缺少正式 spec 时会正确停在 `策略定义`，不再误判为已完成。

## 当前主要缺口

### P0: 工作台从零建策略的完整闭环

需要确保一个新建策略可以在工作台内按 step 顺序完成：

1. 创建策略假设。
2. 在 `策略定义` step 点击生成基础定义。
3. 在 `参数档案` step 点击生成默认参数。
4. 在 `生成运行产物` step materialize。
5. 在 `train` step 发起调优或 train 回测。
6. 在 `validation` step 发起 validation gate。
7. 在 `test` step 发起 test 留出回测。
8. 在 `paper` step 创建模拟盘记录。

### P0: step 操作结果展示

每个 step 操作后，页面需要给出明确反馈：

- 创建了哪个 job。
- 是否命中 dedupe。
- 失败原因摘要。
- 下一步应该点哪个 step。

当前部分 mutation 结果只显示在 AI 推进计划区域，不够贴近 step。

### P0: 基础定义 scaffold 需要可解释

`生成基础定义` 当前是保守默认模板。下一步需要在工作台展示：

- 生成了哪些因子。
- 生成了哪些入场/出场规则。
- train / validation / test 区间。
- 风控参数。
- 明确提示“这是流程打通模板，不是可直接实盘策略”。

### P1: 参数档案可编辑

当前只能生成默认参数或新增空草稿。需要提供最小可用参数编辑能力：

- max_open_trades
- stoploss
- trailing_stop_positive
- trailing_stop_positive_offset
- minimal_roi
- 核心 factor 参数，如 MA period、RSI period、RSI overbought/oversold、volume ratio

编辑后写入 `strategy_profiles.overrides`。

### P1: profile 状态推进一致性

需要梳理 profile status 和证据的关系：

- 生成基础定义后，profile 是否应该变为 `generated`。
- materialize 成功后是否自动写 promotion event 或只写 artifact。
- train 成功后是否自动标记 `backtested`。
- validation gate 通过后是否仍要求人工点 `晋级验证`。

建议保守原则：

- 自动任务只写证据。
- 状态晋级需要明确按钮。
- `validated` 以后必须人工确认。

### P1: 页面信息架构

工作台建议最终结构：

```text
选择区
新增策略 / 新增档案
当前策略概要
流程步骤（主操作）
右侧：Thesis / 当前证据 / 最近事件
```

历史类信息仅保留跳转：

- 任务历史 -> `/jobs`
- 回测验证 -> `/backtests`
- 运行产物 -> `/runtime`
- 模拟记录 -> `/paper`

## 重点文件

后端：

- `web/backend/app/services/lifecycle_service.py`
- `web/backend/app/services/registry_service.py`
- `web/backend/app/services/jobs_service.py`
- `web/backend/app/routers/lifecycle.py`
- `web/backend/app/routers/registry.py`
- `web/backend/app/routers/jobs.py`

前端：

- `web/frontend/src/pages/lifecycle-page.tsx`
- `web/frontend/src/api/index.ts`
- `web/frontend/src/api/types.ts`
- `web/frontend/src/components/app-shell.tsx`

## 验收标准

以一个全新策略，例如 `flow_test_v1`，验证：

1. 可以在工作台创建策略。
2. 不填写 Thesis 也不会阻塞。
3. `策略定义` step 可生成基础定义，并刷新后变为 completed。
4. `参数档案` step 可生成默认参数，并刷新后有 overrides。
5. `生成运行产物` step 可创建 materialize job。
6. `train` step 可创建 train 任务，错误能在 step 内展示。
7. 切换策略不会沿用上一个策略的 profile。
8. 所有任务历史可在 `/jobs` 查到。
9. 前端构建通过。
10. 后端 compileall 通过。

## 建议验证命令

```bash
python3 -m compileall web/backend/app
cd web/frontend && npm run build
web/start_web.sh
```

## 注意事项

- 旧 Vue 前端已废弃，后续不需要兼容旧 Vue 文件。
- `strategies/` 是唯一策略源码挂载目录，不要新增 Docker 策略副本。
- 工作台生成的基础定义只是流程模板，不能作为实盘有效性结论。
- validation/test 不能用于反复调参。
- `paper_active/live_candidate/live_active` 涉及运行风险，必须保留人工确认。
