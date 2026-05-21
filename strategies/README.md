# 策略工厂

`strategies/` 当前定位为策略工厂代码目录，不再作为长期策略产物仓库。

新的主线是：

```text
PostgreSQL strategy registry
  -> registry materialize
  -> execution/freqtrade/user_data/runtime_strategies/
  -> Freqtrade Docker
```

详细生命周期、状态机和隔离规则见：

- [STRATEGY_LIFECYCLE.md](/Users/wangjiangtao/Documents/AI/AI-OuYi/strategies/STRATEGY_LIFECYCLE.md)

## 当前目录职责

```text
strategies/
├── cli.py                 # 策略管理 CLI
├── services/              # 生成、执行、profile、registry 服务
├── templates/             # 策略模板
├── spec/                  # 过渡期空目录；旧 YAML 已归档
├── profiles/              # 过渡期空目录；旧 profile 已归档
├── generated/             # 过渡期空目录；生成物禁止长期维护
├── AGENTS.md
└── STRATEGY_LIFECYCLE.md
```

旧策略资产已归档到：

- [research/archive/strategy_assets_20260521](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/archive/strategy_assets_20260521/README.md)

## 数据库

本地策略注册表使用 PostgreSQL：

```bash
DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:5432/ouyi_db
```

初始化：

```bash
.venv/bin/python strategies/cli.py registry init-db
```

查看：

```bash
.venv/bin/python strategies/cli.py registry list
```

## 从数据库生成运行产物

运行 Freqtrade 前，先 materialize 当前策略：

```bash
.venv/bin/python strategies/cli.py registry materialize grid_ls_v1
```

产物位置：

```text
execution/freqtrade/user_data/runtime_strategies/auto_grid_ls_v1.py
execution/freqtrade/user_data/runtime_strategies/auto_grid_ls_v1.json
```

这些文件是临时运行产物，已被 Git 忽略，不应作为源码阅读或手工编辑。

## 旧文件导入

如果需要从归档的 YAML/profile 重新导入，可以直接指定归档目录：

```bash
.venv/bin/python strategies/cli.py registry import-files --source-dir research/archive/strategy_assets_20260521
```

当前数据库已经完成一次旧资产导入。

## 禁止事项

- 禁止新策略直接放到 `strategies/` 根目录。
- 禁止手工编辑 `auto_*.py`、`auto_*.json`。
- 禁止把 generated/runtime 文件作为长期策略资产。
- 禁止跳过 validation/promotion 事件直接声明 paper/live active。
