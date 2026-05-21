# AI-OuYi Web

AI-OuYi Web 管理系统落地在仓库内 `web/`，作为现有 Freqtrade 与 PostgreSQL strategy registry 的管理层。

第一阶段边界：

- 后端目录：`web/backend/`
- 前端目录：`web/frontend/`
- 数据事实来源：PostgreSQL strategy registry
- 运行产物目录：`execution/freqtrade/user_data/runtime_strategies/`
- 不读取或展示 runtime/generated 策略 Python 正文

当前 TASK-001 只提供项目边界和环境检查脚手架。完整 FastAPI API 骨架由 TASK-002 承接。

环境检查：

```bash
python3 web/backend/system_check.py
python3 web/backend/system_check.py --strict
```

