# AI Context

## 一句话概括

这是一个围绕 OKX 合约交易展开的 Freqtrade 研究仓库，当前主价值在于“快速验证策略假设”，不是“已经证明可稳定盈利的实盘系统”。

## 接手时先确认的 5 件事

1. 当前真实运行目录是不是 `execution/freqtrade/user_data/`
2. 容器 `freqtrade` 当前默认启动的是哪个策略类名
3. Docker 是否仍把本地 `strategies/` 直接挂载到容器策略目录
4. 最近回测结果对应的是哪一个策略类名
5. 这次任务是否允许修改功能代码，还是只允许修改文档/配置/AI 文件

## 当前仓库状态

- `execution/freqtrade/docker-compose.yml` 当前默认通过 `trade` 启动 `GridLsV1Strategy`
- 本地 `strategies/` 是唯一策略源码目录，并直接挂载进 Docker
- 当前版本判断以 Docker 环境为准；关于本地 package 安装引发的旧兼容性记忆，不作为当前判断依据
- 当前生成链下至少存在 `grid_ls_v1`、`multi_ls_v2`、`multi_ls_v3` 三个策略族；默认启动策略不等于唯一策略事实
- 历史回测里可能还会看到 `MultiLSStrategy`、`LongShortSwitchStrategy` 等旧名字，它们不再是当前主线
- `execution/templates/freqtrade_user_data/` 是模板目录，不是主要运行目录
- 当前执行架构决策: `Freqtrade` 为主执行层，自定义 OKX 机器人仅为原型参考
- 当前研究架构补充结论: `Freqtrade` 继续负责回测与执行，但研究型因子数据不应长期依赖其内建下载链路
- 对 `funding_rate`、`mark / index / premium`、`open_interest`、`long-short ratio`、`taker buy/sell volume` 等合约因子，建议逐步迁移到自建 `data/` 数据层统一管理

## 2026-04-02 验证结论

### Docker / 模拟盘 / 实盘

- 宿主机在开启 VPN + `SOCKS5 7897` 的前提下，可直接连接：
  - `wss://wspap.okx.com:8443/ws/v5/public`
  - `wss://ws.okx.com:8443/ws/v5/public`
- Docker 容器内也可在同样代理前提下，直接通过 Python `websockets` 连上 `wspap` 并完成公共频道订阅。
- 这说明“本机 + VPN 自动交易”从网络可达性角度是可行的，问题不在宿主机网络本身。
- `Freqtrade` 侧要想接 OKX 模拟盘，不能只依赖 `sandboxMode`：
  - 需要显式添加 `x-simulated-trading: 1`
  - 需要把异步 WebSocket 地址显式切到 `wss://wspap.okx.com:8443/ws/v5`
  - 需要在 `ccxt_async_config` 里显式配置 `wsProxy=socks5h://host.docker.internal:7897`
- 当前已把上述配置写入 `execution/freqtrade/user_data/config.json`。
- 最新状态：
  - 模拟盘私有 REST 和私有 WebSocket 已验证可用
  - `Freqtrade` 自身的 `watch_ohlcv` 长连接在代理环境下仍会偶发超时或 `1006` 断开
  - 当前运行基线已切到 `execution/freqtrade/user_data/config.json` 中 `exchange.enable_ws = false`，优先使用 REST 模式保证稳定性
- 仍未完成的验证：
  1. REST 基线的长时间稳定运行验证
  2. “实盘”真实下单验证

### 当前可信结论

- `Freqtrade` 作为 OKX 的主执行框架，继续保留是合理的。
- `dry-run` 作为执行链路和状态机验证器是可用方向。
- “是否已可稳定用于模拟盘长跑”当前以 REST 模式继续验证，WebSocket 模式暂不算稳定。
- “是否已可直接切到实盘”目前不能下结论。

## 运行入口

### Docker

```bash
docker compose -f execution/freqtrade/docker-compose.yml up -d freqtrade
docker exec freqtrade freqtrade backtesting -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker exec freqtrade freqtrade trade -c /freqtrade/user_data/config.json -s GridLsV1Strategy
docker logs -f freqtrade
execution/scripts/simctl up
execution/scripts/simctl summary
execution/scripts/simctl recent-trades-summary 5
execution/scripts/simctl daily-report 7
execution/scripts/simctl pair-stats
execution/scripts/simctl exit-reason-stats
execution/scripts/simctl direction-stats
execution/scripts/simctl strategy-sample-status
execution/scripts/simctl strategy-natural-trades 5
execution/scripts/simctl strategy-review-gate 10
execution/scripts/simctl balance
execution/scripts/simctl status
execution/scripts/simctl force-enter SOL/USDT:USDT long 50 1
```

当前策略问题清单见：

- [docs/operations/strategy-issue-list.md](/Users/wangjiangtao/Documents/AI/AI-OuYi/docs/operations/strategy-issue-list.md)

当前主线策略参数治理已升级为 `Spec + Profile + Promotion`：

- `strategies/spec/` 管策略结构与默认值
- `strategies/profiles/` 管具体参数档案与 active profile
- `strategies/cli.py profile ...` 管 profile 创建、激活与晋级
- 当前活跃 profile 需要按各自策略目录分别核对，例如 `strategies/profiles/*/_active.yaml`

### 本地研究脚本

```bash
python3 research/experiments/multi_trend_backtest.py --symbol SOL-USDT --timeframe 15m
```

## 重要边界

- Freqtrade 策略、vectorbt 回测、自定义 WebSocket 机器人不是同一套执行层。
- `Freqtrade` 不是完整的研究数据平台，不应默认承担所有历史因子采集与标准化工作。
- 文档里出现的策略名与实际类名可能不完全一致，执行前必须核对。
- 研究结果不等于可上线执行策略，尤其是 OKX 永续合约场景。
- 容器内 `/freqtrade/user_data/strategies/` 来自仓库根目录 `strategies/` 挂载，不应再单独维护第二份副本。

## 数据层建议

- 对标准 OHLCV 回测，继续优先使用 `Freqtrade` / `ccxt` 下载链路。
- 对研究型合约因子，优先建设自有 `data/` 数据层，负责下载、补齐、缓存、版本化和统一落盘。
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
- 如果涉及目录演进，先读 `.opencode/knowledge-base/project-structure-plan.md`。
