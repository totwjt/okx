# AI-OuYi Web 管理系统任务清单

## 总览

```text
TASK-001 review  Web 项目边界与脚手架决策
TASK-002 review  后端 Web API 骨架
TASK-003 review  Registry API
TASK-004 review  前端路由与主布局
TASK-005 review  策略管理页面
TASK-006 review  Runtime materialize 与 artifact 页面
TASK-007 review  Job 任务系统
TASK-008 review  回测任务与结果页面
TASK-009 review  Validation gate 与 profile 晋级
TASK-010 review  Dry-run 模拟盘监控
TASK-011 review    风控只读看板
TASK-012 review    因子数据健康页
TASK-013 todo    用户与权限收口
```

---

# TASK-001

状态: review
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
- `web/`
- `web/backend/system_check.py`

验证:
- `.venv/bin/python web/backend/system_check.py --strict`
- `.venv/bin/python strategies/cli.py registry list`
- `.venv/bin/python -m compileall -q web/backend`

备注:
- TASK-002 可复用 `web/backend/app/services/system_check.py` 挂载 `/api/system/check`。
- 本机全局 `python3 strategies/cli.py registry list` 缺少 `PyYAML`，项目虚拟环境可正常执行。

---

# TASK-002

状态: review
负责人: codex
依赖: TASK-001
优先级: P0
模块: backend

目标:
- 新建 AI-OuYi Web 后端 API 骨架。

验收:
- `GET /api/health` 返回 ok
- `GET /api/system/check` 返回 PostgreSQL、runtime 目录、Docker/Freqtrade 基础状态

交付:
- `web/backend/app/main.py`
- `web/backend/app/routers/health.py`
- `web/backend/app/routers/system.py`
- `web/backend/app/services/system_check.py`
- `requirements.txt`

验证:
- `.venv/bin/python -m compileall -q web/backend`
- `/Users/wangjiangtao/Documents/AI/AI-OuYi/.venv/bin/python web/backend/run_api.py`
- `curl -sS http://127.0.0.1:8123/api/health`
- `curl -sS http://127.0.0.1:8123/api/system/check`

备注:
- 2026-05-22 重新验收：Docker daemon 已启用，Docker check 为 OK。
- 2026-05-22 重新验收：Freqtrade compose 可访问，但容器 state 为 `restarting` 时不计为 ready。

---

# TASK-003

状态: review
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

交付:
- `web/backend/app/routers/registry.py`
- `web/backend/app/services/registry_service.py`
- `web/backend/run_api.py`

验证:
- `.venv/bin/python -m compileall -q web/backend`
- `.venv/bin/python web/backend/run_api.py`
- `curl -sS http://127.0.0.1:8123/api/strategies`
- `curl -sS http://127.0.0.1:8123/api/strategies/grid_ls_v1`
- `curl -sS http://127.0.0.1:8123/api/strategies/grid_ls_v1/profiles`
- `curl -sS 'http://127.0.0.1:8123/api/runtime/artifacts?limit=5'`
- `curl -sS -o /tmp/ai-ouyi-missing-strategy.json -w '%{http_code}' http://127.0.0.1:8123/api/strategies/not_exists`

备注:
- Web 后端固定使用 `127.0.0.1:8123`。
- Registry API 只读 PostgreSQL 表和 artifact 元数据，不读取 runtime/generated Python 正文。

---

# TASK-004

状态: review
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

交付:
- `web/frontend/package.json`
- `web/frontend/vite.config.ts`
- `web/frontend/src/main.ts`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/components/AppShell.vue`
- `web/frontend/src/views/RuntimeView.vue`
- `web/frontend/src/views/PlaceholderView.vue`
- `web/frontend/src/styles/main.css`
- `web/backend/app/main.py`
- `web/start_web.sh`

验证:
- `npm install`
- `npm run build`
- `.venv/bin/python web/backend/run_api.py`
- `web/start_web.sh`
- `curl -sS http://127.0.0.1:8123/api/health`
- `curl -sS http://127.0.0.1:8123/`
- Playwright desktop viewport `1280x720`: `scrollWidth=1280`, `overflowX=false`
- Playwright mobile viewport `390x844`: `scrollWidth=390`, `overflowX=false`

