# AI Runtime Implementation Task Flow

Updated: 2026-05-26

## Goal

Build an AI-friendly runtime layer so strategy generation is guided by SOP, constrained by tools, and still backed by the existing Web API as the source of truth.

Current standard flow:

```text
AI professional judgment -> MCP tool -> Web API -> registry/job/evidence -> AI interpretation
```

Do not replace Web API. Wrap it.

## Context To Read First

Before implementing, read:

- `AGENTS.md`
- `docs/operations/ai-strategy-generation-sop.md`
- `docs/operations/web-job-api.md`
- `web/backend/app/routers/registry.py`
- `web/backend/app/routers/jobs.py`
- `web/backend/app/routers/data.py`
- `web/backend/app/services/registry_service.py`
- `web/backend/app/services/jobs_service.py`

## Directory Decision

Create and use root-level `ai_runtime/`.

Reason:

- Skill/MCP are AI operation infrastructure, not Web product code.
- They should not be mixed into `strategies/`, because they are not strategy source.
- They should not be mixed into `execution/`, because they are not Freqtrade runtime.
- They should not be mixed into `web/`, because Web API remains the source of truth and should not depend on AI-specific packaging.

## Phase 1: Skill

Create:

```text
ai_runtime/skills/ai-ouyi-strategy-research/SKILL.md
```

The skill must enforce:

- every strategy task starts by declaring:
  - SOP path
  - current Step
  - strategy-level vs system-level scope
- AI must perform professional reasoning for:
  - hypothesis
  - spec design
  - profile/risk bounds
  - result interpretation
  - system-gap detection
- mechanical actions must use MCP/Web API when available.
- manual YAML is fallback only.
- terminal commands are fallback only and must produce a system-gap note if they represent missing API/MCP capability.

Acceptance checks:

- Skill references `docs/operations/ai-strategy-generation-sop.md`.
- Skill lists the 10 strategy steps.
- Skill explicitly says scaffold is not final spec.
- Skill requires Step advancement after each completed action.

## Phase 2: MCP Design

Create:

```text
ai_runtime/mcp/README.md
```

Define first-version tools:

```text
create_strategy_hypothesis
update_strategy_definition
ensure_data
materialize_strategy
run_backtest
run_validation_gate
get_strategy_state
get_job
report_system_gap
```

Each tool spec must include:

- input schema
- Web API endpoint called
- expected output
- failure behavior
- whether it advances SOP Step

Acceptance checks:

- No MCP tool writes YAML as its primary behavior.
- No MCP tool writes directly to Postgres in v1.
- Every tool has an explicit Web API mapping or is marked as a known missing API.

## Phase 3: MCP Server Implementation

Create:

```text
ai_runtime/mcp/pyproject.toml
ai_runtime/mcp/ai_ouyi_mcp/__init__.py
ai_runtime/mcp/ai_ouyi_mcp/server.py
ai_runtime/mcp/ai_ouyi_mcp/client.py
ai_runtime/mcp/ai_ouyi_mcp/schemas.py
```

Implementation constraints:

- Use the local Web API base URL, default `http://127.0.0.1:8123`.
- Allow override by environment variable `AI_OUYI_WEB_BASE_URL`.
- Use typed request/response models.
- Poll job tools until terminal status only when the tool explicitly supports `wait=true`.
- Return structured errors, not raw tracebacks.
- Never shell out to Docker in v1.

Suggested tool mappings:

| MCP tool | Web API |
|---|---|
| `create_strategy_hypothesis` | `POST /api/strategies` |
| `update_strategy_definition` | `PUT /api/strategies/{slug}/definition` |
| `ensure_data` | `POST /api/data/ensure` |
| `materialize_strategy` | `POST /api/runtime/materialize` or `POST /api/jobs` with `materialize` |
| `run_backtest` | `POST /api/jobs` with `backtest` |
| `run_validation_gate` | `POST /api/jobs` with `validation` |
| `get_strategy_state` | `GET /api/strategies/{slug}` and `GET /api/strategies/{slug}/profiles` |
| `get_job` | `GET /api/jobs/{job_id}` |
| `report_system_gap` | create local structured gap file until Web API exists |

Acceptance checks:

- Can create a draft strategy through MCP.
- Can write a complete spec through MCP.
- Can launch data/backtest/validation jobs through MCP.
- Can fetch job result through MCP.
- Can report a system gap without breaking the flow.

## Phase 4: Backend Flow-State Gaps

Review whether Web backend needs new API/state for:

- current SOP Step
- completed evidence flags
- system gaps
- blocked steps
- next allowed actions

If missing, create a backend task list first. Do not hack this only into MCP.

Likely API additions:

```text
GET  /api/strategies/{slug}/workflow
POST /api/strategies/{slug}/workflow/advance
POST /api/system-gaps
GET  /api/system-gaps
```

Acceptance checks:

- System can answer “what is the current required next step?”
- AI cannot silently skip required evidence.
- Missing tool/API capabilities are visible in Web/backend records.

## Phase 5: Smoke Flow

Create:

```text
ai_runtime/smoke/strategy_flow_smoke.md
```

Run a temporary strategy through:

```text
Step 1 hypothesis
Step 2 complete spec
Step 3 profile
Step 4 registry state check
Step 5 materialize
Step 6 data ensure
Step 7 backtest
Step 8 validation
Step 9 result interpretation
Step 10 system-gap review
```

Acceptance checks:

- Smoke strategy can be deleted afterward.
- No hand-written YAML is needed.
- No direct Docker command is needed from AI.
- Backtest result points to `web_jobs/job_<job_id>/`.
- Any unsupported flow is logged as a system gap.

## Definition Of Done

- `ai_runtime/skills/ai-ouyi-strategy-research/SKILL.md` exists.
- `ai_runtime/mcp/README.md` exists with tool specs.
- MCP server can call at least strategy create, definition update, job create, job fetch.
- Smoke flow document records commands/results.
- Existing Web API remains the source of truth.
- `docs/operations/ai-strategy-generation-sop.md` remains the authoritative SOP.

## Important Non-Goals

- Do not replace Web API.
- Do not create a second database.
- Do not make MCP write strategy YAML as normal path.
- Do not make MCP run Docker directly in v1.
- Do not optimize strategy profitability in this task.
