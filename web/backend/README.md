# AI-OuYi Web Backend

后端采用 Python + FastAPI 方向，服务边界是读取 PostgreSQL strategy registry、触发既有 CLI/job，并检查 Freqtrade runtime 环境。

TASK-001 已落地的内容：

- `app/services/system_check.py`: 可复用系统检查服务
- `system_check.py`: 命令行检查入口

TASK-002 API 入口：

```bash
python web/backend/run_api.py
```

接口：

- `GET /api/health`
- `GET /api/system/check`

端口固定为 `127.0.0.1:8123`，避免与其他本地 Web 项目冲突。

后续 TASK-003 将补齐 strategy registry 只读 API。
