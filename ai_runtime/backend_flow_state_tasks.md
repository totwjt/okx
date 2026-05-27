# Backend Flow-State Task List

Updated: 2026-05-26

## Context

Phase 4 of `ai_runtime/TASKS.md` requires reviewing whether the Web backend can represent AI strategy-generation workflow state.

Current finding: the Web API supports strategy registry, profiles, runtime materialization, data ensure, jobs, backtests, and validation results. It does not yet expose durable workflow state, system-gap records, blocked steps, or next allowed actions.

Do not solve this only in MCP. MCP v1 can report local gap files, but Web/backend must become the source of truth for workflow state.

## Required Backend APIs

### P0: Workflow State

Add:

```text
GET /api/strategies/{slug}/workflow
```

Response should include:

- `strategy_slug`
- `current_step`
- `completed_steps`
- `blocked_step`
- `next_allowed_actions`
- `required_evidence`
- `latest_jobs`
- `system_gaps`
- `updated_at`

Acceptance:

- Web/API can answer: "what is the current required next step?"
- Missing evidence prevents silent step skipping.

### P0: Workflow Advancement

Add:

```text
POST /api/strategies/{slug}/workflow/advance
```

Request should include:

- `from_step`
- `to_step`
- `ai_notes`
- `api_calls`
- `artifacts`
- `evidence`
- `strategy_issues`
- `system_issues`

Acceptance:

- Advancement is auditable.
- Advancement can be rejected when required evidence is missing.
- Step advancement is tied to existing registry/job/evidence records where possible.

### P0: System Gap Registry

Add:

```text
POST /api/system-gaps
GET /api/system-gaps
GET /api/system-gaps/{gap_id}
PATCH /api/system-gaps/{gap_id}
```

Fields:

- `title`
- `description`
- `impact_scope`
- `current_status`
- `recommended_api`
- `recommended_ui`
- `related_strategy_slug`
- `blocking_step`
- `metadata`
- `created_at`
- `updated_at`

Acceptance:

- Missing MCP/Web/backend capabilities are visible in backend records.
- MCP `report_system_gap` can switch from local JSON to Web API without changing AI workflow.

### P1: Data Coverage

Add:

```text
GET /api/data/coverage
```

Inputs:

- `strategy_slug`
- `profile_name`
- `pair`
- `timeframe`
- `trading_mode`
- `timerange`

Acceptance:

- API reports data start/end, missing intervals, candle types, and whether futures-specific data is sufficient.
- Step 7 can complete based on evidence, not only on download job success.

### P1: Materialize And Static Check

Add:

```text
POST /api/strategies/{slug}/pipeline/materialize-and-check
```

Behavior:

- Materialize runtime artifacts.
- Compile generated Python.
- Check `class_name`, `timeframe`, `can_short`, dataframe references, parameter names, and protections.
- Return artifact hashes and static check results.

Acceptance:

- Step 5 and Step 6 can be completed through Web API evidence.
- AI does not need terminal fallback for normal static validation.

### P1: Smoke Strategy Cleanup

Add one of:

```text
DELETE /api/strategies/{slug}
POST /api/strategies/{slug}/archive
```

Acceptance:

- Runtime smoke tests can create and clean up temporary strategy records without manual DB work.
- Destructive delete should be restricted to draft/test strategies, or archive should be preferred.

## Suggested Tables

```text
strategy_generation_steps
system_gaps
```

`strategy_generation_steps` should reference strategy slug and optionally job IDs/artifact records.

`system_gaps` should be general enough for AI Runtime, Web API, generator, data, lifecycle, and UI gaps.

## Migration Order

1. Add `system_gaps` table and API.
2. Add workflow read endpoint that derives current state from existing strategy/profile/job data plus explicit step records.
3. Add workflow advance endpoint with evidence checks.
4. Add data coverage endpoint.
5. Add materialize-and-check endpoint.
6. Add smoke cleanup archive/delete endpoint.

## Current MCP v1 Bridge

Until `POST /api/system-gaps` exists, MCP writes local JSON files under:

```text
ai_runtime/mcp/system_gaps/
```

This is an interim bridge, not the final source of truth.