备注:
- 固定 Web 入口为 `http://127.0.0.1:8123/`，FastAPI 同端口托管前端构建产物和 `/api/*`。
- Vite `5173` 仅作为可选前端开发端口。

---

# TASK-005

状态: review
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

交付:
- `web/frontend/src/api/strategies.ts`
- `web/frontend/src/views/StrategiesView.vue`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/styles/main.css`

验证:
- `npm run build`
- `web/start_web.sh`
- `curl -sS http://127.0.0.1:8123/api/strategies`
- Browser `/strategies`: 渲染 4 条 strategy row、34 条当前选中 strategy profile row
- Playwright desktop viewport `1280x720`: `scrollWidth=1280`, `overflowX=false`
- Playwright mobile viewport `390x844`: `scrollWidth=390`, `overflowX=false`

备注:
- 页面只调用 `/api/strategies`、`/api/strategies/{slug}`、`/api/strategies/{slug}/profiles`。
- Spec 区只展示 key/type 摘要，并显式标注 `no generated code`。

---

# TASK-006

状态: review
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

交付:
- `web/backend/app/routers/registry.py`
- `web/backend/app/services/registry_service.py`
- `web/frontend/src/api/runtime.ts`
- `web/frontend/src/views/RuntimeView.vue`
- `web/frontend/src/styles/main.css`

验证:
- `npm run build`
- `.venv/bin/python -m compileall -q web/backend`
- `web/start_web.sh`
- `curl -sS -X POST http://127.0.0.1:8123/api/runtime/materialize -H 'Content-Type: application/json' -d '{"strategy_slug":"grid_ls_v1"}'`
- `curl -sS 'http://127.0.0.1:8123/api/runtime/artifacts?limit=4'`
- Browser `/runtime`: artifact table 渲染 10 条记录，显示 profile/type/file/hash/created
- Playwright desktop viewport `1280x720`: `overflowX=false`
- Playwright mobile viewport `390x844`: `scrollWidth=390`, `overflowX=false`

备注:
- Materialize 操作会弹出确认框。
- Artifact 页面只展示路径文件名、hash、时间、profile 和 artifact type，不展示 Python 正文。
- 本次 materialize 使 `strategy_runtime_artifacts` 从 8 增加到 10。

---

# TASK-007

状态: review
负责人: codex
依赖: TASK-006
优先级: P0
模块: jobs

目标:
- 建立数据库 job 任务系统。

验收:
- job 状态包含 pending/running/success/failed
- 失败能看到错误摘要

交付:
- `web/backend/app/services/jobs_service.py`
- `web/backend/app/routers/jobs.py`
- `web/backend/app/main.py`
- `web/frontend/src/api/jobs.ts`
- `web/frontend/src/views/JobsView.vue`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/components/AppShell.vue`
- `web/frontend/src/api/runtime.ts`
- `web/frontend/src/styles/main.css`

验证:
- `.venv/bin/python -m compileall -q web/backend`
- `npm run build`
- `web/start_web.sh`
- `curl -sS 'http://127.0.0.1:8123/api/jobs?limit=5'`
- `curl -sS -X POST http://127.0.0.1:8123/api/jobs -H 'Content-Type: application/json' -d '{"job_type":"materialize","payload":{"strategy_slug":"grid_ls_v1"}}'`
- `curl -sS -X POST http://127.0.0.1:8123/api/jobs -H 'Content-Type: application/json' -d '{"job_type":"materialize","payload":{"strategy_slug":"not_exists"}}'`
- Browser `/jobs`: 渲染 job rows，失败 job 显示 `error_summary`，desktop `overflowX=false`

备注:
- TASK-007 先提供数据库 job 表、API 和同步执行的 `materialize` job；TASK-008 再扩展异步 backtest worker。
- job 状态约束为 `pending/running/success/failed`。

