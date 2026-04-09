# AI 开发 SOP

## 目标

让后续 AI 线程在这个仓库里沿着同一条主线持续推进，而不是重新分叉。

## 0. 接手前先读

按顺序读取：

1. `AI_CONTEXT.md`
2. `.opencode/knowledge-base/project.md`
3. `.opencode/knowledge-base/ai-collaboration.md`
4. `.opencode/knowledge-base/execution-architecture.md`
5. `strategies/README.md`

## 1. 先判断任务类型

每次任务先判断属于哪一类：

- 文档 / AI 协作
- 策略逻辑
- 参数与回测
- 数据同步 / 数据标准化
- 成本模型
- 风控模型
- 执行架构

如果任务跨多类，先说明本次主任务和次任务。

## 2. 改动前必做检查

改动前至少检查：

1. 当前主线策略是否仍是 `MultiLsV2Strategy`
2. `strategies/` 是否仍是唯一策略源码目录
3. YAML 是否仍是参数主来源
4. 当前回测是否仍采用 train / validation / test
5. 成本模型和风险模型是否仍在 YAML 中显式维护

## 3. 修改规则

### 改 Python 代码结构

- 新增或重构 Python 代码时，目标是单文件尽量不超过 400 行
- 如果单文件持续膨胀，按功能 / 领域拆分到 `core`、`utils`、`services`、`models`、`config` 等模块
- 优先使用标准 Python package 结构，并补齐必要的 `__init__.py`
- 拆分时优先提取可复用能力，避免把流程控制、数据结构、配置读取混写在同一个大文件里
- 该约束的目标是提升代码复用性、降低 AI 阅读成本，并便于后续团队协作
- 如果受第三方框架入口或策略类约束，无法严格满足 400 行目标，需要在说明中明确原因，并继续按职责拆分周边模块

### 改策略

- 只改 `strategies/`
- 优先改 `spec/multi_ls_v2.yaml`
- 需要时再重新生成代码

### 改参数

- 先改 `spec/multi_ls_v2.yaml`
- 不要再引入第二套参数来源

### 改回测流程

- 保持 train / validation / test 三段式
- 不要把 test 集重新拿去做调参

### 改数据同步

- 优先把研究型因子与 `Freqtrade` 内建下载链路解耦
- 原始数据、标准化数据、策略读取逻辑分开维护
- 外部因子优先落盘到 `execution/freqtrade/user_data/external_data/`
- 涉及时间对齐时，先明确时区、频率和前向填充规则

### 改执行架构

- 先更新 `execution-architecture.md`
- 再开始代码层改动

## 4. 验证规则

如果改了 `strategies/cli.py`：

- 至少运行 `python3 -m py_compile strategies/cli.py`

如果改了策略规范：

- 至少确认 README 与 YAML 不冲突

如果改了执行架构相关内容：

- 至少确认 `AGENTS.md`、`AI_CONTEXT.md`、知识库文档三处一致

如果改了数据同步或外部因子读取：

- 至少运行相关脚本的 `py_compile`
- 至少确认策略在缺失外部数据时有降级路径，不会直接崩溃

## 5. 提交规则

- 每个线程尽量一个提交
- 提交信息应体现该线程目标

推荐格式：

- `chore: ...`
- `feat: ...`
- `docs: ...`

## 6. 禁止事项

- 不要恢复已淘汰的旧策略分支
- 不要再创建第二份 Docker 策略副本
- 不要绕过 YAML 另起一套参数体系
- 不要把原型执行脚本误写成当前生产主线

## 7. 当前推荐推进顺序

1. 策略表达能力增强
2. 更完整的回测结果归档
3. Freqtrade protections 与 YAML 风控边界联动
4. 运行监控与告警
5. 必要时再评估自定义执行层

## 8. 双线程协作

当前项目允许使用双线程协作，但职责必须固定：

- 线程一只做 profile 层持续优化与验证闭环
- 线程二只在收到线程一信号后处理 spec 层结构修改

注意：

- 这不是所有线程的默认要求
- 只有明确加载线程专用任务文件的两个线程才使用这套机制
- 普通功能开发线程不需要进入 signal 流程
- 双线程的 `progress/signal` 必须按 `strategy_slug` 分目录隔离；切策略时必须新建上下文，不能复用旧策略 current 内容

详细规则见：

- `docs/operations/dual-thread-sop.md`
- `docs/operations/thread-signal-spec.md`
- `research/coordination/thread1-profile-optimization.md`
- `research/coordination/thread2-spec-optimization.md`
