# AI Runtime Strategy Flow Smoke

Run date: 2026-05-26

SOP: `docs/operations/ai-strategy-generation-sop.md`

Scope: system-level AI Runtime smoke. This smoke verifies MCP wrappers against the Web API source of truth. It does not optimize profitability and does not promote any strategy lifecycle status.

## Summary

Temporary smoke strategy:

```text
ai_runtime_smoke_0526_215610
```

Result: passed Runtime smoke.

The MCP server successfully called Web API for:

- strategy draft creation
- complete spec/profile update
- registry state fetch
- materialize job
- data ensure job
- backtest job
- validation job
- job fetch
- system-gap report

No hand-written strategy YAML was used. MCP did not directly write Postgres and did not run Docker. Docker was only invoked behind the Web Job API as expected.

## Preliminary Issue

An earlier smoke attempt created:

```text
ai_runtime_smoke_0526_215333
```

That attempt failed at Step 2 because the running Web API process was stale and did not expose:

```text
PUT /api/strategies/{slug}/definition
```

After restarting `web/start_web.sh`, OpenAPI showed the current routes:

```text
/api/strategies/{slug}/definition
/api/data/ensure
```

The smoke was then rerun successfully with `ai_runtime_smoke_0526_215610`.

## Step Results

### Step 1: Hypothesis

Tool:

```text
create_strategy_hypothesis
```

Result: success.

AI judgment:

- Market: OKX `SOL/USDT:USDT` perpetual futures.
- Purpose: runtime smoke only.
- Direction: long-only; `can_short=false`.
- Invalidation: results are not used for tuning or lifecycle promotion.

### Step 2: Complete Spec

Tool:

```text
update_strategy_definition
```

Result: success.

Spec source: copied from an existing valid registry strategy and adjusted for smoke timeranges and metadata. This is acceptable for Runtime smoke because the goal is Web API/MCP flow verification, not strategy ideation.

Important fields:

```text
timeframe: 15m
trading_mode: futures
margin_mode: isolated
can_short: false
train_timerange: 20250101-20250110
validation_timerange: 20250111-20250120
test_timerange: 20250121-20250131
```

### Step 3: Profile

Tool:

```text
update_strategy_definition
```

Result: success.

Profile:

```text
default
status: candidate
source: ai_runtime_smoke
active_profile: default
```

### Step 4: Registry State Check

Tool:

```text
get_strategy_state
```

Result: success.

The strategy exists in the Web registry with active profile `default`.

### Step 5: Materialize

Tool:

```text
materialize_strategy(wait=true)
```

Web job:

```text
job_id: 68
job_type: materialize
status: success
```

Artifacts:

```text
execution/freqtrade/user_data/runtime_strategies/auto_ai_runtime_smoke_0526_215610.py
execution/freqtrade/user_data/runtime_strategies/auto_ai_runtime_smoke_0526_215610.json
```

### Step 6: Data Ensure

Tool:

```text
ensure_data(wait=true)
```

Web job:

```text
job_id: 69
job_type: data_ensure
status: success
timerange: 20250101-20250131
```

### Step 7: Backtest

Tool:

```text
run_backtest(wait=true)
```

Web job:

```text
job_id: 70
job_type: backtest
status: success
timerange: 20250101-20250110
```

Result directory:

```text
execution/freqtrade/user_data/backtest_results/web_jobs/job_70
```

Backtest zip:

```text
execution/freqtrade/user_data/backtest_results/web_jobs/job_70/backtest-result-2026-05-26_13-56-27.zip
```

Metrics:

```text
total_trades: 4
wins: 3
losses: 1
winrate: 0.75
profit_total: 0.0038983416899999995
profit_factor: 1.4889056108602279
max_drawdown_account: 0.007880056367253502
```

Interpretation: Runtime backtest execution and artifact isolation passed. The sample is intentionally tiny and is not research evidence for strategy quality.

### Step 8: Validation

Tool:

```text
run_validation_gate(wait=true)
```

Web job:

```text
job_id: 71
job_type: validation
status: success
timerange: 20250111-20250120
```

Result directory:

```text
execution/freqtrade/user_data/backtest_results/web_jobs/job_71
```

Validation zip:

```text
execution/freqtrade/user_data/backtest_results/web_jobs/job_71/backtest-result-2026-05-26_13-56-34.zip
```

Metrics:

```text
total_trades: 1
wins: 0
losses: 1
winrate: 0.0
profit_total: -0.0078682494
profit_factor: 0.0
max_drawdown_account: 0.007868249399999968
```

Gate result:

```text
passed: false
failed_checks:
- profit_total=-0.007868 < min_profit=0.000000
- avg_profit=-0.031912 < min_avg_profit=0.000000
```

Interpretation: The validation job completed correctly and returned gate evidence. Gate failure is a strategy-result outcome, not a Runtime failure.

### Step 9: Result Interpretation

Runtime interpretation:

- MCP can create strategy records through Web API.
- MCP can write complete spec/profile through Web API.
- MCP can launch and wait for Web jobs.
- MCP can fetch terminal job evidence.
- Backtest and validation artifacts are isolated by job directory.

Strategy interpretation:

- This temporary strategy is not promoted.
- The validation sample has one losing trade and fails the configured gate.
- No profitability conclusion should be drawn from this smoke.

### Step 10: System-Gap Review

Tool:

```text
report_system_gap
```

Local gap file:

```text
ai_runtime/mcp/system_gaps/20260526-215634_workflow_and_cleanup_apis_missing_for_ai_runtime_smoke.json
```

System gaps:

- Web backend lacks durable workflow state APIs.
- Web backend lacks `POST /api/system-gaps`.
- Web backend lacks a safe strategy archive/delete endpoint for smoke cleanup.
- A stale Web API process can expose an older route set; operational checks should confirm OpenAPI before smoke runs.

## Acceptance Checklist

- Skill exists: yes.
- MCP design exists: yes.
- MCP server can create a draft strategy: yes.
- MCP server can write a complete spec: yes.
- MCP server can launch data/backtest/validation jobs: yes.
- MCP server can fetch job results: yes.
- Existing Web API remains the source of truth: yes.
- No normal-path YAML write: yes.
- No direct Docker command from MCP: yes.
- Backtest result points to `web_jobs/job_<job_id>/`: yes, `job_70`.
- Unsupported flow logged as system gap: yes.
- Smoke strategy cleanup through Web API: not yet supported; logged as system gap.