---

# TASK-008

状态: review
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

交付:
- `web/backend/app/services/jobs_service.py`
- `web/backend/app/routers/jobs.py`
- `web/frontend/src/api/backtests.ts`
- `web/frontend/src/views/BacktestsView.vue`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/styles/main.css`

验证:
- `.venv/bin/python -m compileall -q web/backend`
- `npm run build`
- `web/start_web.sh`
- `curl -sS -X POST http://127.0.0.1:8123/api/jobs -H 'Content-Type: application/json' -d '{"job_type":"backtest","payload":{"strategy_slug":"grid_ls_v1","phase":"custom","timerange":"20251004-20251005","timeout_seconds":300}}'`
- `curl -sS http://127.0.0.1:8123/api/jobs/7`
- `curl -sS 'http://127.0.0.1:8123/api/backtests/results?limit=5'`
- Browser `/backtests`: 渲染 2 条 backtest row，显示 trades/profit/drawdown/winrate/profit factor，desktop `overflowX=false`

备注:
- `backtest` job 通过独立 worker 进程异步执行，先返回 `pending`，随后进入 `running`，完成后写入 `success/failed`。
- 当前后端通过 `docker exec freqtrade freqtrade backtesting` 执行，结果 zip 落入 `execution/freqtrade/user_data/backtest_results/web_jobs/`。

---

# TASK-009

状态: review
负责人: codex
依赖: TASK-008
优先级: P0
模块: validation

目标:
- 接入 validation gate 和 profile 晋级。

验收:
- 未通过 gate 不允许一键晋级
- 晋级写入 promotion event

交付:
- `web/backend/app/services/jobs_service.py`
- `web/backend/app/routers/jobs.py`
- `web/backend/app/job_worker.py`
- `web/frontend/src/api/validation.ts`
- `web/frontend/src/views/BacktestsView.vue`
- `web/frontend/src/styles/main.css`
- `strategies/services/db_service.py`

验证:
- `.venv/bin/python -m compileall -q web/backend strategies`
- `npm run build`
- `web/start_web.sh`
- `curl -sS -X POST http://127.0.0.1:8123/api/jobs -H 'Content-Type: application/json' -d '{"job_type":"validation","payload":{"strategy_slug":"grid_ls_v1","profile_name":"candidate_opt_20260415_v2","timerange":"20251010-20251011","min_trades":1,"min_profit":0,"min_profit_factor":1,"max_drawdown":0.3,"timeout_seconds":300}}'`
- `curl -sS -X POST http://127.0.0.1:8123/api/profiles/promote -H 'Content-Type: application/json' -d '{"strategy_slug":"grid_ls_v1","profile_name":"candidate_opt_20260415_v2","to_status":"validated","reason":"blocked test"}'` -> HTTP 400
- `curl -sS -X POST http://127.0.0.1:8123/api/jobs -H 'Content-Type: application/json' -d '{"job_type":"validation","payload":{"strategy_slug":"grid_ls_v1","profile_name":"candidate_opt_20260415_v2","timerange":"20251010-20251011","min_trades":1,"min_profit":0,"min_profit_factor":0,"max_drawdown":0.3,"timeout_seconds":300}}'`
- `curl -sS -X POST http://127.0.0.1:8123/api/profiles/promote -H 'Content-Type: application/json' -d '{"strategy_slug":"grid_ls_v1","profile_name":"candidate_opt_20260415_v2","to_status":"validated","reason":"passed validation gate test"}'`
- Browser `/backtests`: Validation Gate 渲染 PASS/FAIL，失败检查可见，desktop `overflowX=false`

备注:
- `validation` job 会写入 `strategy_validation_results`，并把 `last_result` 写回对应 profile 的 `validation` JSON。
- `/api/profiles/promote` 对 `validated/paper_active/live_candidate/live_active` 做最近一次 validation passed 检查。
- 晋级到 `validated` 保留原 active profile；只有 `paper_active/live_active` 会切换 active profile。

