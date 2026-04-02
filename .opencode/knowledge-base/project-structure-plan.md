# 当前项目结构

## 结构目标

当前仓库已按长期形态重构为“执行层、策略层、数据层、研究层、文档层”分离的结构。

重构目标是：

- 保留 `Freqtrade` 作为主执行框架
- 保留 `strategies/` 作为唯一策略源码目录
- 把运行态、研究态、数据同步和原型程序从语义上拆开

## 当前目录结构

```text
AI-OuYi/
├── .opencode/                           # AI 知识库与协作说明
├── apps/
│   └── prototypes/
│       └── freqtrade_bot/              # 原型级实时机器人
├── data/
│   └── sync/
│       └── okx/                        # OKX 外部数据同步脚本
├── docs/
│   └── operations/                     # 运行与版本文档
├── execution/
│   ├── configs/                        # 样例配置与参数快照
│   ├── freqtrade/                      # 当前主执行目录
│   │   ├── docker-compose.yml
│   │   └── user_data/                  # Freqtrade 当前真实运行目录
│   └── templates/
│       └── freqtrade_user_data/        # Freqtrade 模板目录
├── research/
│   ├── experiments/                    # 研究脚本
│   └── reports/                        # 研究报告
├── strategies/                         # 唯一策略源码目录
├── AGENTS.md
├── AI_CONTEXT.md
└── requirements.txt
```

## 目录职责

### 执行层

- `execution/freqtrade/` 是当前唯一主执行目录
- `execution/freqtrade/user_data/` 是当前真实运行目录
- `execution/freqtrade/docker-compose.yml` 是当前 Docker 启动入口
- `execution/configs/` 存放样例配置和参数快照
- `execution/templates/` 存放模板态 Freqtrade 目录

### 策略层

- `strategies/` 是唯一策略源码目录
- 包含：
  - YAML 规范
  - 自动生成策略
  - 策略模板
  - 策略 CLI

### 数据层

- `data/sync/` 承接外部数据同步
- 当前已收口 `OKX funding rate` 相关脚本
- 后续建议继续承接：
  - `mark / index / premium`
  - `open_interest`
  - `long-short ratio`
  - `taker buy/sell volume`

### 研究层

- `research/experiments/` 放实验脚本
- `research/reports/` 放分析报告
- 研究层不应承担主执行职责

### 原型层

- `apps/prototypes/freqtrade_bot/` 保留实时机器人原型
- 默认视作原型研发，不代表主执行架构改变

## 当前事实来源

涉及运行事实时，优先级如下：

1. `execution/freqtrade/docker-compose.yml`
2. `execution/freqtrade/user_data/config.json`
3. `strategies/`
4. 最近运行日志与交易数据库
5. 说明性文档

## 当前最重要的边界

1. `Freqtrade` 仍然是主执行框架
2. `strategies/` 仍然是唯一策略源码目录
3. `apps/prototypes/freqtrade_bot/` 仍然不是主执行层
4. `research/` 仍然只是研究验证层
5. `data/` 才是后续扩展因子和外部数据的正确归宿

## 后续建议

1. 继续把 `Docker + OKX 模拟盘 + 代理` 跑稳
2. 在 `data/` 下继续补齐外部因子同步
3. 在 `strategies/` 下逐步细化 `factors/` 或等价目录
4. 继续把运行文档和 AI 文档对齐到当前结构

## 一句话结论

当前仓库已经从“以运行目录为中心”调整为“按分层语义组织”的结构。

后续所有新增能力，默认应先判断它属于：

- 执行层
- 策略层
- 数据层
- 研究层
- 原型层

不要再把不同层的代码混放到同一个目录里。
