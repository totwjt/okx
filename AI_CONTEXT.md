# OKX 超短线自动交易系统 AI 开发需求文档

**文档版本**：v1.1（2026-03-29）
**项目名称**：OKX Scalping Bot（超短线量能策略机器人）
**编制日期**：2026-03-29
**目标**：提供完整、结构化需求文档，供 AI（或开发工程师）直接识别并启动开发。

## 1. 项目背景与概述

用户需在 **欧易（OKX）** 平台搭建一个**全自动交易系统**，优先实现**超短线（scalping）交易**。

**核心策略**：
- **买入信号**：缩量 + 下跌（volume 萎缩 + 价格下跌 → 潜在反转买入）
- **卖出信号**：放量 + 上涨（volume 放大 + 价格上涨 → 获利卖出）

**附加要求**：
- 完整**风控机制**（止损、仓位控制、最大回撤限制等）
- 支持**回测**，重点分析最大回撤百分比（Max Drawdown %）、回撤持续时间、回撤占比等，用于策略筛选与优化
- 支持**实时数据驱动**（WebSocket），回测使用历史数据，两者逻辑必须一致
- 先在**模拟盘（Paper Trading）**验证，后小资金实盘

**交易标的**：优先支持 OKX 股票永续合约（Stock Perpetuals，如 AAPL、TSLA 等）或主流加密现货/合约（BTC-USDT 等）。

**目标**：实现从回测 → 参数优化 → 实时执行 → 风控的全闭环系统。

## 2. 功能需求（优先级：高→低）

### 2.1 策略引擎
- 实时/历史 volume MA 或量比（Volume Ratio）判断：
  - **量比计算**：`volume_ratio = current_vol / rolling_mean_vol`（窗口可配置）
  - 买入信号：`volume_ratio < 0.7`（缩量） + 价格下跌
  - 卖出信号：`volume_ratio > 1.5`（放量） + 价格上涨
- 支持 K 线周期：1s / 1m / 5m 等
- 策略参数可配置（MA 周期、缩放阈值、K 线粒度等）

### 2.2 实时交易执行
- 通过 WebSocket 订阅实时数据（`tickers`、`candle1m`、`trades`）
- 信号触发后自动下单（市价/限价 + 带 TP/SL）
- 支持批量单、算法委托

### 2.3 风控系统
- 单笔风险 ≤ 总资金 1-2%
- 总浮亏 > 5% 自动平仓所有仓位
- 最大回撤限额（每日/总）自动停止交易
- 实时监控仓位、余额、风险率

### 2.4 回测与分析
- 使用历史 K 线 + 逐笔成交数据
- 输出报告包含：胜率、盈亏比、**最大回撤 %**、回撤持续时间、回撤占比
- 支持参数优化（Hyperopt 或类似），筛选“在跌幅 < X% 市场表现最佳”的策略

### 2.5 其他功能
- 一键切换模拟盘（Demo）环境
- Telegram/WebUI 实时推送信号、持仓、回撤预警
- 详细日志记录（信号、下单、风控动作）

## 3. 非功能需求
- **性能**：信号检测到下单延迟 < 500ms（WebSocket 异步处理）
- **稳定性**：支持 7×24 小时运行，自动重连、异常处理
- **安全性**：API Key 加密存储，仅授予交易权限；优先使用模拟盘
- **可扩展性**：易添加新策略、支持多币种
- **手续费与滑点**：回测中必须模拟真实 OKX 费率
- **合规提醒**：用户位于美国加州 San Jose，需注意本地法规

## 4. 技术栈要求（必须使用最有效开源 + 官方工具）

| 层级       | 推荐工具                  | 安装方式                          | 作用                              |
|------------|---------------------------|-----------------------------------|-----------------------------------|
| API 客户端 | python-okx / CCXT        | `pip install python-okx ccxt`    | 官方封装 + 统一接口              |
| 主框架     | **Freqtrade**            | GitHub clone                     | 策略/回测/实盘/风控一站式        |
| 回测引擎   | VectorBT + Freqtrade内置 | `pip install vectorbt`           | 向量化快速回测 + 跌幅分析        |
| 数据处理   | pandas + pandas-ta       | `pip install pandas pandas-ta`   | volume MA、量比计算              |
| 实时 WS    | asyncio + OKX WebSocket  | -                                | 1s 级 tick/trades 推送           |

**优先推荐**：以 **Freqtrade** 作为主框架，大幅减少开发工作量。

## 5. 官方文档与资源（2026 年最新）

- **OKX V5 API 官方文档**（REST + WebSocket 全覆盖）：
  https://www.okx.com/docs-v5/en/

- **关键 WebSocket 通道**：
  - 公共行情：`wss://ws.okx.com:8443/ws/v5/public`
  - 模拟盘：`wss://wspap.okx.com:8443/ws/v5/public`
  - 实时数据：`tickers`、`candle1m`、`trades`、`candle1s`

- **历史数据接口**：
  - `/api/v5/market/history-candles`
  - `/api/v5/market/history-trades`

- **Trades 字段**：`sz`（成交量）、`px`（价格）、`ts`（时间戳）
- **Candle 字段**：`vol`、`volCcy`

## 6. 开源项目地址（全部活跃维护）

- **Freqtrade**（强烈推荐主框架）：
  https://github.com/freqtrade/freqtrade
  文档：https://www.freqtrade.io

- **python-okx**（官方 SDK）：
  https://github.com/okxapi/python-okx

- **CCXT**（万能交易所库）：
  https://github.com/ccxt/ccxt

- **VectorBT**（最快回测库）：
  https://github.com/polakowo/vectorbt

- **Hummingbot**（备选高频框架）：
  https://github.com/hummingbot/hummingbot

## 7. 交付物要求

AI/开发者需依次交付：
1. Freqtrade 自定义策略模板（包含 volume_ratio / 缩量放量逻辑 + 风控）
2. VectorBT 独立回测脚本（支持 OKX 数据导入 + 最大回撤分析）
3. 完整实时机器人主循环（WebSocket 订阅 + 信号判断 + 下单）
4. Docker 部署方案（支持 7×24 运行）
5. 模拟盘测试指南 + 参数优化示例

## 8. 开发启动指令

**AI 请立即开始开发**：
优先输出 **Freqtrade 自定义策略模板**（最推荐路线）。
代码需包含：
- 策略类（继承 `IStrategy`）
- `populate_indicators`（实现 volume MA / volume_ratio 计算）
- `populate_entry_trend` / `populate_exit_trend`（买入卖出逻辑）
- 自定义风控（最大回撤限制等）
- OKX 配置说明（spot / futures + Demo 环境）