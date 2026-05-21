from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[4]
EXPECTED_REGISTRY_TABLES = (
    "strategy_specs",
    "strategy_profiles",
    "strategy_promotion_events",
    "strategy_validation_results",
    "strategy_runtime_artifacts",
)
COMPOSE_FILE = PROJECT_ROOT / "execution/freqtrade/docker-compose.yml"
FREQTRADE_CONFIG = PROJECT_ROOT / "execution/freqtrade/user_data/config.json"
FREQTRADE_API_URL = os.getenv("FREQTRADE_API_URL", "http://127.0.0.1:8080")


def _load_strategy_services() -> Any:
    import sys

    strategy_dir = PROJECT_ROOT / "strategies"
    if str(strategy_dir) not in sys.path:
        sys.path.insert(0, str(strategy_dir))

    from services import db_service, runtime_service

    return db_service, runtime_service


def _redact_database_url(url: str) -> str:
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    userinfo, host = parts.netloc.rsplit("@", 1)
    user = userinfo.split(":", 1)[0]
    return urlunsplit((parts.scheme, f"{user}:***@{host}", parts.path, parts.query, parts.fragment))


def _count_registry_tables(conn: Any) -> dict[str, Any]:
    table_counts: dict[str, int] = {}
    missing_tables: list[str] = []
    with conn.cursor() as cur:
        for table_name in EXPECTED_REGISTRY_TABLES:
            cur.execute("select to_regclass(%s) as table_name", (f"public.{table_name}",))
            exists = cur.fetchone()["table_name"] is not None
            if not exists:
                missing_tables.append(table_name)
                continue
            cur.execute(f"select count(*)::int as count from {table_name}")
            table_counts[table_name] = int(cur.fetchone()["count"])
    return {
        "ok": not missing_tables,
        "table_counts": table_counts,
        "missing_tables": missing_tables,
    }


def _run_command(args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _check_docker() -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "cli_available": False,
        "daemon_available": False,
        "compose_file": str(COMPOSE_FILE),
        "compose_file_exists": COMPOSE_FILE.exists(),
    }

    try:
        version = _run_command(["docker", "--version"])
        result["cli_available"] = version.returncode == 0
        if version.stdout:
            result["cli_version"] = version.stdout.strip()
        if version.stderr:
            result["cli_error"] = version.stderr.strip()
    except FileNotFoundError:
        result["error"] = "docker command not found"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    if not result["cli_available"]:
        return result

    daemon = _run_command(["docker", "info", "--format", "{{.ServerVersion}}"])
    result["daemon_available"] = daemon.returncode == 0
    if daemon.stdout:
        result["daemon_version"] = daemon.stdout.strip()
    if daemon.stderr:
        result["daemon_error"] = daemon.stderr.strip()

    result["ok"] = bool(result["cli_available"] and result["daemon_available"])
    return result


def _check_freqtrade() -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "service": "freqtrade",
        "config_path": str(FREQTRADE_CONFIG),
        "config_exists": FREQTRADE_CONFIG.exists(),
        "api_url": FREQTRADE_API_URL,
    }

    if not COMPOSE_FILE.exists():
        result["compose_error"] = f"compose file not found: {COMPOSE_FILE}"
        return result

    compose = _run_command(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "freqtrade", "--format", "json"]
    )
    result["compose_available"] = compose.returncode == 0
    if compose.stdout:
        result["compose_status_raw"] = compose.stdout.strip()
    if compose.stderr:
        result["compose_error"] = compose.stderr.strip()
    result["ok"] = bool(result["config_exists"] and result["compose_available"])
    return result


def run_system_check() -> dict[str, Any]:
    db_service, runtime_service = _load_strategy_services()

    checks: dict[str, Any] = {
        "postgresql": {"ok": False},
        "registry": {"ok": False},
        "runtime": {"ok": False},
        "docker": {"ok": False},
        "freqtrade": {"ok": False},
    }

    try:
        raw_database_url = db_service.database_url()
        checks["postgresql"]["database"] = db_service.database_name(raw_database_url)
        checks["postgresql"]["database_url"] = _redact_database_url(raw_database_url)
        with db_service.connect(raw_database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("select version() as version")
                version = cur.fetchone()["version"]
            checks["postgresql"]["ok"] = True
            checks["postgresql"]["version"] = version.split(" on ", 1)[0]
            checks["registry"] = _count_registry_tables(conn)
    except Exception as exc:
        checks["postgresql"]["error"] = str(exc)
        checks["registry"]["error"] = "skipped because PostgreSQL check failed"

    runtime_strategy_dir = runtime_service.RUNTIME_STRATEGY_DIR
    checks["runtime"] = {
        "ok": runtime_strategy_dir.exists() and runtime_strategy_dir.is_dir(),
        "path": str(runtime_strategy_dir),
        "exists": runtime_strategy_dir.exists(),
        "is_dir": runtime_strategy_dir.is_dir(),
        "writable": os.access(runtime_strategy_dir, os.W_OK),
    }
    if checks["runtime"]["ok"]:
        checks["runtime"]["artifact_count"] = len(
            [
                path
                for path in runtime_strategy_dir.iterdir()
                if path.is_file() and path.suffix in {".py", ".json"}
            ]
        )

    checks["docker"] = _check_docker()
    checks["freqtrade"] = _check_freqtrade()

    core_checks = ("postgresql", "registry", "runtime")
    operations_checks = ("docker", "freqtrade")
    return {
        "ok": all(checks[name].get("ok") for name in core_checks),
        "operations_ready": all(checks[name].get("ok") for name in operations_checks),
        "project_root": str(PROJECT_ROOT),
        "web_root": str(PROJECT_ROOT / "web"),
        "checks": checks,
    }
