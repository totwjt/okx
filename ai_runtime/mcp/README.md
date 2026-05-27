# AI-OuYi MCP

First-version MCP server for AI-OuYi strategy research workflows.

The MCP server is a typed wrapper around the existing Web API. The Web API remains the source of truth for strategy registry, profiles, jobs, artifacts, and evidence. MCP v1 must not write strategy YAML as its primary behavior, must not write directly to Postgres, and must not run Docker.

Default Web API base URL: `http://127.0.0.1:8123`.

Override:

```bash
export AI_OUYI_WEB_BASE_URL=http://127.0.0.1:8123
```

Before Step 1, run `preflight_web_api`. It verifies the configured base URL against:

```text
GET /api/health
GET /api/strategies
```

If Codex/MCP runs in a sandbox where `127.0.0.1` points somewhere else or local sockets are blocked, set `AI_OUYI_WEB_BASE_URL` to the reachable Web API address and rerun preflight. Do not advance SOP Step 1 until preflight passes.

After Step 5 materialization, run `static_validate_strategy` before any data or backtest job. It performs local static checks against materialized artifacts and advances SOP Step 6 only when generated files are internally consistent.

## Tool Specs

### preflight_web_api

Step: pre-SOP connectivity check.

Input schema:

```json
{
  "base_url": "string, optional"
}
```

Web API endpoints:

```text
GET /api/health
GET /api/strategies
```

Expected output:

```json
{
  "ok": true,
  "data": {
    "base_url": "http://127.0.0.1:8123",
    "base_url_source": "default | AI_OUYI_WEB_BASE_URL | argument",
    "healthy": true,
    "checks": [
      {"path": "/api/health", "ok": true, "status_code": 200},
      {"path": "/api/strategies", "ok": true, "status_code": 200}
    ]
  },
  "sop_step": {"advances": false}
}
```

Failure behavior:

- Return `ok=false` with the configured base URL, source, endpoint checks, and connection or HTTP error details.
- When local sockets are blocked by a command sandbox, return `likely_sandbox_permission_issue=true` and operator advice.
- Do not create strategy records, files, jobs, or database rows.

Advances SOP Step: no. It only proves the Web API is reachable before Step 1.

### create_strategy_hypothesis

Step: 1/10 strategy hypothesis registration.

Input schema:

```json
{
  "slug": "string",
  "name": "string",
  "description": "string",
  "profile_name": "string, default=draft",
  "thesis": "object"
}
```

Web API endpoint:

```text
POST /api/strategies
```

Expected output:

```json
{
  "ok": true,
  "data": {
    "strategy": "strategy record",
    "profile": "draft profile"
  },
  "sop_step": {"advances": true, "from": 1, "to": 2}
}
```

Failure behavior:

- Return structured error with HTTP status and API detail when available.
- Do not create files or write database rows directly.

Advances SOP Step: yes, from Step 1 to Step 2 if successful.

### update_strategy_definition

Step: 2/10 complete strategy spec, and optionally Step 3 profile defaults/overrides.

Input schema:

```json
{
  "slug": "string",
  "spec": "object",
  "profile_name": "string, optional",
  "profile_overrides": "object, optional",
  "profile_status": "string, default=candidate",
  "source": "string, default=ai_generated_spec",
  "validation": "object, default={}",
  "activate_profile": "boolean, default=true"
}
```

Web API endpoint:

```text
PUT /api/strategies/{slug}/definition
```

Expected output:

```json
{
  "ok": true,
  "data": {
    "strategy_slug": "string",
    "profile_name": "string",
    "strategy": "strategy record",
    "profile": "profile payload"
  },
  "sop_step": {"advances": true, "from": 2, "to": 4}
}
```

Failure behavior:

- Return validation failure from Web API.
- Do not fall back to manual YAML in MCP.
- AI should revise the spec unless the error exposes a generator/API gap.

