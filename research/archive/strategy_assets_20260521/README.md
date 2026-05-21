# Strategy Assets Archive 2026-05-21

This archive preserves the file-based strategy assets that were removed from the active `strategies/` source surface during the PostgreSQL strategy registry migration.

Archived groups:

- `spec/`: legacy YAML strategy definitions
- `profiles/`: legacy profile directories and active pointers
- `generated/`: legacy generated strategy Python files
- `root_auto/`: legacy root-level `auto_*.py` and `auto_*.json` runtime artifacts

The active strategy source of truth is now PostgreSQL database `ouyi_db`, populated via:

```bash
.venv/bin/python strategies/cli.py registry import-files
```

Runtime artifacts should be regenerated with:

```bash
.venv/bin/python strategies/cli.py registry materialize <strategy_slug>
```

Do not move these files back to `strategies/` unless explicitly rolling back the registry migration.
