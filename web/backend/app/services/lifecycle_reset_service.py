from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.jobs_service import BACKTEST_RESULT_DIR, init_job_schema
from app.services.paper_run_service import init_paper_run_schema
from app.services.system_check import COMPOSE_FILE, PROJECT_ROOT, _load_strategy_services


REGISTRY_TABLES = (
    "strategy_runtime_artifacts",
    "strategy_validation_results",
    "strategy_promotion_events",
    "strategy_profiles",
    "strategy_specs",
)
WEB_TABLES = ("web_paper_runs", "web_jobs")


def reset_all_strategies() -> dict[str, Any]:
    db_service, runtime_service = _load_strategy_services()
    db_service.init_schema()
    init_job_schema()
    init_paper_run_schema()

    table_counts: dict[str, int] = {}
    artifact_paths: list[str] = []
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            for table_name in (*REGISTRY_TABLES, *WEB_TABLES):
                if not _table_exists(cur, table_name):
                    table_counts[table_name] = 0
                    continue
                cur.execute(f"select count(*)::int as count from {table_name}")
                table_counts[table_name] = int(cur.fetchone()["count"])

            if _table_exists(cur, "strategy_runtime_artifacts"):
                cur.execute("select artifact_path from strategy_runtime_artifacts")
                artifact_paths.extend(str(row["artifact_path"]) for row in cur.fetchall())
            if _table_exists(cur, "strategy_validation_results"):
                cur.execute("select artifact_path from strategy_validation_results where artifact_path is not null")
                artifact_paths.extend(str(row["artifact_path"]) for row in cur.fetchall())

            for table_name in (*WEB_TABLES, *REGISTRY_TABLES):
                if _table_exists(cur, table_name):
                    cur.execute(f"delete from {table_name}")

    deleted_paths = _delete_associated_artifacts(
        artifact_paths,
        runtime_strategy_dir=runtime_service.RUNTIME_STRATEGY_DIR,
        runtime_param_dir=runtime_service.RUNTIME_PARAM_DIR,
    )
    service_pause = _pause_freqtrade_service()
    return {
        "reset": True,
        "table_counts": table_counts,
        "deleted_artifact_paths": deleted_paths,
        "service_pause": service_pause,
    }


def _table_exists(cur: Any, table_name: str) -> bool:
    cur.execute("select to_regclass(%s) as table_name", (f"public.{table_name}",))
    return cur.fetchone()["table_name"] is not None


def _delete_associated_artifacts(
    artifact_paths: list[str],
    *,
    runtime_strategy_dir: Path,
    runtime_param_dir: Path,
) -> list[str]:
    candidates: set[Path] = set()
    for raw_path in artifact_paths:
        path = Path(raw_path)
        if raw_path.startswith("/freqtrade/user_data/"):
            path = PROJECT_ROOT / "execution/freqtrade/user_data" / raw_path.removeprefix("/freqtrade/user_data/")
        candidates.add(path)

    for directory in (runtime_strategy_dir, runtime_param_dir):
        if directory.exists():
            candidates.update(directory.glob("auto_*"))
    if BACKTEST_RESULT_DIR.exists():
        candidates.update(BACKTEST_RESULT_DIR.iterdir())

    deleted: list[str] = []
    for path in sorted(candidates, key=lambda item: str(item)):
        if not _is_project_artifact_path(path) or not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        deleted.append(str(path))
    return deleted


def _is_project_artifact_path(path: Path) -> bool:
    resolved = path.resolve()
    allowed_roots = (
        (PROJECT_ROOT / "execution/freqtrade/user_data/runtime_strategies").resolve(),
        (PROJECT_ROOT / "execution/freqtrade/user_data/runtime_params").resolve(),
        BACKTEST_RESULT_DIR.resolve(),
    )
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def _pause_freqtrade_service() -> dict[str, Any]:
    if not COMPOSE_FILE.exists():
        return {"ok": False, "skipped": True, "reason": f"compose file not found: {COMPOSE_FILE}"}
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "stop", "freqtrade"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "skipped": True, "reason": "docker command not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "skipped": False, "reason": "docker compose stop freqtrade timed out"}
    return {
        "ok": result.returncode == 0,
        "skipped": False,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
