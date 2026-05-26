# AI Runtime

This directory contains the AI-facing runtime layer for AI-OuYi.

It is intentionally separate from:

- `web/`: the business system and source-of-truth API.
- `strategies/`: strategy specs, profiles, and generation services.
- `execution/`: Docker/Freqtrade runtime.

## Purpose

`ai_runtime/` is for tools that guide and constrain AI operators:

- project skill instructions for strategy research workflows
- MCP server wrappers around the Web API
- strongly typed tool schemas
- smoke tests for AI-driven strategy flows
- system-gap reporting templates

The AI runtime must not become a second strategy registry or a second execution layer.
It should call the existing Web API and report missing capabilities when a workflow is not yet supported.

## Target Layout

```text
ai_runtime/
├── README.md
├── TASKS.md
├── skills/
│   └── ai-ouyi-strategy-research/
│       └── SKILL.md
├── mcp/
│   ├── README.md
│   ├── pyproject.toml
│   └── ai_ouyi_mcp/
│       ├── __init__.py
│       ├── server.py
│       ├── client.py
│       └── schemas.py
└── smoke/
    └── strategy_flow_smoke.md
```

## Rules

- Web API remains the source of truth.
- MCP tools should call Web API first, not write database rows directly.
- Terminal commands are allowed only for development, diagnostics, or temporary fallback.
- Any fallback that bypasses Web API must be recorded as a system gap.
- Strategy YAML files are backup/fallback artifacts, not the standard AI generation path.
