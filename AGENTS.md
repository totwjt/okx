# OKX 超短线量化机器人

## 项目结构

```
AI-OuYi/
├── .opencode/              # OpenCode 项目配置（重要！）
│   └── knowledge-base/    # 项目知识库
│
├── strategies/             # 策略源码
├── backtest/              # 回测脚本
├── freqtrade_bot/         # 实时机器人
├── config/                # 本地配置
├── user_data/             # 空的 Freqtrade 模板
├── ft_userdata/           # Docker 数据（正在使用）
├── requirements.txt       # Python 依赖
└── .env                   # API 配置
```

## 技术栈

- 主框架: Freqtrade
- API: python-okx / CCXT
- 数据: pandas, vectorbt

## 运行环境

### 方式1: Docker（推荐）

所有命令通过 Docker 执行：
```bash
# 回测
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s VolumeRatioStrategyV1

# 模拟盘
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s VolumeRatioStrategyV1 --dry-run
```

### 方式2: 本地（需先激活虚拟环境）

```bash
# 激活环境
source venv/bin/activate

# 回测
freqtrade backtesting -c config/config.json -s VolumeRatioStrategy

# 模拟盘
freqtrade trade -c config/config.json -s VolumeRatioStrategy --dry-run
```

## 项目知识库

详细说明请查看：
- `.opencode/knowledge-base/project.md` - 项目完整说明
- `.opencode/knowledge-base/docker.md` - Docker 环境说明

## 待验证

- 实时交易
- 模拟盘测试