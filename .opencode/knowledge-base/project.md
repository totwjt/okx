# AI-OuYi 项目知识库

## 项目概述

这是一个面向 OKX 的量化研究仓库，核心由三部分组成：

- `Freqtrade` 策略开发与回测
- 基于 `python-okx` / `vectorbt` 的研究型脚本
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
├── backtest/
├── config/
├── freqtrade_bot/
├── ft_userdata/
│   ├── docker-compose.yml
│   └── user_data/
├── strategies/
├── user_data/
├── AGENTS.md
├── AI_CONTEXT.md
└── requirements.txt
```

## 目录职责

- `ft_userdata/user_data/`: Docker 当前实际使用的数据、配置、策略和回测结果
- `strategies/`: 唯一策略源码目录，含自动生成策略、YAML 规范、CLI 生成器，并直接挂载到 Docker
- `backtest/`: 自定义研究脚本，适合快速验证想法
- `freqtrade_bot/`: 自定义实时机器人原型
- `user_data/`: Freqtrade 模板目录，不是当前主运行目录

补充说明：

- `ft_userdata/user_data/config.json` 属于本地运行态配置，通常不纳入 git
- 需要可提交、可审查的参数与风控快照时，优先看 `config/strategy_config.json`

## 技术栈

- 主框架: `Freqtrade`
- 交易所接口: `python-okx`, `ccxt`
- 研究分析: `pandas`, `vectorbt`
- 指标库: `talib`, `technical`, `qtpylib`

## 运行环境

### Docker 是主环境

当前最重要的运行事实来自：

- `ft_userdata/docker-compose.yml`
- `ft_userdata/user_data/config.json`
- `strategies/`

版本判断说明：

- 当前以 Docker 主环境为准理解 Freqtrade 版本与兼容性
- 本地 package 安装路径上出现过的历史兼容性问题，不应覆盖 Docker 口径

Docker 常用命令：

```bash
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker logs -f freqtrade
```

策略目录挂载关系：

- 本地: `strategies/`
- 容器: `/freqtrade/user_data/strategies/`

因此策略开发默认只在本地 `strategies/` 进行，不再单独维护 `ft_userdata/user_data/strategies/` 副本。

### 本地 Python 是辅助环境

本地环境适合：

- 阅读和修改研究脚本
- 跑非 Docker 的研究回测
- 生成策略代码

不应默认把本地环境视作与 Docker 完全等价。

## 当前研究方向

仓库当前只保留一条策略主线：

1. `MultiLsV2Strategy`

`MultiLS`、`LongShortSwitch`、`TrendFollowing` 等文件可视为历史迭代痕迹，不再作为当前主线维护。

## 当前已知状态

- 当前默认策略为 `MultiLsV2Strategy`
- Docker 默认启动策略已切到多空主线
- `Freqtrade protections` 已接入基础保护: `CooldownPeriod`、`StoplossGuard`、`MaxDrawdown`
- 文档、策略类名、Docker 副本之间存在一定漂移，需要核对后再行动

## AI 接手建议

当 AI 接手任务时，建议顺序如下：

1. 阅读 `AI_CONTEXT.md`
2. 核对 `ft_userdata/docker-compose.yml`
3. 核对 `ft_userdata/user_data/config.json`
4. 检查最新回测产物
5. 阅读 `execution-architecture.md`
6. 按 `ai-development-sop.md` 执行
7. 只修改 `strategies/`，不要再同时改一份 Docker 副本

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

---
最后更新: 2026-03-31