---

# TASK-010

状态: review
负责人: codex
依赖: TASK-006
优先级: P1
模块: paper

目标:
- 完成 dry-run 模拟盘监控 MVP。

验收:
- 页面明确显示 dry-run
- API 不可达时有错误状态

交付:
- `web/backend/app/services/paper_service.py`
- `web/backend/app/routers/paper.py`
- `web/backend/app/main.py`
- `web/frontend/src/api/paper.ts`
- `web/frontend/src/views/PaperView.vue`
- `web/frontend/src/router/index.ts`
- `web/frontend/src/styles/main.css`

验证:
- `.venv/bin/python -m compileall -q web/backend strategies`
- `npm run build`
- `web/start_web.sh`
- `curl -sS http://127.0.0.1:8123/api/paper/summary`
- Browser `/paper`: 显示 dry-run、REST / WS off、API reachable、open positions、recent trades，desktop `overflowX=false`

备注:
- 当前页面只读展示 Freqtrade dry-run REST baseline，不提供 force-enter/force-exit 等高危操作。
- Freqtrade API 不可达时，`/api/paper/summary` 会保留错误摘要，前端展示错误状态。
- 当前 runtime artifact 与运行策略可做对齐检查

---

# TASK-011

状态: review
负责人: codex
依赖: TASK-010
优先级: P1
模块: risk

目标:
- 完成风控只读看板。

验收:
- 展示 max drawdown、daily loss、consecutive losses、cooldown
- 不执行自动风控动作

交付:
- 新增 `/api/risk/summary` 只读接口，聚合 runtime artifact、profile risk_model、Freqtrade profit/trades/locks。
- 新增 `/risk` 风控看板，展示 Risk Overview、Risk Checks、Rules、Cooldown Locks、Recent Closed Trades。
- 风控状态只读展示，不提供自动 stop、force exit、lock/unlock 等动作。

验证:
- `.venv/bin/python -m compileall -q web/backend strategies`
- `npm run build`
- `curl --noproxy '*' -sS http://127.0.0.1:8123/api/risk/summary`
- Playwright `/risk`: 显示 max drawdown、daily loss、consecutive losses、cooldown；desktop/mobile `overflowX=false`

备注:
- 当前数据源为 Freqtrade dry-run REST API；cooldown 展示 `/locks` 现状和 profile 配置，不主动创建或清理锁。
- 当前运行策略读取 `execution/freqtrade/user_data/runtime_strategies/auto_*.json` 的最新 artifact。

---

# TASK-012

状态: review
负责人: codex
依赖: TASK-011
优先级: P2
模块: factors

目标:
- 完成因子数据健康页。

验收:
- 展示 funding/OHLCV 覆盖时间和缺口

交付:
- 新增 `/api/factors/health` 只读接口，通过 Freqtrade 容器扫描 `.feather` 与外部 funding CSV。
- 新增 `/factors` 因子数据健康页，展示 summary、Funding Coverage、OHLCV Coverage、Gap Samples。
- 缺口扫描按数据类型使用预期间隔：OHLCV 使用文件 timeframe，funding_rate 使用 8h。

验证:
- `.venv/bin/python -m compileall -q web/backend strategies`
- `npm run build`
- `curl --noproxy '*' -sS http://127.0.0.1:8123/api/factors/health`
- Playwright `/factors`: 显示 Funding Coverage、OHLCV Coverage、Gap Samples；desktop/mobile `overflowX=false`

备注:
- 当前扫描结果：20 个数据集，OHLCV 16 个，funding 4 个，内部时间缺口 0 个。
- 宿主 web 环境没有 pandas/pyarrow，接口通过只读 `docker exec freqtrade python` 使用容器内依赖扫描数据。

---

# TASK-013

状态: close, 无限期延后
负责人: codex
依赖: TASK-010
优先级: P3
模块: user

目标:
- 将高危操作接入用户权限和审计。

验收:
- 未授权用户不能执行高危操作
- 审计记录 user/action/target/time/result
