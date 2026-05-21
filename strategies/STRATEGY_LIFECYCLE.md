# 策略生命周期与生成物隔离方案

## 目标

`strategies/` 后续不再作为“策略产物仓库”，而作为“策略工厂代码目录”。

项目策略资产从文件型 YAML / profile / generated Python，迁移为 PostgreSQL 驱动的策略注册表。Freqtrade 运行仍需要 Python 策略文件，但这些文件只允许作为临时 materialized runtime artifact，不再作为长期源码资产。

## 当前问题确认

当前 `strategies/` 同时包含：

- 人工维护源：`cli.py`、`services/`、`templates/`、`spec/`
- 参数资产：`profiles/`
- 生成代码：`generated/*.py`
- 运行快照：`auto_*.py`、`auto_*.json`
- Python 缓存：`__pycache__/`、`*.pyc`

这会带来三个直接问题：

- AI 和人工检索容易把生成物当源码读取，浪费上下文。
- profile、active 指针、generated 文件、Docker 当前策略之间没有强一致性约束。
- 策略晋级历史散落在 YAML 文件里，缺少事件记录、回滚点和审计链。

## 新边界

### 1. 源码层

保留在 Git 中，允许 AI 和人工长期阅读：

- `strategies/cli.py`
- `strategies/services/`
- `strategies/templates/`
- `strategies/schema/` 或 `strategies/migrations/`
- `strategies/STRATEGY_LIFECYCLE.md`
- 少量面向人类的 README / AGENTS 文档

### 2. 数据层

策略资产进入 PostgreSQL：

- 策略定义
- 策略版本
- profile 参数
- validation gate 结果
- promotion 事件
- backtest / paper run 摘要
- runtime artifact 的 hash、路径和生成元数据

### 3. 运行层

Freqtrade 运行前从 PostgreSQL 临时生成：

- `auto_<strategy>.py`
- `auto_<strategy>.json`

运行产物只允许进入 runtime 目录，不进入 Git，不作为 AI 默认上下文。

推荐目录：

```text
execution/freqtrade/user_data/runtime_strategies/
execution/freqtrade/user_data/runtime_params/
```

当前执行约定：

- Docker 使用 `--strategy-path /freqtrade/user_data/runtime_strategies`
- Freqtrade 运行前必须先执行 `registry materialize <strategy_slug>`
- 策略 `.py` 与对应 `auto_<strategy>.json` 暂时同放在 `runtime_strategies/`，保证 Freqtrade 能发现参数文件
- `runtime_params/` 预留给后续更细粒度的参数快照和审计导出

## 全局参数

当前本地 PostgreSQL 使用环境变量：

```bash
DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/ouyi_db
```

约定：

- 数据库名：`ouyi_db`
- 连接配置唯一来源：`DATABASE_URL`
- Python async 客户端使用 `postgresql+asyncpg://`
- `psql` / admin 初始化时需要临时转换为 `postgresql://`
- 创建数据库时先连接 `postgres` maintenance database，再创建 `ouyi_db`
- 不在文档、日志和 Git 中写入真实密码
- 在宿主机运行 registry CLI 时使用 `localhost`；如果未来在 Docker 容器内运行 registry CLI，host 需要改成 `host.docker.internal`

后续可选参数：

```bash
STRATEGY_RUNTIME_DIR=execution/freqtrade/user_data/runtime_strategies
STRATEGY_PARAM_RUNTIME_DIR=execution/freqtrade/user_data/runtime_params
STRATEGY_REGISTRY_SCHEMA=public
```

## 生命周期状态

策略资产状态采用显式状态机：

```text
draft
  -> generated
  -> backtested
  -> validated
  -> paper_active
  -> live_candidate
  -> live_active
  -> archived
```

状态含义：

- `draft`: 尚未完成验证的策略定义或 profile。
- `generated`: 已可生成 Freqtrade 运行文件。
- `backtested`: 已完成至少一次 train 或自定义回测。
- `validated`: 已通过 validation gate。
- `paper_active`: 当前模拟盘候选运行配置。
- `live_candidate`: 准备实盘前的候选配置。
- `live_active`: 当前实盘配置，必须唯一。
- `archived`: 不再参与生成和运行，只保留历史记录。

晋级原则：

- 晋级必须写入 promotion event。
- `paper_active` 和 `live_active` 每个策略族最多只能有一个。
- `live_active` 必须来源于 `validated` 或 `live_candidate`。
- 不允许通过直接改文件跳过生命周期状态。

## PostgreSQL 初始表建议

第一阶段保持 schema 简洁，先承接现有 spec/profile 能力：

```sql
create table strategy_specs (
  id bigserial primary key,
  slug text not null unique,
  name text not null,
  description text,
  status text not null default 'draft',
  spec jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table strategy_profiles (
  id bigserial primary key,
  strategy_slug text not null references strategy_specs(slug),
  profile_name text not null,
  status text not null default 'draft',
  source text,
  overrides jsonb not null default '{}'::jsonb,
  validation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(strategy_slug, profile_name)
);

create table strategy_promotion_events (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  from_status text,
  to_status text not null,
  reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table strategy_validation_results (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  timerange text not null,
  passed boolean not null,
  metrics jsonb not null,
  gate jsonb not null,
  warnings jsonb not null default '[]'::jsonb,
  failed_checks jsonb not null default '[]'::jsonb,
  artifact_path text,
  created_at timestamptz not null default now()
);

create table strategy_runtime_artifacts (
  id bigserial primary key,
  strategy_slug text not null,
  profile_name text not null,
  artifact_type text not null,
  artifact_path text not null,
  artifact_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

## 迁移顺序

建议按低风险顺序执行：

1. 保留现有文件，新增 PostgreSQL 初始化和连接验证。
2. 新增导入命令：把 `spec/*.yaml` 和 `profiles/*/*.yaml` 导入数据库；归档后可用 `--source-dir` 直接从归档目录重导入。
3. 新增读取命令：CLI 优先从数据库读取策略定义和 profile。
4. 新增 materialize 命令：从数据库生成 Freqtrade 临时运行文件。
5. 更新 Docker 策略加载目录，改用 runtime 生成目录。
6. 归档旧 `spec/`、`profiles/`、`generated/`、`auto_*`。
7. 清理 `__pycache__`、`*.pyc` 和其他临时文件。

## 禁止事项

- 禁止手工编辑 `auto_*.py` 和 `auto_*.json`。
- 禁止把新实验策略直接放入 `strategies/` 根目录。
- 禁止让 generated/runtime 目录成为 AI 默认读取目标。
- 禁止用测试集调参。
- 禁止未经过 validation event 直接晋级到 paper/live 状态。

## 当前数据库状态

截至 2026-05-21，已完成：

- 从 `.env` 读取 `DATABASE_URL`
- 创建本地 PostgreSQL 数据库 `ouyi_db`
- 验证可连接到 `ouyi_db`

尚未完成：

- 建表迁移
- 旧 YAML/profile 导入 PostgreSQL
- CLI 改为数据库优先
- runtime materialize 目录隔离
- 旧策略资产归档和清理
