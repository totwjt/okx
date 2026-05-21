# AI-OuYi Web UI 与技术栈

## 参考方式

参考项目：

```text
/Users/wangjiangtao/Documents/AI/AI-trading-web/
```

只参考：

- Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia + Vue Router + Ant Design Vue
- 交易终端式高密度 UI
- 左侧导航 + 顶部导航 + main 内容区布局
- 语义化颜色、数字字体、深色模式

不在参考项目中创建 AI-OuYi 文件，不复用它的业务模块。

## 推荐技术栈

前端：

- Vue 3 Composition API
- Vite
- TypeScript
- Tailwind CSS
- Pinia
- Vue Router
- Ant Design Vue
- Iconify 或同等图标库
- lightweight-charts / Chart.js

后端：

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 或 psycopg2/asyncpg
- 数据库 job 表 + worker
- 调用现有 AI-OuYi CLI：
  - `strategies/cli.py registry list`
  - `strategies/cli.py registry materialize`
  - `execution/scripts/simctl ...`

## UI 风格

目标：

```text
专业交易终端
高密度数据展示
低视觉噪音
明确状态和风险
```

优先级：

```text
信息密度 > 响应速度 > 可读性 > 美观
```

## 页面建议

- `/strategies`: 策略管理
- `/backtests`: 回测与 validation
- `/runtime`: 运行产物与系统检查
- `/paper`: dry-run 模拟盘监控
- `/risk`: 风控系统
- `/factors`: 因子管理
- `/settings`: 系统配置

## 视觉规范

- 使用语义化颜色：`primary / up / down / warning / border / bgMain / card / textMain / textSub / textMute`
- 数字使用 `font-numeric`
- 表格使用高密度样式
- 卡片圆角不超过 8px
- 避免营销式大留白
- 不使用渐变装饰、装饰性光球、大面积单色主题
- 深色模式必须可读
- 移动窄屏不能文字重叠

## 状态颜色建议

- `draft`: 灰色
- `candidate`: 蓝色
- `validated`: 绿色
- `paper_active`: 主色高亮
- `live_candidate`: 橙色警示
- `live_active`: 红色高风险
- `archived`: 灰色弱化

## 建议目录

如果作为 AI-OuYi 子项目落地：

```text
web/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── views/
│       ├── stores/
│       └── types/
└── backend/
    ├── routers/
    ├── services/
    ├── models.py
    ├── schemas.py
    ├── jobs.py
    └── settings.py
```

## 实现原则

- 先读 PostgreSQL，不读旧 YAML/profile 文件。
- runtime artifact 只展示路径和 hash，不展示生成代码正文。
- Backtest、materialize、import 都走 job。
- 页面先做只读和执行验证，再做编辑能力。
- 高危操作必须二次确认并写 audit log。

