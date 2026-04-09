# 线程信号协议

## 目标

让线程一和线程二通过文件化信号交接，而不是靠口头上下文。

该协议只对以下两个专用线程生效：

- [`thread1-profile-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread1-profile-optimization.md)
- [`thread2-spec-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread2-spec-optimization.md)

其他普通线程不需要读取、发送或维护这些信号文件。

## 策略隔离要求

所有 signal/progress 必须按策略命名空间隔离。

策略 slug 示例：`grid_ls_v1`、`multi_ls_v3`。

信号目录：

- `research/coordination/signals/<strategy_slug>/`

进度目录：

- `research/coordination/progress/<strategy_slug>/`

线程只允许读取当前 `strategy_slug` 下的文件。

初始化新策略上下文可使用：

`execution/scripts/simctl strategy-context-init <strategy_slug> <strategy_name> [context_id]`

## 信号文件命名

格式：

`YYYYMMDD_HHMMSS_<strategy_slug>_<signal_type>_<slug>.json`

示例：

- `20260409_103000_grid_ls_v1_T1_TO_T2_low_signal_density.json`
- `20260409_113500_grid_ls_v1_T2_TO_T1_spec_updated_for_signal_density.json`

## 信号类型

### `T1_TO_T2`

线程一发给线程二，表示：

- 当前 candidate 优化任务已结束
- 线程一判断问题属于结构层
- 需要线程二修改 spec

### `T2_TO_T1`

线程二发给线程一，表示：

- 当前 spec 修改已完成或终止
- 线程一可以重新进入验证流程

## 必填字段

### 通用字段

- `signal_type`
- `created_at`
- `from_thread`
- `to_thread`
- `strategy_name`
- `strategy_slug`
- `context_id`
- `active_profile`
- `summary`
- `status`

### `T1_TO_T2` 额外字段

- `candidate_profile`
- `problem_class`
- `evidence`
- `attempted_profile_changes`
- `why_profile_layer_failed`
- `requested_spec_changes`
- `expected_outcome`

### `T2_TO_T1` 额外字段

- `source_signal`
- `spec_changes`
- `affected_files`
- `logic_rationale`
- `expected_tradeoff`
- `next_actions_for_thread_1`

## `context_id` 规则

- 同一策略的一轮协作必须共享同一个 `context_id`
- 切换策略必须创建新的 `context_id`
- 线程读取 signal 时，如果 `strategy_slug` 或 `context_id` 不匹配当前任务，必须忽略

## 状态值

`T1_TO_T2` 使用：

- `OPEN`
- `CANCELLED`

`T2_TO_T1` 使用：

- `DONE`
- `ABORTED`

## 进度记录要求

除了信号 JSON，这两个专用线程各自都要同步写一份进度记录到：

- `research/coordination/progress/<strategy_slug>/`

固定命名：

- `thread1_current.md`
- `thread2_current.md`

记录内容至少包含：

- 当前目标
- 当前任务
- 当前对象
- 最近一次动作
- 当前结论
- 下一个动作

## 线程一发信号的标准

只有满足以下条件，线程一才允许发 `T1_TO_T2`：

- 当前 candidate 已完成本轮参数修改
- 至少有明确验证结果或 paper run 观察结果
- 能清楚说明为何问题不是 profile 层能解决
- 能具体指出希望线程二改哪一类结构

## 线程二回传信号的标准

线程二只有在以下两种情况下允许发 `T2_TO_T1`：

- 已完成 spec 修改，并说明影响范围
- 认为这次 spec 修改不应继续，给出终止理由

## 当前项目推荐的问题分类

线程一给线程二的 `problem_class` 建议限定为：

- `ENTRY_TOO_SPARSE`
- `EXIT_LOGIC_TOO_COARSE`
- `FACTOR_SET_INSUFFICIENT`
- `TREND_FILTER_TOO_STRICT`
- `SPEC_RISK_BOUNDARY_MISMATCH`

## 当前项目推荐的信号原则

- 一个信号只表达一个主问题
- 一个信号只对应一个 `strategy_slug`
- 线程一发信号前必须先完成当前任务收尾
- 线程二只从信号开始工作，不自行扩展问题范围
- 线程二回传后，线程一必须重新开始验证闭环
