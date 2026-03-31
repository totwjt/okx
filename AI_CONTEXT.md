# AI Context

## 一句话概括

这是一个围绕 OKX 合约交易展开的 Freqtrade 研究仓库，当前主价值在于“快速验证策略假设”，不是“已经证明可稳定盈利的实盘系统”。

## 接手时先确认的 5 件事

1. 当前真实运行目录是不是 `ft_userdata/user_data/`
2. 容器 `freqtrade` 是否仍以 `MultiLsV2Strategy` 作为默认启动策略
3. Docker 是否仍把本地 `strategies/` 直接挂载到容器策略目录
4. 最近回测结果对应的是哪一个策略类名
5. 这次任务是否允许修改功能代码，还是只允许修改文档/配置/AI 文件

## 当前仓库状态

- `ft_userdata/docker-compose.yml` 默认通过 `trade` 启动 `MultiLsV2Strategy`
- 本地 `strategies/` 是唯一策略源码目录，并直接挂载进 Docker
- 当前版本判断以 Docker 环境为准；关于本地 package 安装引发的旧兼容性记忆，不作为当前判断依据
- 历史回测里可能还会看到 `MultiLSStrategy`、`LongShortSwitchStrategy` 等旧名字，它们不再是当前主线
- `user_data/` 更像模板目录，不是主要运行目录
- 当前执行架构决策: `Freqtrade` 为主执行层，自定义 OKX 机器人仅为原型参考
- 当前研究架构补充结论: `Freqtrade` 继续负责回测与执行，但研究型因子数据不应长期依赖其内建下载链路
- 对 `funding_rate`、`mark / index / premium`、`open_interest`、`long-short ratio`、`taker buy/sell volume` 等合约因子，建议逐步迁移到自建数据同步模块

## 运行入口

### Docker

```bash
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s MultiLsV2Strategy
docker logs -f freqtrade
```

### 本地研究脚本

```bash
python3 backtest/multi_trend_backtest.py --symbol BTC-USDT --timeframe 15m
```

## 重要边界

- Freqtrade 策略、vectorbt 回测、自定义 WebSocket 机器人不是同一套执行层。
- `Freqtrade` 不是完整的研究数据平台，不应默认承担所有历史因子采集与标准化工作。
- 文档里出现的策略名与实际类名可能不完全一致，执行前必须核对。
- 研究结果不等于可上线执行策略，尤其是 OKX 永续合约场景。
- 容器内 `/freqtrade/user_data/strategies/` 来自仓库根目录 `strategies/` 挂载，不应再单独维护第二份副本。

## 数据层建议

- 对标准 OHLCV 回测，继续优先使用 `Freqtrade` / `ccxt` 下载链路。
- 对研究型合约因子，优先建设自有 `data_sync` 模块，负责下载、补齐、缓存、版本化和统一落盘。
- 推荐最小优先级顺序:
  1. `funding_rate`
  2. `mark / index / premium`
  3. `open_interest`
  4. `long-short ratio`
  5. `taker buy/sell volume`
- 未来如果回测或策略依赖上述因子，应优先从统一数据目录读取，而不是每次在线临时拉接口。

## 对 AI 的工作建议

- 优先做一致性检查: 文档、配置、策略类名、Docker 副本是否一致。
- 对交易相关结论保持保守: 先看回测结果，再看成本模型，再看执行可行性。
- 如果用户要求“不要改功能代码”，只更新文档、知识库、流程说明和 AI 约束。
- 如果涉及执行层路线调整，先读 `execution-architecture.md` 再动手。
