# AI-OuYi 项目知识库

## 项目概述

这是一个面向 OKX 的量化研究仓库，核心由三部分组成：

- `Freqtrade` 策略开发与回测
- 基于 `python-okx` / `vectorbt` 的研究型脚本
- 面向研究因子的自建数据同步与标准化
- 面向 AI 的策略生成和协作文档

从现实角度看，它目前属于“研究验证阶段”，不是已经完成实盘工程化的系统。

## 当前目录结构

```text
AI-OuYi/
├── .opencode/
│   ├── opencode.json
│   └── knowledge-base/
│       ├── project.md
│       ├── docker.md
│       └── ai-collaboration.md
├── apps/
├── data/
├── docs/
├── execution/
│   ├── configs/
│   ├── freqtrade/
│   │   ├── docker-compose.yml
│   │   └── user_data/
│   └── templates/
├── research/
├── strategies/
├── AGENTS.md
├── AI_CONTEXT.md
└── requirements.txt
```

## 目录职责

- `execution/freqtrade/user_data/`: Docker 当前实际使用的数据、配置、策略和回测结果
- `strategies/`: 唯一策略源码目录，含自动生成策略、YAML 规范、CLI 生成器，并直接挂载到 Docker
- `research/`: 研究脚本、实验与报告
- `apps/prototypes/freqtrade_bot/`: 自定义实时机器人原型
- `execution/templates/freqtrade_user_data/`: Freqtrade 模板目录，不是当前主运行目录
- `data/`: 外部数据同步与标准化
- `execution/configs/`: 样例配置、参数快照与运行参考

补充说明：

- `execution/freqtrade/user_data/config.json` 属于本地运行态配置
- 需要可提交、可审查的参数与风控快照时，优先看 `execution/configs/strategy_config.snapshot.json`
- `execution/freqtrade/user_data/external_data/` 适合作为研究型外部因子数据统一落盘目录

## 技术栈

- 主框架: `Freqtrade`
- 交易所接口: `python-okx`, `ccxt`
- 研究分析: `pandas`, `vectorbt`
- 指标库: `talib`, `technical`, `qtpylib`

## 运行环境

### Docker 是主环境

当前最重要的运行事实来自：

- `execution/freqtrade/docker-compose.yml`
- `execution/freqtrade/user_data/config.json`
- `strategies/`

版本判断说明：

- 当前以 Docker 主环境为准理解 Freqtrade 版本与兼容性
- 本地 package 安装路径上出现过的历史兼容性问题，不应覆盖 Docker 口径

Docker 常用命令：

```bash
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker logs -f freqtrade
execution/scripts/simctl up
execution/scripts/simctl balance
execution/scripts/simctl status
```

策略目录挂载关系：

- 本地: `strategies/`
- 容器: `/freqtrade/user_data/strategies/`

因此策略开发默认只在本地 `strategies/` 进行，不再单独维护 `execution/freqtrade/user_data/strategies/` 副本。

### 本地 Python 是辅助环境

本地环境适合：

- 阅读和修改研究脚本
- 跑非 Docker 的研究回测
- 生成策略代码
- 编写与运行自建数据同步脚本

不应默认把本地环境视作与 Docker 完全等价。

## 数据架构补充结论

对于 OKX 合约研究，`Freqtrade` 继续作为主执行与回测框架，但不应被视作完整研究数据平台。

未来涉及以下因子时，优先走自建数据同步模块，而不是依赖 `Freqtrade` 的内建下载能力或临时在线抓取：

- `funding_rate`
- `mark / index / premium`
- `open_interest`
- `long-short ratio`
- `taker buy/sell volume`
- 交易规则类元数据，例如精度、最小下单量、杠杆档位、手续费档位

推荐的最小演进方向：

1. 建立独立的数据同步脚本或模块
2. 统一把研究因子落盘到 `execution/freqtrade/user_data/external_data/`
3. 策略与回测层只消费标准化后的本地数据
4. 将下载、补齐、缓存、版本化与策略逻辑解耦

## 当前研究方向

仓库当前的主线生成链至少包括：

1. `grid_ls_v1`
2. `multi_ls_v2`
3. `multi_ls_v3`

