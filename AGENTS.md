# AI-OuYi PROJECT KNOWLEDGE BASE

**更新**: 2026-05-25 | **分支**: master

## 项目定位

面向 OKX 合约的 Freqtrade 量化研究仓库，当前处于"策略实验验证阶段"，非成熟实盘系统。

## 结构
```
AI-OuYi/
├── .opencode/              # OpenCode 配置与知识库
├── apps/prototypes/         # 原型级机器人（非生产）
├── data/sync/              # 外部数据同步
├── docs/operations/        # 运行文档
├── execution/               # 执行层（Docker 主环境）
│   ├── scripts/            # simctl 运维脚本
│   └── freqtrade/          # freqtrade 容器配置
├── research/               # 研究、实验、协调
├── strategies/              # 策略源码（直接挂载 Docker）
│   ├── spec/              # 策略 YAML 定义（3 条生成链）
│   ├── profiles/           # 参数档案（46 个 profile）
│   ├── generated/          # 自动生成代码
│   ├── services/          # CLI 服务层
│   └── cli.py             # 主 CLI 入口
├── web/                    # Web 管理系统（FastAPI + React）
├── AI_CONTEXT.md           # AI 接手上下文
└── requirements.txt
```

## WHERE TO LOOK
| 任务 | 路径 | 备注 |
|------|------|------|
| 当前运行配置 | `execution/freqtrade/user_data/config.json` | Docker 主配置 |
| 策略定义 | `strategies/spec/` | YAML 入口 |
| 参数档案 | `strategies/profiles/*/` | 46 个 profile |
| CLI 命令 | `strategies/cli.py` | 主 CLI |
| 知识库 | `.opencode/knowledge-base/` | 项目知识 |
| Web 管理系统 | `web/` | FastAPI + React 管理层 |

## CODE MAP
| 符号 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `cli.py` | CLI | `strategies/` | 主入口 |
| `grid_ls_v1` | strategy | `spec/` | SOL 网格 |
| `multi_ls_v2` | strategy | `spec/` | 多空切换 V2 |
| `multi_ls_v3` | strategy | `spec/` | 多空结构化 V3 |
| `generation_service` | service | `services/` | 代码生成 |
| `profile_service` | service | `services/` | 参数治理 |
| `main.tsx` | frontend | `web/frontend/src/` | React Web 入口 |
| `api/index.ts` | frontend | `web/frontend/src/` | Web 统一 API client |

## ANTI-PATTERNS (THIS PROJECT)
- ❌ 把 `execution/templates/` 当主运行目录
- ❌ 单独维护 Docker 策略副本（`strategies/` 即唯一源码）
- ❌ 用测试集调参
- ❌ 把实验策略放 `strategies/` 主目录 → `research/experiments/`
- ❌ 依赖 Freqtrade 内建下载 funding_rate 等合约因子
- ❌ 在 Web 前端恢复历史前端技术栈

## COMMANDS
```bash
# Docker
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s GridLsV1Strategy

# CLI
docker exec freqtrade python /freqtrade/user_data/strategies/cli.py run multi_ls_v2

# simctl
execution/scripts/simctl up
execution/scripts/simctl balance
execution/scripts/simctl status

# Web
web/start_web.sh
cd web/frontend && npm run build
```

## 边界
- 主执行层 = Freqtrade（Docker）
- 策略源码 = `strategies/`（bind mount 到容器）
- 数据层 = `execution/freqtrade/user_data/external_data/`
- Web 前端 = `React + Vite + TypeScript + Tailwind CSS + shadcn/ui + Radix UI + lucide-react + TanStack Query/Table`
- 当前运行默认：`GridLsV1Strategy`，但仓库维护 3 条生成链
