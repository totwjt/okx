# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-30 09:21:05
**Project:** OKX Scalping Bot（超短线量能策略机器人）

## OVERVIEW
OKX 平台全自动超短线交易系统，核心策略：缩量下跌买入（volume_ratio < 0.7 + 价格下跌），放量上涨卖出（volume_ratio > 1.5 + 价格上涨）。

## STRUCTURE
```
./
├── AI_CONTEXT.md    # 需求文档（开发依据）
└── [TODO] freqtrade/  # 主框架
└── [TODO] strategies/  # 策略文件
└── [TODO] backtest/   # 回测脚本
└── [TODO] config/     # 配置文件
```

## TECH STACK
| 组件 | 工具 | 用途 |
|------|------|------|
| 主框架 | **Freqtrade** | 策略/回测/实盘/风控一站式 |
| 回测引擎 | VectorBT | 向量化快速回测 |
| API 客户端 | python-okx / CCXT | OKX 接口封装 |
| 数据处理 | pandas + pandas-ta | 指标计算 |

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 需求文档 | AI_CONTEXT.md | 开发依据 |
| Freqtrade 策略 | strategies/ | 继承 IStrategy |
| 回测脚本 | backtest/ | VectorBT |
| 配置 | config/ | API keys, 参数 |

## CONVENTIONS
- **Python**: 类型提示全覆盖，pytest 测试
- **Freqtrade**: 遵循官方策略模板结构
- **API**: 使用 python-okx 优先，CCXT 备选
- **配置**: API Key 加密存储，环境变量优先

## ANTI-PATTERNS (THIS PROJECT)
- 禁止在代码中硬编码 API Key/Secret
- 禁止直接实盘测试，未在模拟盘验证的策略不得上线
- 禁止忽略手续费与滑点（回测必须模拟真实费率）
- 禁止无风控下单（必须带 TP/SL）

## UNIQUE STYLES
- **策略参数**: volume_ratio 阈值、K 线周期、MA 窗口可配置
- **风控**: 单笔风险 ≤ 2%，总浮亏 > 5% 自动平仓
- **回测**: 重点输出最大回撤 %、回撤持续时间

## COMMANDS
```bash
# Freqtrade 启动
freqtrade trade -c config/config.json

# 回测
freqtrade backtesting -c config/config.json

# 参数优化
freqtrade hyperopt -c config/config.json
```

## NOTES
- 用户位于美国加州 San Jose，需注意本地法规
- 优先模拟盘验证，后小资金实盘
- 延迟要求：信号检测到下单 < 500ms