其中运行默认值以 `execution/freqtrade/docker-compose.yml` 和显式命令参数为准，不应再把某一个策略类名写成永远唯一的主线事实。

`MultiLS`、`LongShortSwitch`、`TrendFollowing` 等文件可视为更早期迭代痕迹，不再作为当前主线维护。

当前主线唯一允许的策略接入链是：

- `spec -> profile -> generated -> auto_json -> docker运行`

独立实验策略不再继续放在 `strategies/` 主目录，统一转入 `research/experiments/` 或 `research/archive/`。

## 当前已知状态

- 当前 `docker compose up` 默认启动策略为 `GridLsV1Strategy`
- 仓库内同时维护多条生成链，不能再把某一条写成唯一主线策略
- `Freqtrade protections` 已接入基础保护: `CooldownPeriod`、`StoplossGuard`、`MaxDrawdown`
- 文档、策略类名、Docker 副本之间存在一定漂移，需要核对后再行动
- 针对 `funding_rate` 这类合约因子，仓库已经开始引入外部数据文件读取路径，不再默认依赖单一内建下载链路

## 运行验证补充结论

截至 2026-04-02，关于 `Docker + OKX + 模拟盘 + VPN` 的结论如下：

- 宿主机在开启 VPN + `SOCKS5 7897` 时，可以直接连通 `OKX` 正式与模拟盘公共 WebSocket。
- Docker 容器内部也可以通过宿主机 `SOCKS5 7897` 直接连通 `wspap.okx.com`。
- `Freqtrade` 要接入 `OKX` 模拟盘，当前已知至少需要：
  1. `x-simulated-trading: 1`
  2. `ccxt_async_config.urls.api.ws = wss://wspap.okx.com:8443/ws/v5`
  3. `ccxt_async_config.wsProxy = socks5h://host.docker.internal:7897`
  4. `options.sandboxMode = true`
- 当前仓库里的运行态主配置已经按上述方向调整。

当前判断：

- `Freqtrade` 继续作为 OKX 的主执行框架是合理的。
- `dry-run` 继续作为模拟盘 / 执行验证入口是合理的。
- 但“是否已可长期稳定运行模拟盘、以及是否可切换到实盘”仍需继续观察和验证，不应提前下结论。

## 目录演进建议

如果项目后续明确走：

- `Freqtrade` 作为主执行框架
- 在其上持续扩展策略、因子、数据源、模拟盘 / 实盘能力

那么当前结构建议做“收口式优化”，但不建议激进重构。

推荐目标不是立刻推翻现状，而是逐步把仓库分成四层：

1. 执行层
   - `execution/` 为当前运行态主目录
   - 其中 `execution/freqtrade/` 是当前主执行目录
2. 策略层
   - `strategies/` 继续作为唯一策略源码层
3. 数据层
   - 逐步引入 `data/`
   - 承接 `funding_rate`、`mark/index/premium`、`open_interest` 等扩展数据
4. 研究层
   - 保留 `research/`
   - 语义上明确其为研究与实验，不与主执行层混用

更完整的结构建议见：

- `.opencode/knowledge-base/project-structure-plan.md`

## AI 接手建议

当 AI 接手任务时，建议顺序如下：

1. 阅读 `AI_CONTEXT.md`
2. 核对 `execution/freqtrade/docker-compose.yml`
3. 核对 `execution/freqtrade/user_data/config.json`
4. 检查最新回测产物
5. 阅读 `execution-architecture.md`
6. 按 `ai-development-sop.md` 执行
7. 只修改 `strategies/`，不要再同时改一份 Docker 副本
8. 涉及目录优化时，阅读 `project-structure-plan.md`

## OpenCode 加载说明

OpenCode 会优先加载：

1. `~/.config/opencode/instructions.md`
2. `.opencode/knowledge-base/project.md`
3. `.opencode/knowledge-base/ai-collaboration.md`
4. `.opencode/knowledge-base/execution-architecture.md`
5. `.opencode/knowledge-base/ai-development-sop.md`

如需更准确接手上下文，还应主动读取：

- `.opencode/knowledge-base/docker.md`
- `AI_CONTEXT.md`
- `AGENTS.md`
- `.opencode/knowledge-base/project-structure-plan.md`

---
最后更新: 2026-04-10
