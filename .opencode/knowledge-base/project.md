# AI-OuYi 项目知识库

## 项目概述

OKX 超短线量化机器人，基于 Freqtrade 框架开发。

## 项目结构

```
AI-OuYi/
├── .opencode/              # OpenCode 项目配置（重要！）
│   ├── opencode.json       # 项目级配置
│   └── knowledge-base/    # 项目知识库
│       ├── project.md      # 本文件
│       └── docker.md      # Docker 环境说明
│
├── strategies/             # 策略源码（主目录）
│   ├── volume_ratio_strategy.py      # 量比策略
│   ├── emarsi_momentum_scalping.py   # EMA+RSI 剥头皮策略
│   └── __init__.py
│
├── backtest/               # 回测脚本
│   ├── custom_backtest.py
│   ├── vbt_backtest.py
│   └── multi_trend_backtest.py
│
├── freqtrade_bot/          # 实时机器人
│   └── realtime_bot.py
│
├── config/                 # 配置文件
│   ├── config.json        # 主配置
│   └── strategy_config.json
│
├── user_data/              # 空的 Freqtrade 模板目录（可删除）
│   ├── strategies/         # 仅含 sample_strategy.py
│   └── data/
│
├── ft_userdata/            # Docker 数据目录（正在使用）
│   ├── docker-compose.yml
│   └── user_data/         # 挂载到容器 /freqtrade/user_data
│       ├── config.json    # Docker 内配置
│       ├── strategies/    # Docker 内策略
│       ├── data/          # K线数据
│       └── backtest_results/
│
├── requirements.txt       # Python 依赖
├── .env                   # API 密钥配置
├── AGENTS.md              # 项目说明
└── AI_CONTEXT.md          # 运行时上下文
```

## 技术栈

- **主框架**: Freqtrade
- **API**: python-okx / CCXT
- **数据分析**: pandas, vectorbt, pandas-ta
- **技术指标**: talib, technical, qtpylib

## 依赖安装

```bash
# 方式1: 直接安装
pip install -r requirements.txt

# 方式2: 使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 方式3: 使用 Docker（已在 AI_CONTEXT.md 说明）
docker exec freqtrade freqtrade <command>
```

## 启动命令

### 本地运行（需要先激活虚拟环境）

```bash
# 激活虚拟环境
source venv/bin/activate

# 回测
freqtrade backtesting -c config/config.json -s VolumeRatioStrategy

# 模拟盘
freqtrade trade -c config/config.json -s VolumeRatioStrategy --dry-run
```

### Docker 运行

```bash
# 回测
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s VolumeRatioStrategyV1

# 查看日志
docker logs -f freqtrade
```

## 重要提示

1. **Docker 是主要运行环境** - 所有交易命令通过 Docker 执行
2. **策略同步** - 修改 `strategies/` 后需复制到 Docker：
   ```bash
   docker cp strategies/volume_ratio_strategy.py freqtrade:/freqtrade/user_data/strategies/
   ```
3. **数据位置** - Docker 内路径 `/freqtrade/user_data/`
4. **配置文件** - 优先使用 `user_data/config.json`

## 当前策略状态

| 策略 | 1m收益 | 5m收益 | 状态 |
|------|--------|--------|------|
| EMA+RSI | -7.04% | -7.63% | ❌ 亏损 |
| 量比策略 | -99.85% | -84.11% | ❌ 严重亏损 |

**注意**: 两个策略当前均为亏损状态，不建议实盘。

## AI 上下文加载

当打开新的 OpenCode session 时，系统会自动加载：
1. 全局指令: `~/.config/opencode/instructions.md`
2. 项目知识库: `.opencode/knowledge-base/project.md`（本文件）
3. Docker 说明: `.opencode/knowledge-base/docker.md`

这确保 AI 能够快速理解项目结构和运行环境。

---
*最后更新: 2026-03-31*