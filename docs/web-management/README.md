# AI-OuYi Web 管理系统文档入口

本目录记录 AI-OuYi 自己的 Web 管理系统。当前实现已落地在仓库内 `web/`。

核心目标：

```text
PostgreSQL strategy registry
  -> profile / promotion
  -> runtime materialize
  -> Freqtrade backtest / dry-run
  -> result / audit / risk gate
```

文档：

- [PRODUCT_PLAN.md](./PRODUCT_PLAN.md): 功能模块、优先级、MVP 范围
- [../tasks/AI_CODING_WORKFLOW.md](../tasks/AI_CODING_WORKFLOW.md): AI coding workflow 任务状态机

当前技术栈：

- 后端：FastAPI，固定服务端口 `127.0.0.1:8123`
- 前端：React + Vite + TypeScript + Tailwind CSS
- UI primitives：Radix UI
- UI 组件约定：shadcn/ui 本地源码组件模式，配置见 `web/frontend/components.json`
- 数据请求：TanStack Query
- 表格：TanStack Table
- 图标：lucide-react
- API 边界：前端只调用 `/api/*`，不直接读取策略源码或 runtime Python 正文

关键入口：

- `web/start_web.sh`: 构建前端并启动 Web 服务
- `web/backend/app/main.py`: FastAPI app 与静态前端托管
- `web/frontend/src/main.tsx`: React 入口与路由
- `web/frontend/src/api/index.ts`: 前端统一 API client
- `web/frontend/src/components/ui/`: shadcn 风格共享 UI 组件
- `web/frontend/src/pages/`: 页面级组件
