# AI-OuYi Web 管理系统任务清单

## 总览

```text
TASK-001 ready   Web 项目边界与脚手架决策
TASK-002 todo    后端 Web API 骨架
TASK-003 todo    Registry API
TASK-004 todo    前端路由与主布局
TASK-005 todo    策略管理页面
TASK-006 todo    Runtime materialize 与 artifact 页面
TASK-007 todo    Job 任务系统
TASK-008 todo    回测任务与结果页面
TASK-009 todo    Validation gate 与 profile 晋级
TASK-010 todo    Dry-run 模拟盘监控
TASK-011 todo    风控只读看板
TASK-012 todo    因子数据健康页
TASK-013 todo    用户与权限收口
```

---

# TASK-001

状态: ready
负责人: codex
依赖: none
优先级: P0
模块: foundation

目标:
- 确定 AI-OuYi Web 管理系统的落地目录、技术栈和环境检查接口。

范围:
- 技术栈和 UI 设计规则
- 确定 AI-OuYi 内部 Web 目录
- 验证 `ouyi_db` 和 strategy registry 可连接
- 验证 runtime 目录存在

验收:
- 有明确 Web 目录方案
- PostgreSQL 连接状态可验证
- registry 表计数可验证
- runtime strategy dir 可验证

交付:
- `docs/web-management/`
- `docs/tasks/`
- 后续脚手架目录

---

# TASK-002

状态: todo
负责人: codex
依赖: TASK-001
优先级: P0
模块: backend

目标:
- 新建 AI-OuYi Web 后端 API 骨架。

验收:
- `GET /api/health` 返回 ok
- `GET /api/system/check` 返回 PostgreSQL、runtime 目录、Docker/Freqtrade 基础状态

---

# TASK-003

状态: todo
负责人: codex
依赖: TASK-002
优先级: P0
模块: registry

目标:
- 提供策略注册表只读 API。

验收:
- `GET /api/strategies`
- `GET /api/strategies/{slug}`
- `GET /api/strategies/{slug}/profiles`
- `GET /api/runtime/artifacts`

---

# TASK-004

状态: todo
负责人: codex
依赖: TASK-003
优先级: P0
模块: frontend

目标:
- 新建前端路由与主布局。

验收:
- 左侧导航 + 顶部导航 + main 内容区
- 深色模式
- 移动窄屏不重叠

---

# TASK-005

状态: todo
负责人: codex
依赖: TASK-004
优先级: P0
模块: strategy

目标:
- 完成策略管理页面 MVP。

验收:
- 数据来自 PostgreSQL registry
- 状态标签清晰
- 不读取 generated Python 正文

---

# TASK-006

状态: todo
负责人: codex
依赖: TASK-005
优先级: P0
模块: runtime

目标:
- 完成 runtime materialize 和 artifact 页面。

验收:
- materialize 后 artifact 列表刷新
- 只展示路径/hash/时间/profile
- 操作有确认

---

# TASK-007

状态: todo
负责人: codex
依赖: TASK-006
优先级: P0
模块: jobs

目标:
- 建立数据库 job 任务系统。

验收:
- job 状态包含 pending/running/success/failed
- 失败能看到错误摘要

---

# TASK-008

状态: todo
负责人: codex
依赖: TASK-007
优先级: P0
模块: backtest

目标:
- 完成回测任务发起和结果页面。

验收:
- 回测异步执行
- 结果可回查
- 指标包含收益、回撤、交易数、胜率、profit factor

---

# TASK-009

状态: todo
负责人: codex
依赖: TASK-008
优先级: P0
模块: validation

目标:
- 接入 validation gate 和 profile 晋级。

验收:
- 未通过 gate 不允许一键晋级
- 晋级写入 promotion event

---

# TASK-010

状态: todo
负责人: codex
依赖: TASK-006
优先级: P1
模块: paper

目标:
- 完成 dry-run 模拟盘监控 MVP。

验收:
- 页面明确显示 dry-run
- API 不可达时有错误状态
- 当前 runtime artifact 与运行策略可做对齐检查

---

# TASK-011

状态: todo
负责人: codex
依赖: TASK-010
优先级: P1
模块: risk

目标:
- 完成风控只读看板。

验收:
- 展示 max drawdown、daily loss、consecutive losses、cooldown
- 不执行自动风控动作

---

# TASK-012

状态: todo
负责人: codex
依赖: TASK-011
优先级: P2
模块: factors

目标:
- 完成因子数据健康页。

验收:
- 展示 funding/OHLCV 覆盖时间和缺口

---

# TASK-013

状态: todo
负责人: codex
依赖: TASK-010
优先级: P3
模块: user

目标:
- 将高危操作接入用户权限和审计。

验收:
- 未授权用户不能执行高危操作
- 审计记录 user/action/target/time/result