Advances SOP Step: yes. It can cover Step 2 and Step 3 when a complete profile is supplied and activated; otherwise AI must explicitly keep Step 3 open.

### ensure_data

Step: 7/10 data preparation.

Input schema:

```json
{
  "strategy_slug": "string",
  "profile_name": "string, optional",
  "pair": "string, optional",
  "timeframe": "string, optional",
  "trading_mode": "string, optional",
  "timerange": "string, optional",
  "erase": "boolean, default=false",
  "no_parallel_download": "boolean, default=false",
  "candle_types": "array of strings, optional",
  "timeout_seconds": "integer, optional",
  "wait": "boolean, default=false",
  "poll_interval_seconds": "number, default=2",
  "timeout_wait_seconds": "integer, default=1800"
}
```

Web API endpoint:

```text
POST /api/data/ensure
GET  /api/jobs/{job_id} when wait=true
```

Expected output:

- Created `web_jobs` record.
- If `wait=true`, terminal job state: `success` or `failed`.

Failure behavior:

- Return structured API or timeout error.
- Never shell out to Docker from MCP.

Advances SOP Step: yes, from Step 7 to Step 8 only when data job succeeds. Job creation alone records that Step 7 is in progress.

### materialize_strategy

Step: 5/10 materialize runtime artifacts.

Input schema:

```json
{
  "strategy_slug": "string",
  "profile_name": "string, optional",
  "wait": "boolean, default=false",
  "poll_interval_seconds": "number, default=2",
  "timeout_wait_seconds": "integer, default=900"
}
```

Web API endpoint:

```text
POST /api/jobs with {"job_type": "materialize", "payload": {...}}
GET  /api/jobs/{job_id} when wait=true
```

Known alternate API:

```text
POST /api/runtime/materialize
```

MCP v1 uses `/api/jobs` so wait semantics and evidence are consistent.

Expected output:

- Created materialize job.
- If `wait=true`, terminal job result includes artifact details from the backend.

Failure behavior:

- Return structured error.
- Do not edit runtime strategy files.

Advances SOP Step: yes, from Step 5 to Step 6 only when materialization succeeds.

### static_validate_strategy

Step: 6/10 static validation after materialize.

Input schema:

```json
{
  "strategy_slug": "string",
  "expected_timeframe": "string, optional",
  "expected_can_short": "boolean, optional",
  "runtime_dir": "string, optional"
}
```

Local artifact inputs:

```text
execution/freqtrade/user_data/runtime_strategies/auto_<strategy_slug>.py
execution/freqtrade/user_data/runtime_strategies/auto_<strategy_slug>.json
```

Expected output:

- Python source exists and compiles.
- Strategy class exists.
- Optional expected `timeframe` and `can_short` match class attributes.
- Entry/exit signal columns `enter_long`, `enter_short`, `exit_long`, and `exit_short` are present in generated code.
- Params JSON exists, parses, and `strategy_name` matches the generated class.

Failure behavior:

- Return `ok=false` with all check evidence in `error.detail`.
- Do not import Freqtrade, run Docker, run backtests, or edit generated artifacts.

Advances SOP Step: yes, from Step 6 to Step 7 only when all static checks pass.

### run_backtest

Step: 8/10 backtest.

Input schema:

```json
{
  "strategy_slug": "string",
  "profile_name": "string, optional",
  "phase": "string, default=validation",
  "timerange": "string, optional",
  "force": "boolean, default=false",
  "timeout_seconds": "integer, optional",
  "wait": "boolean, default=false",
  "poll_interval_seconds": "number, default=2",
  "timeout_wait_seconds": "integer, default=1800",
  "extra_payload": "object, default={}"
}
```

Web API endpoint:

```text
POST /api/jobs with job_type=backtest
GET  /api/jobs/{job_id} when wait=true
```

Expected output:

- Created backtest job.
- Backtest result path should be under `execution/freqtrade/user_data/backtest_results/web_jobs/job_<job_id>/`.

