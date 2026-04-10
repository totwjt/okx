# AI-OuYi

## 项目定位

这是一个以 `Freqtrade + OKX` 为核心的研究型量化仓库，当前更接近“策略实验平台”，而不是可直接实盘托管的成熟交易系统。

## 当前事实来源

- 运行中的 Docker 数据目录: `execution/freqtrade/user_data/`
- 唯一策略源码目录: `strategies/`
- 研究实验脚本目录: `research/experiments/`
- 自定义实时机器人原型: `apps/prototypes/freqtrade_bot/realtime_bot.py`
- OpenCode 知识库: `.opencode/knowledge-base/`

优先相信以下路径中的内容是否与彼此一致，而不是只相信单个说明文件：

- `execution/freqtrade/user_data/config.json`
- `strategies/`
- `AI_CONTEXT.md`
- `.opencode/knowledge-base/project-structure-plan.md`

## 运行环境

### Docker（主环境）

`freqtrade` 容器是当前主要运行入口。默认挂载关系见：

- `execution/freqtrade/docker-compose.yml`

当前运行策略以以下事实为准：

- `execution/freqtrade/docker-compose.yml` 当前默认启动 `GridLsV1Strategy`
- `strategies/spec/` 当前存在 `grid_ls_v1`、`multi_ls_v2`、`multi_ls_v3` 三条生成链
- 具体执行时，如命令显式传入 `-s <StrategyClass>`，以显式指定为准

常用命令：

```bash
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker logs -f freqtrade
```

### 本地 Python（辅助环境）

仅适合阅读脚本、做研究型回测或生成策略，不应默认假设本地环境和 Docker 环境完全一致。

### 策略目录挂载关系

Docker 直接挂载：

- 本地 `strategies/`
- 到容器 `/freqtrade/user_data/strategies/`

这意味着修改本地 `strategies/` 后，无需再手动复制到 Docker。

## 目录说明

```text
AI-OuYi/
├── .opencode/                  # OpenCode 项目配置与知识库
├── apps/                       # 原型应用与非主线程序
├── data/                       # 外部数据同步与标准化
├── docs/                       # 通用文档
├── execution/                  # 执行层（Docker、运行态配置、模板）
├── research/                   # 研究实验与报告
├── strategies/                 # 本地策略源码、生成器、规范
├── AI_CONTEXT.md               # AI 快速接手上下文
└── requirements.txt            # Python 依赖
```

## AI 协作规则

- 不要默认模板目录是当前真实运行目录，当前主目录是 `execution/freqtrade/user_data/`。
- 不要再维护第二份 Docker 策略副本，`strategies/` 就是唯一策略源码目录。
- 当前主线唯一允许的策略接入链是：`spec -> profile -> generated -> auto_json -> docker运行`。
- `strategies/` 主目录不再接受独立手写实验策略；这类文件应放到 `research/experiments/` 或 `research/archive/`。
- `generated/`、`auto_*.py`、`auto_*.json` 都是生成产物，不应再作为手工维护入口。
- 不要仅凭文档断言策略有效，优先核对最近的回测产物与配置。
- 如果要修改策略逻辑，先说明会影响 `Freqtrade`、自定义回测脚本、Docker 副本中的哪一层。
- 如果只做文档或 AI 说明优化，不要顺手改交易逻辑。

## 当前状态

- 仓库当前已落地的主线生成链至少包含：`grid_ls_v1`、`multi_ls_v2`、`multi_ls_v3`。
- `MultiLS`、`LongShortSwitch`、`TrendFollowing` 等更早期命名仍应视为历史变体，不再作为当前主线事实来源。
- `Freqtrade` 是当前主执行层，`apps/prototypes/freqtrade_bot/realtime_bot.py` 仅保留为原型参考。

## 建议的阅读顺序

1. `AI_CONTEXT.md`
2. `.opencode/knowledge-base/project.md`
3. `.opencode/knowledge-base/ai-collaboration.md`
4. `execution/freqtrade/docker-compose.yml`
5. `execution/freqtrade/user_data/config.json`
6. `.opencode/knowledge-base/execution-architecture.md`
7. `.opencode/knowledge-base/ai-development-sop.md`
8. `.opencode/knowledge-base/project-structure-plan.md`
9. `strategies/README.md`
