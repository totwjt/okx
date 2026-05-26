# AI-OuYi Web

AI-OuYi Web 管理系统落地在仓库内 `web/`，作为现有 Freqtrade 与 PostgreSQL strategy registry 的管理层。

当前边界：

- 后端目录：`web/backend/`
- 前端目录：`web/frontend/`
- 后端技术栈：FastAPI
- 前端技术栈：React + Vite + TypeScript + Tailwind CSS + shadcn/ui + Radix UI + lucide-react + TanStack Query/Table
- 数据事实来源：PostgreSQL strategy registry
- 运行产物目录：`execution/freqtrade/user_data/runtime_strategies/`
- 不读取或展示 runtime/generated 策略 Python 正文

主要前端入口：

- `web/frontend/src/main.tsx`: React 路由与 QueryClient
- `web/frontend/src/api/index.ts`: 统一 API client
- `web/frontend/src/pages/`: 页面级组件
- `web/frontend/src/components/`: Shell 与共享 UI
- `web/frontend/components.json`: shadcn/ui 项目约定

后端固定同端口托管 API 和前端构建产物：

- API：`/api/*`
- 前端：`web/frontend/dist`

环境检查：

```bash
python3 web/backend/system_check.py
python3 web/backend/system_check.py --strict
```

一键启动：

```bash
web/start_web.sh
```

脚本会先释放固定端口 `8123`，再构建前端并启动 Web 服务。
