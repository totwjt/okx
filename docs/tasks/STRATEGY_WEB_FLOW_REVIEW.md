# 策略创建到执行全流程与 Web 覆盖情况

更新: 2026-05-22

## 1. 完整流程

AI-OuYi 当前的策略链路可以理解为三层：策略资产层、验证筛选层、运行执行层。

```text
策略想法
  -> 策略定义 spec
  -> 参数档案 profile
  -> 生成 Freqtrade 运行文件
  -> 回测 backtest
  -> 验证闸门 validation gate
  -> 参数档案晋级 promotion
  -> 生成 runtime artifact
  -> dry-run 模拟盘运行
  -> 风控与因子健康监控
  -> live_candidate / live_active
```

### 阶段说明

1. 策略创建
   - 输入是策略逻辑、指标、入场/出场规则、风控模型。
   - 历史文件入口是 `strategies/spec/*.yaml`，目标形态是 PostgreSQL `strategy_specs`。
   - 当前不建议把实验策略直接放到 `strategies/` 根目录。

2. 参数档案创建
   - 每个策略可以有多个 profile，用来表达不同参数组合。
   - 历史文件入口是 `strategies/profiles/<strategy>/*.yaml`，目标形态是 PostgreSQL `strategy_profiles`。
   - profile 状态从 `draft/generated/backtested/validated/paper_active/live_candidate/live_active/archived` 显式流转。

3. 生成运行文件
   - Freqtrade 运行仍需要 Python 策略文件和参数 JSON。
   - Web/CLI 通过 registry materialize 从数据库生成临时 runtime artifact。
   - 运行产物只进入 `execution/freqtrade/user_data/runtime_strategies/`，不作为长期源码。

4. 回测筛选
   - 对策略和当前 active profile 发起 backtest job。
   - 关键指标包括收益、最大回撤、交易数、胜率、利润因子。
   - 回测结果写入 job/result，可回查。

5. 验证闸门
   - validation gate 用固定阈值检查候选 profile。
   - 常见阈值包括最少交易数、最低收益、最低利润因子、最大回撤。
   - 未通过 gate 的 profile 不能一键晋级到 `validated`。

6. 晋级
   - 通过验证后，profile 可以晋级到 `validated`。
   - 晋级必须写入 `strategy_promotion_events`。
   - `paper_active/live_active` 会影响当前生效 profile，不能绕过 validation event。

7. 模拟盘执行
   - 对已选策略/profile 生成 runtime artifact。
   - Freqtrade dry-run 使用 runtime 策略目录启动。
   - Web 当前只读监控模拟盘，不提供强制开仓/平仓。

8. 风控与数据健康
   - 风控看板展示回撤、单日亏损、连续亏损、冷却锁定。
   - 因子页检查 funding/OHLCV 覆盖范围和缺口。
   - 这些是晋级和运行判断的辅助证据，不自动替代人工决策。

## 2. Web 覆盖情况

| 流程环节 | Web 是否覆盖 | 当前入口 | 说明 |
|---|---:|---|---|
| 查看策略注册表 | 是 | 策略管理 | 读取 PostgreSQL strategy registry |
| 查看 profile | 是 | 策略管理 | 展示状态、生效标记、覆盖参数、验证信息 |
| 新建策略 spec | 否 | 无 | 目前没有 Web 表单或导入按钮 |
| 新建/编辑 profile | 否 | 无 | 目前只读，没有参数编辑器 |
| 旧 YAML 导入数据库 | 否 | 无 | 文档规划有 import-files，但 Web 未接入 |
| 生成 runtime artifact | 是 | 运行系统 | 可选择策略并生成运行产物 |
| 查看 runtime artifact | 是 | 运行系统 | 展示文件、hash、类型、生成时间 |
| 发起回测 | 是 | 回测验证 | 支持 strategy、phase、timerange |
| 查看回测结果 | 是 | 回测验证 | 展示交易数、收益、回撤、胜率、利润因子 |
| 发起 validation gate | 是 | 回测验证 | 可配置基础阈值 |
| profile 晋级到 validated | 是 | 回测验证 | 未通过 gate 时按钮不可用，后端也会拦截 |
| 晋级到 paper/live | 部分 | API 有约束，Web 无入口 | 当前 Web 只做 validated 晋级 |
| 模拟盘监控 | 是 | 模拟盘 | 只读展示 dry-run、余额、持仓、交易 |
| 风控看板 | 是 | 风控看板 | 只读，不执行自动风控动作 |
| 因子数据健康 | 是 | 因子数据 | 检查 funding/OHLCV 覆盖和缺口 |
| 用户权限/审计 | 否 | 无 | TASK-013 已无限期延后 |

## 3. Web 人工操作流程

当前 Web 可以覆盖“查看已有策略 -> 生成运行产物 -> 回测 -> 验证 -> 晋级 validated -> 模拟盘观察”的中后段流程。

1. 打开 Web
   - 执行 `web/start_web.sh`
   - 浏览器访问 `http://127.0.0.1:8123/`

2. 策略管理
   - 进入“策略管理”。
   - 查看策略列表、当前状态、profile 数量。
   - 选择一个策略后，确认“当前参数档案”和 profile 状态。

3. 生成运行产物
   - 进入“运行系统”。
   - 选择策略。
   - 点击“生成”，确认后写入 runtime 策略目录。
   - 在“运行产物”表中确认策略代码和参数文件已生成，并记录 hash。

4. 发起回测
   - 进入“回测验证”。
   - 选择策略、阶段和时间范围。
   - 点击“发起”创建 backtest job。
   - 等任务完成后查看收益、回撤、交易数、胜率、利润因子。

5. 运行验证闸门
   - 仍在“回测验证”。
   - 设置验证时间范围、最少交易数、最低收益、利润因子、最大回撤。
   - 点击“验证”。
   - 通过后表格显示“通过”，未通过会显示失败检查。

6. 晋级
   - validation gate 通过后，点击“晋级已验证”。
   - 后端会写 promotion event。
   - 未通过 gate 的记录不能晋级。

7. 模拟盘观察
   - 进入“模拟盘”。
   - 确认模式是“模拟盘”，接口可访问。
   - 查看当前持仓、余额、累计盈亏和最近交易。

8. 风控和因子复核
   - 进入“风控看板”，查看最大回撤、单日亏损、连续亏损和冷却锁定。
   - 进入“因子数据”，确认 funding/OHLCV 覆盖范围和缺口状态。

## 4. 主要不足

1. Web 还不能从零创建策略 spec。
2. Web 还不能创建或编辑 profile 参数。
3. Web 还没有接入旧 YAML/profile 导入按钮。
4. Web 只支持晋级到 `validated`，还没有 `paper_active/live_candidate/live_active` 的人工操作入口。
5. Web 没有用户权限、审计和高危操作确认体系，因此不适合开放实盘高危操作。
6. Web 当前偏“研究管理与验证控制台”，不是完整交易平台。

