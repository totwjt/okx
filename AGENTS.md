# OKX 超短线量化机器人

## 项目结构
```
AI-OuYi/
├── strategies/          # 策略源码
├── backtest/           # 回测脚本
├── freqtrade_bot/      # 实时机器人
├── config/             # 配置文件
├── requirements.txt    # Python 依赖
└── .env               # API 配置
```

## 技术栈
- 主框架: Freqtrade
- API: python-okx / CCXT
- 数据: pandas

## 启动命令
```bash
# 安装依赖
pip install -r requirements.txt

# 回测
freqtrade backtesting -c config/config.json -s VolumeRatioStrategy

# 模拟盘
freqtrade trade -c config/config.json -s VolumeRatioStrategy --dry-run
```

## 待验证
- 实时交易
- 模拟盘测试
