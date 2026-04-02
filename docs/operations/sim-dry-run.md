# 模拟盘运行基线

当前项目的推荐运行基线是：

- `Freqtrade`
- `dry_run = true`
- `exchange.enable_ws = false`
- 通过容器内 REST API 做状态观测和强制开平仓

## 统一入口

使用脚本：

```bash
execution/scripts/simctl
```

常用命令：

```bash
execution/scripts/simctl up
execution/scripts/simctl ps
execution/scripts/simctl ping
execution/scripts/simctl summary
execution/scripts/simctl show-config
execution/scripts/simctl balance
execution/scripts/simctl profit
execution/scripts/simctl status
execution/scripts/simctl recent-trades 5
execution/scripts/simctl recent-trades-summary 5
execution/scripts/simctl daily-report 7
execution/scripts/simctl pair-stats
execution/scripts/simctl exit-reason-stats
execution/scripts/simctl direction-stats
execution/scripts/simctl strategy-sample-status
execution/scripts/simctl strategy-natural-trades 5
execution/scripts/simctl strategy-review-gate 10
execution/scripts/simctl logs 120
execution/scripts/simctl db-last-trades 5
execution/scripts/simctl db-last-orders 8
```

强制开平仓：

```bash
execution/scripts/simctl force-enter BTC/USDT:USDT long 50 1
execution/scripts/simctl force-exit 13
```

推荐先看：

```bash
execution/scripts/simctl summary
```

它会汇总：

- 账户余额
- 模拟盘累计盈亏
- 已关闭交易数
- 胜率
- 当前打开的仓位

如果想看更可读的成交与日报：

```bash
execution/scripts/simctl recent-trades-summary 5
execution/scripts/simctl daily-report 7
```

如果想看策略表现拆解：

```bash
execution/scripts/simctl pair-stats
execution/scripts/simctl exit-reason-stats
execution/scripts/simctl direction-stats
```

如果想单独追踪当前主策略 `MultiLsV2Strategy` 的自然样本：

```bash
execution/scripts/simctl strategy-sample-status
execution/scripts/simctl strategy-natural-trades 5
execution/scripts/simctl strategy-review-gate 10
```

## 为什么当前默认禁用 WebSocket

在当前机器的 `VPN + SOCKS5 7897 + Docker + OKX` 环境下：

- 模拟盘私有 REST 可用
- 模拟盘私有 WebSocket 可用
- 但 `Freqtrade` 自身的 `watch_ohlcv` 长连接仍会偶发超时或 `1006` 断开

因此当前优先使用 REST 模式作为稳定基线。

## 当前已验证通过的链路

- 模拟盘账户余额读取
- 模拟盘持仓读取
- 强制开仓
- 强制平仓
- 交易与订单落库

## 关键文件

- 运行配置: [execution/freqtrade/user_data/config.json](/Users/wangjiangtao/Documents/AI/AI-OuYi/execution/freqtrade/user_data/config.json)
- Docker 入口: [execution/freqtrade/docker-compose.yml](/Users/wangjiangtao/Documents/AI/AI-OuYi/execution/freqtrade/docker-compose.yml)
- 统一脚本: [execution/scripts/simctl](/Users/wangjiangtao/Documents/AI/AI-OuYi/execution/scripts/simctl)