Failure behavior:

- Return structured error.
- If trades are too few or metrics are weak, AI handles that as interpretation, not MCP failure.

Advances SOP Step: partial. It advances within Step 8 but validation gate is still required before lifecycle decisions.

### run_validation_gate

Step: 8/10 validation gate.

Input schema:

```json
{
  "strategy_slug": "string",
  "profile_name": "string, optional",
  "timerange": "string, optional",
  "min_trades": "integer, default=5",
  "min_profit_factor": "number, default=1.0",
  "force": "boolean, default=false",
  "timeout_seconds": "integer, optional",
  "wait": "boolean, default=false",
  "poll_interval_seconds": "number, default=2",
  "timeout_wait_seconds": "integer, default=1800",
  "extra_payload": "object, default={}"
}
```

Web API endpoint:

```text
POST /api/jobs with job_type=validation
GET  /api/jobs/{job_id} when wait=true
```

Expected output:

- Created validation job.
- If `wait=true`, result contains gate metrics, passed flag, failed checks, and backtest artifact references.

Failure behavior:

- Return structured API or timeout error.
- Gate failure is returned as successful job evidence with `passed=false`, not as a transport error.

Advances SOP Step: yes, from Step 8 to Step 9 only when the validation job finishes. AI still decides whether evidence is sufficient.

### get_strategy_state

Step: 4/10 registry state check, also useful throughout.

Input schema:

```json
{
  "slug": "string"
}
```

Web API endpoints:

```text
GET /api/strategies/{slug}
GET /api/strategies/{slug}/profiles
```

Expected output:

```json
{
  "ok": true,
  "data": {
    "strategy": "strategy record",
    "profiles": "profile list payload"
  }
}
```

Failure behavior:

- Return structured 404 or API error.

Advances SOP Step: yes, Step 4 can complete when registry state and active profile match the intended spec/profile.

### get_job

Step: evidence lookup for Steps 5, 7, and 8.

Input schema:

```json
{
  "job_id": "integer",
  "wait": "boolean, default=false",
  "poll_interval_seconds": "number, default=2",
  "timeout_wait_seconds": "integer, default=1800"
}
```

Web API endpoint:

```text
GET /api/jobs/{job_id}
```

Expected output:

- Current job record.
- If `wait=true`, terminal job record.

Failure behavior:

- Return structured API or timeout error.

Advances SOP Step: no by itself. It supplies evidence for another Step.

### report_system_gap

Step: 10/10 system-gap review, and any blocked Step.

Input schema:

```json
{
  "title": "string",
  "description": "string",
  "impact_scope": "string",
  "current_status": "string, default=open",
  "recommended_api": "string, optional",
  "recommended_ui": "string, optional",
  "related_strategy_slug": "string, optional",
  "blocking_step": "string, optional",
  "metadata": "object, default={}"
}
```

Web API endpoint:

```text
Known missing API in v1.
Recommended future endpoints:
POST /api/system-gaps
GET  /api/system-gaps
```

Expected output:

- Local structured gap JSON file under `ai_runtime/mcp/system_gaps/`.
- The file is an interim record until Web API supports system gaps.

Failure behavior:

- Return structured filesystem error.
- Never write Postgres directly.

Advances SOP Step: no automatically. It can unblock a fallback decision or contribute to Step 10 closeout.

## Known Missing APIs

- Workflow state: `GET /api/strategies/{slug}/workflow`.
- Workflow advancement: `POST /api/strategies/{slug}/workflow/advance`.
- System gaps: `POST /api/system-gaps`, `GET /api/system-gaps`.
- Data coverage: `GET /api/data/coverage`.
- Combined materialize and static check: `POST /api/strategies/{slug}/pipeline/materialize-and-check`.

MCP v1 reports these through `report_system_gap`; backend implementation should be handled as a separate Phase 4 task list.
