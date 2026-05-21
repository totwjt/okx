# AI-OuYi Web 项目边界

## 落地目录

Web 管理系统作为 AI-OuYi 仓库内子项目落地：

```text
web/
├── backend/
│   ├── app/
│   │   └── services/
│   └── system_check.py
└── frontend/
```

## 技术栈决策

后端：

- Python
- FastAPI
- PostgreSQL
- psycopg2/SQLAlchemy 方向
- 通过现有 `strategies/cli.py registry ...` 和服务层复用策略注册表能力

前端：

- Vue 3 Composition API
- Vite
- TypeScript
- Tailwind CSS
- Pinia
- Vue Router
- Ant Design Vue
- Iconify 或同等图标库

## 数据与运行边界

- PostgreSQL `ouyi_db` 是策略管理事实来源。
- `DATABASE_URL` 是唯一数据库连接配置来源。
- runtime 策略产物目录固定为 `execution/freqtrade/user_data/runtime_strategies/`，可通过 `STRATEGY_RUNTIME_DIR` 覆盖。
- Web 页面只展示 runtime artifact 的路径、hash、类型、profile、生成时间等元数据。
- Web 页面不读取、不展示 `strategies/generated/` 或 runtime Python 正文。
- Freqtrade 执行仍由 `execution/freqtrade/` 和 `execution/scripts/simctl` 承接。

## 环境检查接口

TASK-001 提供命令行检查入口，TASK-002 可直接复用同一服务挂载到 `/api/system/check`。

```bash
python3 web/backend/system_check.py
python3 web/backend/system_check.py --strict
```

检查内容：

- PostgreSQL 是否可连接
- 目标数据库名是否为 `ouyi_db`
- registry 关键表是否存在
- registry 关键表计数是否可读取
- runtime strategy dir 是否存在、是否目录、是否可写

