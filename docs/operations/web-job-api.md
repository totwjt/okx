# Web Job API 操作说明

更新: 2026-05-26

## 目标

把策略流程里的固定机械步骤封装到 Web API/job 队列：

- 数据准备：`data_ensure`
- 运行产物生成：`materialize`
- 回测：`backtest`
- 验证闸门：`validation`

AI 仍负责策略假设、spec 设计、参数边界、结果解释和系统级问题判断。

## 数据确保

接口：

```http
POST /api/data/ensure
```

示例：

```json
{
  "strategy_slug": "okx_sol_crash_rebound_v1",
  "profile_name": "default",
  "timerange": "20250101-20260526",
  "no_parallel_download": true,
  "timeout_seconds": 1800
}
```

说明：

- 如果不传 `pair`，使用 `spec.market.pair`。
- 如果不传 `timeframe`，使用 `spec.timeframe`。
- 如果不传 `trading_mode`，使用 `spec.trading_mode`。
- 如果不传 `timerange`，会根据 train / validation / test 自动推导，开放结束时间会补到当前日期。
- 底层通过 `docker compose run --rm freqtrade download-data ...` 执行，不要求 `freqtrade` 容器常驻。

返回的是 `web_jobs` 任务记录。用下面接口查询：

```http
GET /api/jobs/{job_id}
```

## 回测

接口：

```http
POST /api/jobs
```

示例：

```json
{
  "job_type": "backtest",
  "payload": {
    "strategy_slug": "okx_sol_crash_rebound_v1",
    "profile_name": "default",
    "phase": "validation",
    "timerange": "20251001-20251130",
    "force": true,
    "timeout_seconds": 900
  }
}
```

底层通过 `docker compose run --rm freqtrade backtesting ...` 执行，不要求 `freqtrade` 容器常驻。

每个回测/验证 job 使用独立结果目录：

```text
execution/freqtrade/user_data/backtest_results/web_jobs/job_<job_id>/
```

这样 train、validation 或多个候选并发运行时，不会互相串扰 `latest zip` 识别。

## Validation Gate

接口：

```http
POST /api/jobs
```

示例：

```json
{
  "job_type": "validation",
  "payload": {
    "strategy_slug": "okx_sol_crash_rebound_v1",
    "profile_name": "default",
    "timerange": "20251001-20251130",
    "min_trades": 5,
    "min_profit_factor": 1.0,
    "force": true,
    "timeout_seconds": 900
  }
}
```

返回结果会包含：

- `metrics`
- `gate`
- `passed`
- `failed_checks`
- `backtest_zip`
- `materialize`
- 实际执行命令

## 任务列表

```http
GET /api/jobs?limit=100
GET /api/jobs/{job_id}
GET /api/backtests/results
GET /api/validation/results
```

## 当前约束

- Docker daemon 仍然必须可用。
- OKX 数据下载仍可能遇到交易所限流；任务失败时看 `error_summary`。
- API 封装的是机械执行，不替代 AI 对样本量、过拟合和市场适用性的判断。
