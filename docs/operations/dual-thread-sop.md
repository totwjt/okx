# 双线程策略研发 SOP

## 目标

把协作拆成两个固定职责线程：

- 线程一：`Profile Optimization Thread`
- 线程二：`Spec Optimization Thread`

线程一负责参数层闭环，线程二只处理结构层问题。

## 生效范围

仅对以下两个专用线程生效：

- [`thread1-profile-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread1-profile-optimization.md)
- [`thread2-spec-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread2-spec-optimization.md)

其他线程不进入 signal 协议。

## 核心约束

- 主线链路固定：`spec -> profile -> generated -> auto_json -> backtest -> validation -> test -> paper run -> review`
- 双线程上下文必须按策略隔离，禁止跨策略复用 `current/progress/signal`
- 切换策略时必须创建新的策略命名空间上下文，不允许沿用旧策略内容

## 策略命名空间

以策略 slug 为隔离键（例如 `grid_ls_v1`、`multi_ls_v3`）：

- 进度文件：`research/coordination/progress/<strategy_slug>/thread1_current.md`
- 进度文件：`research/coordination/progress/<strategy_slug>/thread2_current.md`
- 信号目录：`research/coordination/signals/<strategy_slug>/`

## 策略切换重置 SOP

每次从 A 策略切到 B 策略，必须按顺序执行：

1. 归档 A 策略当前进度到 `research/coordination/progress/archive/`
2. 创建 B 策略目录：`progress/<strategy_slug>/` 与 `signals/<strategy_slug>/`
3. 初始化 B 策略的 `thread1_current.md`、`thread2_current.md`（空白或 INIT 状态）
4. 新信号文件仅写入 `signals/<strategy_slug>/`
5. 线程启动时仅允许读取当前 `<strategy_slug>` 下的 `progress/signal`

推荐直接使用命令完成上述动作：

`execution/scripts/simctl strategy-context-init <strategy_slug> <strategy_name> [context_id]`

## 线程一 SOP

角色：

- 诊断 baseline/validation/test/paper run
- 从证据里自主选当前轮唯一目标
- 基于 `paper_baseline` 建 candidate 并验证
- 必要时发 `T1_TO_T2` 结构问题信号

允许改动：

- `strategies/profiles/<strategy_slug>/*.yaml`
- 可读取 `strategies/spec/<strategy_slug>.yaml`
- 可触发生成产物，但不手改生成产物

禁止：

- 不手改 `generated/auto_*.py` 与 `auto_*.json`
- 不直接改 spec（除非线程二任务）
- 不跳过 validation/test 闭环

## 线程二 SOP

角色：

- 仅按 `T1_TO_T2` 信号处理结构问题
- 修改 `strategies/spec/<strategy_slug>.yaml`
- 发 `T2_TO_T1` 回传后停止

禁止：

- 不维护 candidate profile
- 不做最终有效性裁决
- 不越界做线程一的闭环验证

## 线程交接原则

- 线程一负责“证明有效性”
- 线程二负责“修改结构定义”
- 线程二完成即停，线程一收到回传后重新跑：
- `generate`
- `profile validate`
- `validate`
- 必要时 `paper run`

## 标准结论词汇

线程一：

- `KEEP_TESTING`
- `REJECT_PROFILE`
- `PROMOTE_TO_VALIDATED`
- `PROMOTE_TO_PAPER_ACTIVE`
- `ESCALATE_TO_THREAD_2`

线程二：

- `SPEC_UPDATED_READY_FOR_THREAD_1`
- `SPEC_CHANGE_REQUIRES_NEW_BASELINE`
- `SPEC_CHANGE_ABORTED`
