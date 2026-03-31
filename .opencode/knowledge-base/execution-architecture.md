# 执行架构决策

## 当前结论

当前项目的主执行层选择如下：

1. `Freqtrade` 作为主交易执行框架
2. `strategies/` 下的 `MultiLsV2Strategy` 作为唯一主线策略
3. `freqtrade_bot/realtime_bot.py` 仅保留为原型参考，不作为当前生产执行主线

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

## 明确边界

### 主执行层

- `ft_userdata/docker-compose.yml`
- `ft_userdata/user_data/config.json`
- `strategies/auto_multi_ls_v2.py`
- `strategies/cli.py`

### 非主执行层

- `freqtrade_bot/realtime_bot.py`

它目前不具备以下生产能力：

- 私有下单与撤单链路
- 成交回报驱动的持仓状态同步
- OMS / EMS 语义
- 失败重试与断线恢复
- 风控熔断闭环

因此不能把它视为当前可上线执行引擎。

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
- 如果修改 `freqtrade_bot/realtime_bot.py`，默认视作原型研发，不代表主执行架构改变
