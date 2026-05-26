# ai-ouyi-strategy-research

Use this skill for AI-OuYi strategy research, generation, transformation, validation, and result interpretation tasks.

Authoritative SOP: `docs/operations/ai-strategy-generation-sop.md`.

## Opening Declaration

Every strategy task must begin with an explicit declaration:

```text
本次按 docs/operations/ai-strategy-generation-sop.md 执行。
当前 Step: <n>/10 <step name>。
作用域判断: <strategy-level | system-level | both>。
```

If the task is about AI Runtime, MCP, Web API, generator, lifecycle, evidence, or workflow capability rather than one strategy's parameters, treat issues as system-level unless proven otherwise.

## Standard 10 Steps

1. Strategy hypothesis registration.
2. Generate or complete the strategy spec.
3. Generate profile parameter records.
4. Write or sync the registry state.
5. Materialize runtime artifacts.
6. Static validation.
7. Data preparation.
8. Backtest and validation gate.
9. Lifecycle advancement decision.
10. Closeout and report.

After each completed action, advance or restate the current Step and report:

- professional judgment made by AI
- MCP/Web API calls used
- produced artifacts or records
- strategy-level issues
- system-level issues

## AI Responsibilities

AI must perform the professional reasoning for:

- market and instrument assumptions
- falsifiable hypothesis
- spec design and indicator selection
- entry and exit logic
- profile and risk bounds
- train, validation, and test split discipline
- result interpretation
- overfitting and sample-size concerns
- system-gap detection

The Web scaffold is not a final strategy spec. It is only a conservative process template used to unblock registry and materialization workflows. For concrete strategy ideas such as crash rebound, funding-rate arbitrage, breakout, trend following, or grid variants, AI must produce a complete professional spec before treating Step 2 as complete.

## Mechanical Actions

Use MCP tools when available. MCP must wrap the Web API because Web API is the source of truth.

Preferred mechanical path:

```text
AI professional judgment -> MCP tool -> Web API -> registry/job/evidence -> AI interpretation
```

Manual YAML edits are fallback only. If manual YAML is used, report a system gap explaining which Web API or MCP capability is missing.

Terminal commands are fallback only for diagnostics or temporary unblock work. If a terminal command replaces a missing API/MCP action, report a system gap.

Never directly write Postgres, directly write strategy YAML as the normal path, or shell out to Docker as an AI operation path when MCP/Web API can perform the action.

## Tooling Expectations

Use these MCP tools when available:

- `create_strategy_hypothesis` for Step 1.
- `update_strategy_definition` for Step 2 and Step 3 profile activation/overrides when bundled with the spec update.
- `get_strategy_state` for Step 4.
- `materialize_strategy` for Step 5.
- `ensure_data` for Step 7.
- `run_backtest` and `run_validation_gate` for Step 8.
- `get_job` for job evidence.
- `report_system_gap` for missing API/MCP/backend capability.

If a tool fails, classify the failure:

- current strategy spec/profile issue
- data/environment issue
- system-level API, generator, registry, lifecycle, or evidence gap

## Step Advancement Rules

Do not silently skip required evidence.

Advance a Step only when:

- AI has completed the required professional judgment for that Step.
- Required MCP/Web API call succeeded, or an explicit fallback and system-gap record exists.
- Artifacts or records can be named.
- Remaining blockers are clearly stated.

If blocked, keep the current Step unchanged and state the next allowed action.

## Forbidden Patterns

- Treating scaffold output as the final strategy spec.
- Jumping directly from a strategy idea to Python code.
- Using the test set for repeated parameter tuning.
- Hand-editing `auto_<slug>.py` runtime artifacts.
- Maintaining a separate Docker strategy copy.
- Running Docker directly from MCP v1.
- Writing directly to Postgres from MCP v1.
