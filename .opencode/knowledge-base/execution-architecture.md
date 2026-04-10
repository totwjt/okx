# 执行架构决策

## 当前结论

当前项目的主执行层选择如下：

1. `Freqtrade` 作为主交易执行框架
2. `strategies/` 是唯一策略源码目录；当前运行默认策略由 `execution/freqtrade/docker-compose.yml` 决定，当前为 `GridLsV1Strategy`
3. `apps/prototypes/freqtrade_bot/realtime_bot.py` 仅保留为原型参考，不作为当前生产执行主线

补充说明：

- 主执行层仍然是 `Freqtrade`
- 研究数据层应逐步从 `Freqtrade` 内建下载能力中解耦
- 对合约特有因子，推荐建设独立数据同步模块
- `OKX` 模拟盘接入不应默认认为与正式盘完全等价，需单独处理代理、WebSocket 地址与请求头

## 为什么这样决策

当前仓库已经完成了：

- 主线策略统一
- 策略源码目录统一
- 参数基线统一
- 三段式回测工作流
- 成本模型与风险模型规范化

在这个阶段，继续把执行主线放在 `Freqtrade` 上，收益最大、风险最小，因为：

- 已有 Docker 运行环境
- 已有回测 / hyperopt / trade 工作流
- 已有配置、日志、数据库和 Web API 能力
- 可以先验证策略与风控边界，再决定是否需要自建执行层

但这不代表研究数据也应该全部绑定在 `Freqtrade` 上。对 OKX 永续研究来说，以下因子更适合交给独立数据层维护：

- `funding_rate`
- `mark / index / premium`
- `open_interest`
- `long-short ratio`
- `taker buy/sell volume`

## 明确边界

### 主执行层

- `execution/freqtrade/docker-compose.yml`
- `execution/freqtrade/user_data/config.json`
- `strategies/auto_grid_ls_v1.py`
- `strategies/auto_multi_ls_v2.py`
- `strategies/auto_multi_ls_v3.py`
- `strategies/cli.py`

### 推荐独立数据层

- `data/` 下的数据同步与标准化脚本
- `execution/freqtrade/user_data/external_data/` 作为外部因子统一落盘目录

### 非主执行层

- `apps/prototypes/freqtrade_bot/realtime_bot.py`

它目前不具备以下生产能力：

- 私有下单与撤单链路
- 成交回报驱动的持仓状态同步
- OMS / EMS 语义
- 失败重试与断线恢复
- 风控熔断闭环

因此不能把它视为当前可上线执行引擎。

## 2026-04-02 运行验证补充

围绕 `OKX` 模拟盘与 `Docker` 的补充结论：

- 宿主机 + VPN 可直接连 `OKX` 正式 / 模拟盘公共 WebSocket。
- Docker 容器本身也可通过宿主机 `SOCKS5 7897` 直连 `wspap`。
- 当前瓶颈已从“宿主机网络问题”收缩为“`Freqtrade -> ccxt.pro` 的 WebSocket 代理与模拟盘配置问题”。

当前已知对 `Freqtrade` 有效的关键配置方向：

1. `headers.x-simulated-trading = 1`
2. `options.sandboxMode = true`
3. `ccxt_async_config.urls.api.ws = wss://wspap.okx.com:8443/ws/v5`
4. `ccxt_async_config.wsProxy = socks5h://host.docker.internal:7897`

当前状态：

- 上述配置已写入运行态配置
- `freqtrade` 已可带着这套配置启动并进入 `RUNNING`
- 模拟盘私有 REST 与私有 WebSocket 已验证成功
- `Freqtrade` 的 WebSocket `watch_ohlcv` 在当前代理环境下仍会偶发超时或 `1006` 断开
- 当前稳定基线是在运行配置中设置 `exchange.enable_ws = false`，优先走 REST 模式
- 日常运行与观测入口统一到 `execution/scripts/simctl`
- 是否已通过长时间模拟盘验证、以及是否可直接切到实盘，仍未完成最终确认

## 什么时候再考虑自建执行层

满足以下条件后，才建议进入“自定义 OKX 执行层”路线：

1. `Freqtrade` 无法满足策略表达能力
2. `Freqtrade` 无法满足执行延迟要求
3. `Freqtrade` 无法满足风控或订单编排需求
4. 主线策略已经通过稳定的样本外验证

在这之前，优先把策略、回测、成本、风控做扎实。

## 未来执行层演进路径

### 阶段 A

继续以 `Freqtrade` 为主执行层：

- 策略迭代
- 参数验证
- 风控边界固化
- 运行监控完善
- 自建研究数据同步模块
- 将外部因子接入回测与策略读取层
- 继续补全模拟盘 / 实盘配置与运行验证

### 阶段 B

如果后续确有必要，再新增独立执行层目录，例如：

- `execution/`
- `oms/`
- `risk/`

并显式拆出：

- signal layer
- portfolio / risk layer
- execution layer

## AI 实施规则

- 任何涉及“执行架构切换”的修改，都必须先更新本文件
- 如果只是优化策略，不要顺手把项目从 `Freqtrade` 切到自定义执行层
- 如果修改 `apps/prototypes/freqtrade_bot/realtime_bot.py`，默认视作原型研发，不代表主执行架构改变
- 如果新增研究因子数据源，优先理解为“数据层增强”，而不是“执行架构切换”
