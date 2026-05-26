from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from psycopg2.extras import Json

from app.services.registry_service import materialize_strategy
from app.services.system_check import COMPOSE_FILE, PROJECT_ROOT, _load_strategy_services


JOB_SCHEMA_SQL = """
create table if not exists web_jobs (
  id bigserial primary key,
  job_type text not null,
  status text not null default 'pending',
  payload jsonb not null default '{}'::jsonb,
  result jsonb,
  error_summary text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint web_jobs_status_check
    check (status in ('pending', 'running', 'success', 'failed'))
);

create index if not exists web_jobs_created_at_idx on web_jobs(created_at desc);
create index if not exists web_jobs_status_idx on web_jobs(status);
"""

BACKTEST_RESULT_DIR = PROJECT_ROOT / "execution/freqtrade/user_data/backtest_results/web_jobs"
CONTAINER_BACKTEST_RESULT_DIR = "/freqtrade/user_data/backtest_results/web_jobs"
CONTAINER_CONFIG_PATH = "/freqtrade/user_data/config.json"
SUPPORTED_JOB_TYPES = {"materialize", "data_ensure", "backtest", "validation", "optimization"}
_SCHEMA_LOCK = Lock()
_SCHEMA_INITIALIZED = False


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def init_job_schema() -> None:
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_INITIALIZED:
            return
        _init_job_schema_unlocked()
        _SCHEMA_INITIALIZED = True


def _init_job_schema_unlocked() -> None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(JOB_SCHEMA_SQL)


def create_job(job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    init_job_schema()
    normalized_payload = payload or {}
    if job_type in {"backtest", "validation"} and not normalized_payload.get("force"):
        existing = _find_existing_execution(job_type, normalized_payload)
        if existing:
            existing["deduped"] = True
            existing["dedupe_reason"] = "same strategy/profile/phase/timerange already has a non-failed job"
            return existing
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into web_jobs(job_type, payload)
                values (%s, %s)
                returning *
                """,
                (job_type, Json(normalized_payload)),
            )
            return dict(cur.fetchone())


def _find_existing_execution(job_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    strategy_slug = str(payload.get("strategy_slug") or "").strip()
    profile_name = str(payload.get("profile_name") or "").strip()
    phase = "validation" if job_type == "validation" else str(payload.get("phase") or "validation").strip()
    timerange = str(payload.get("timerange") or "").strip()
    max_repeats = int(payload.get("max_repeats") or 1)
    if not strategy_slug or max_repeats <= 0:
        return None

    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            if timerange:
                cur.execute(
                    """
                    select *
                    from web_jobs
                    where job_type = %s
                      and status in ('pending', 'running', 'success')
                      and payload->>'strategy_slug' = %s
                      and coalesce(payload->>'profile_name', '') = %s
                      and coalesce(payload->>'phase', 'validation') = %s
                      and coalesce(payload->>'timerange', '') = %s
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (job_type, strategy_slug, profile_name, phase, timerange, max_repeats),
                )
            else:
                cur.execute(
                    """
                    select *
                    from web_jobs
                    where job_type = %s
                      and status in ('pending', 'running', 'success')
                      and payload->>'strategy_slug' = %s
                      and coalesce(payload->>'profile_name', '') = %s
                      and coalesce(payload->>'phase', 'validation') = %s
                      and coalesce(payload->>'timerange', '') = ''
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (job_type, strategy_slug, profile_name, phase, max_repeats),
                )
            rows = list(cur.fetchall())
            if len(rows) >= max_repeats:
                return dict(rows[0])
    return None


def start_job_process(job_id: int) -> None:
    log_path = PROJECT_ROOT / "output/web_jobs.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "app.job_worker",
                str(job_id),
            ],
            cwd=PROJECT_ROOT,
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(PROJECT_ROOT / "web/backend"),
            },
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )


def _update_job(job_id: int, status: str, **fields: Any) -> dict[str, Any]:
    init_job_schema()
    db_service = _db_service()
    assignments = ["status = %s", "updated_at = now()"]
    values: list[Any] = [status]
    for key, value in fields.items():
        assignments.append(f"{key} = %s")
        if key in {"payload", "result"} and value is not None:
            values.append(Json(value))
        else:
            values.append(value)
    values.append(job_id)
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                update web_jobs
                set {", ".join(assignments)}
                where id = %s
                returning *
                """,
                values,
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"job not found: {job_id}")
            return dict(row)


def mark_job_running(job_id: int) -> dict[str, Any]:
    return _update_job(job_id, "running", started_at=datetime.now(timezone.utc))


def mark_job_success(job_id: int, result: dict[str, Any]) -> dict[str, Any]:
    return _update_job(
        job_id,
        "success",
        result=result,
        error_summary=None,
        finished_at=datetime.now(timezone.utc),
    )


def mark_job_failed(job_id: int, error_summary: str) -> dict[str, Any]:
    return _update_job(
        job_id,
        "failed",
        error_summary=error_summary[:1000],
        finished_at=datetime.now(timezone.utc),
    )


def list_jobs(limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
    init_job_schema()
    db_service = _db_service()
    normalized_limit = max(1, min(limit, 500))
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    """
                    select *
                    from web_jobs
                    where status = %s
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (status, normalized_limit),
                )
            else:
                cur.execute(
                    """
                    select *
                    from web_jobs
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (normalized_limit,),
                )
            return list(cur.fetchall())


def get_job(job_id: int) -> dict[str, Any] | None:
    init_job_schema()
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from web_jobs where id = %s", (job_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_backtest_results(limit: int = 100) -> list[dict[str, Any]]:
    init_job_schema()
    db_service = _db_service()
    normalized_limit = max(1, min(limit, 500))
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select *
                from web_jobs
                where job_type = 'backtest'
                order by created_at desc, id desc
                limit %s
                """,
                (normalized_limit,),
            )
            return list(cur.fetchall())


def list_validation_results(limit: int = 100) -> list[dict[str, Any]]:
    init_job_schema()
    db_service = _db_service()
    normalized_limit = max(1, min(limit, 500))
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select *
                from web_jobs
                where job_type = 'validation'
                order by created_at desc, id desc
                limit %s
                """,
                (normalized_limit,),
            )
            return list(cur.fetchall())


def promote_profile_with_gate(
    strategy_slug: str,
    profile_name: str,
    to_status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    db_service = _db_service()
    db_service.init_schema()
    protected_statuses = {"validated", "paper_active", "live_candidate", "live_active"}
    if to_status in protected_statuses:
        latest = latest_validation_result(strategy_slug, profile_name)
        if not latest or not latest["passed"]:
            raise RuntimeError(f"latest validation is not passed: {strategy_slug}/{profile_name}")
    db_service.promote_profile(strategy_slug, profile_name, to_status, reason)
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "to_status": to_status,
        "promoted": True,
    }


def latest_validation_result(strategy_slug: str, profile_name: str) -> dict[str, Any] | None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select *
                from strategy_validation_results
                where strategy_slug = %s and profile_name = %s
                order by created_at desc, id desc
                limit 1
                """,
                (strategy_slug, profile_name),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def run_job(job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    job = create_job(job_type, payload)
    return execute_job(int(job["id"]))


def execute_job(job_id: int) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise RuntimeError(f"job not found: {job_id}")
    mark_job_running(job_id)
    try:
        result = _execute_job(job_id, str(job["job_type"]), dict(job["payload"] or {}))
    except Exception as exc:
        return mark_job_failed(job_id, str(exc))
    return mark_job_success(job_id, result)


def _execute_job(job_id: int, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if job_type not in SUPPORTED_JOB_TYPES:
        raise RuntimeError(f"unsupported job type: {job_type}")
    if job_type == "materialize":
        strategy_slug = str(payload.get("strategy_slug") or "").strip()
        if not strategy_slug:
            raise RuntimeError("strategy_slug is required")
        profile_name = payload.get("profile_name")
        if profile_name is not None:
            profile_name = str(profile_name).strip() or None
        return materialize_strategy(strategy_slug, profile_name)
    if job_type == "data_ensure":
        return _run_data_ensure_job(payload)
    if job_type == "backtest":
        return _run_backtest_job(payload, job_id=job_id)
    if job_type == "validation":
        return _run_validation_job(payload, job_id=job_id)
    if job_type == "optimization":
        from app.services.optimization_service import auto_tune_strategy

        strategy_slug = str(payload.get("strategy_slug") or "").strip()
        if not strategy_slug:
            raise RuntimeError("strategy_slug is required")
        baseline_profile = payload.get("baseline_profile")
        if baseline_profile is not None:
            baseline_profile = str(baseline_profile).strip() or None
        return auto_tune_strategy(
            strategy_slug,
            baseline_profile,
            candidate_count=int(payload.get("candidate_count") or 3),
            run_backtests=bool(payload.get("run_backtests", True)),
        )
    raise RuntimeError(f"unsupported job type: {job_type}")


def _strategy_service_modules() -> tuple[Any, Any, Any, Any]:
    import sys

    strategy_dir = PROJECT_ROOT / "strategies"
    if str(strategy_dir) not in sys.path:
        sys.path.insert(0, str(strategy_dir))

    from services import profile_validation_service, runtime_service, spec_service

    return profile_validation_service, runtime_service, spec_service, _db_service()


def _run_freqtrade_compose(args: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "run",
        "--rm",
        "freqtrade",
        *args,
    ]
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )


def _command_error_tail(completed: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    lines = output.strip().splitlines()
    return "\n".join(lines[-30:]) or f"command failed with code {completed.returncode}"


def _resolve_strategy_bundle(payload: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    _profile_validation_service, _runtime_service, spec_service, db_service = _strategy_service_modules()
    strategy_slug = str(payload.get("strategy_slug") or "").strip()
    if not strategy_slug:
        raise RuntimeError("strategy_slug is required")
    profile_name = payload.get("profile_name")
    if profile_name is not None:
        profile_name = str(profile_name).strip() or None
    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    effective_spec = spec_service.apply_profile_overrides(spec, profile)
    return strategy_slug, effective_spec, profile, spec_service


def _timerange_with_closed_end(timerange: str) -> str:
    if "-" not in timerange:
        return timerange
    start, end = timerange.split("-", 1)
    if end:
        return timerange
    return f"{start}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def _default_data_timerange(spec: dict[str, Any], spec_service: Any) -> str:
    timeranges = spec_service.get_timeranges(spec)
    start_candidates = []
    end_candidates = []
    for value in timeranges.values():
        value = _timerange_with_closed_end(str(value or "").strip())
        if "-" not in value:
            continue
        start, end = value.split("-", 1)
        if start:
            start_candidates.append(start)
        if end:
            end_candidates.append(end)
    if not start_candidates:
        raise RuntimeError("unable to infer data timerange from strategy spec")
    start = min(start_candidates)
    end = max(end_candidates) if end_candidates else datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{start}-{end}"


def _run_data_ensure_job(payload: dict[str, Any]) -> dict[str, Any]:
    strategy_slug, effective_spec, profile, spec_service = _resolve_strategy_bundle(payload)
    market = effective_spec.get("market") or {}
    pair = str(payload.get("pair") or market.get("pair") or "").strip()
    if not pair:
        raise RuntimeError("pair is required; set payload.pair or spec.market.pair")

    timeframe = str(payload.get("timeframe") or effective_spec.get("timeframe") or "15m").strip()
    trading_mode = str(payload.get("trading_mode") or effective_spec.get("trading_mode") or "futures").strip()
    timerange = str(payload.get("timerange") or _default_data_timerange(effective_spec, spec_service)).strip()
    timerange = _timerange_with_closed_end(timerange)

    cmd_args = [
        "download-data",
        "-c",
        CONTAINER_CONFIG_PATH,
        "--trading-mode",
        trading_mode,
        "--timerange",
        timerange,
        "-t",
        timeframe,
        "-p",
        pair,
    ]
    if payload.get("erase"):
        cmd_args.append("--erase")
    if payload.get("no_parallel_download"):
        cmd_args.append("--no-parallel-download")
    candle_types = payload.get("candle_types")
    if isinstance(candle_types, list) and candle_types:
        cmd_args.append("--candle-types")
        cmd_args.extend(str(item) for item in candle_types)

    completed = _run_freqtrade_compose(
        cmd_args,
        timeout_seconds=int(payload.get("timeout_seconds") or 1800),
    )
    if completed.returncode != 0:
        raise RuntimeError(_command_error_tail(completed))

    data_dir = PROJECT_ROOT / "execution/freqtrade/user_data/data/okx"
    files = sorted(str(path) for path in data_dir.glob("**/*") if path.is_file() and pair.replace("/", "_").replace(":", "_") in path.name)
    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile["profile_name"],
        "pair": pair,
        "timeframe": timeframe,
        "trading_mode": trading_mode,
        "timerange": timerange,
        "files": files,
        "stdout_tail": "\n".join((completed.stdout or "").strip().splitlines()[-20:]),
    }


def _run_backtest_job(payload: dict[str, Any], *, job_id: int | None = None) -> dict[str, Any]:
    profile_validation_service, runtime_service, spec_service, db_service = _strategy_service_modules()
    strategy_slug = str(payload.get("strategy_slug") or "").strip()
    if not strategy_slug:
        raise RuntimeError("strategy_slug is required")

    profile_name = payload.get("profile_name")
    if profile_name is not None:
        profile_name = str(profile_name).strip() or None
    phase = str(payload.get("phase") or "validation").strip()
    if phase not in {"train", "validation", "test", "custom"}:
        raise RuntimeError(f"unsupported backtest phase: {phase}")

    spec, profile = db_service.load_strategy_bundle(strategy_slug, profile_name)
    effective_spec = spec_service.apply_profile_overrides(spec, profile)
    timeranges = spec_service.get_timeranges(effective_spec)
    timerange = str(payload.get("timerange") or timeranges.get(phase) or "").strip()
    if not timerange:
        raise RuntimeError("timerange is required")

    materialize_result = materialize_strategy(strategy_slug, profile.get("profile_name"))
    result_dir = BACKTEST_RESULT_DIR / f"job_{job_id}" if job_id is not None else BACKTEST_RESULT_DIR
    container_result_dir = (
        f"{CONTAINER_BACKTEST_RESULT_DIR}/job_{job_id}" if job_id is not None else CONTAINER_BACKTEST_RESULT_DIR
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    before = {path.name for path in result_dir.glob("*.zip")}

    strategy_name = runtime_service.strategy_class_name(strategy_slug)
    config_path = spec_service.get_config_path(effective_spec)
    cost_model = spec_service.get_cost_model(effective_spec)
    enable_protections = bool(spec_service.build_protections(effective_spec))

    cmd = [
        "backtesting",
        "-c",
        config_path,
        "-s",
        strategy_name,
        "--strategy-path",
        "/freqtrade/user_data/runtime_strategies",
        "--timerange",
        timerange,
        "--export",
        "trades",
        "--backtest-directory",
        container_result_dir,
    ]
    if cost_model.get("fee") is not None:
        cmd.extend(["--fee", str(cost_model["fee"])])
    if enable_protections:
        cmd.append("--enable-protections")

    completed = _run_freqtrade_compose(
        cmd,
        timeout_seconds=int(payload.get("timeout_seconds") or 900),
    )
    if completed.returncode != 0:
        raise RuntimeError(_command_error_tail(completed))

    latest_zip = profile_validation_service.latest_created_backtest_zip(before, result_dir)
    raw_metrics = profile_validation_service.read_backtest_summary(latest_zip, strategy_name)
    metrics = profile_validation_service.normalize_backtest_metrics(raw_metrics)

    return {
        "strategy_slug": strategy_slug,
        "strategy_name": strategy_name,
        "profile_name": profile["profile_name"],
        "phase": phase,
        "timerange": timerange,
        "metrics": metrics,
        "backtest_zip": str(latest_zip),
        "backtest_directory": str(result_dir),
        "materialize": materialize_result,
        "command": ["docker", "compose", "-f", str(COMPOSE_FILE), "run", "--rm", "freqtrade", *cmd],
    }


def _run_validation_job(payload: dict[str, Any], *, job_id: int | None = None) -> dict[str, Any]:
    backtest_payload = dict(payload)
    backtest_payload["phase"] = "validation"
    backtest_result = _run_backtest_job(backtest_payload, job_id=job_id)
    metrics = dict(backtest_result["metrics"])
    timerange = str(backtest_result["timerange"])

    validation_days = _timerange_days(timerange)
    trades_per_day = None
    if validation_days:
        trades_per_day = metrics["total_trades"] / validation_days

    gate = {
        "min_trades": int(payload.get("min_trades", 1)),
        "min_profit": float(payload.get("min_profit", 0.0)),
        "min_profit_factor": float(payload.get("min_profit_factor", 1.0)),
        "max_drawdown": float(payload.get("max_drawdown", 0.30)),
        "min_winrate": float(payload.get("min_winrate", 0.0)),
        "min_avg_profit": float(payload.get("min_avg_profit", 0.0)),
        "min_trades_per_day": float(payload.get("min_trades_per_day", 0.0)),
    }
    failed_checks: list[str] = []
    warnings: list[str] = []

    if metrics["total_trades"] < gate["min_trades"]:
        failed_checks.append(f"total_trades={metrics['total_trades']} < min_trades={gate['min_trades']}")
    if metrics["profit_total"] < gate["min_profit"]:
        failed_checks.append(f"profit_total={metrics['profit_total']:.6f} < min_profit={gate['min_profit']:.6f}")
    if metrics["profit_factor"] < gate["min_profit_factor"]:
        failed_checks.append(
            f"profit_factor={metrics['profit_factor']:.4f} < min_profit_factor={gate['min_profit_factor']:.4f}"
        )
    if metrics["max_drawdown_account"] > gate["max_drawdown"]:
        failed_checks.append(
            f"max_drawdown_account={metrics['max_drawdown_account']:.4f} > max_drawdown={gate['max_drawdown']:.4f}"
        )
    if metrics["winrate"] < gate["min_winrate"]:
        failed_checks.append(f"winrate={metrics['winrate']:.4f} < min_winrate={gate['min_winrate']:.4f}")
    if metrics["avg_profit"] < gate["min_avg_profit"]:
        failed_checks.append(
            f"avg_profit={metrics['avg_profit']:.6f} < min_avg_profit={gate['min_avg_profit']:.6f}"
        )
    if trades_per_day is not None and trades_per_day < gate["min_trades_per_day"]:
        failed_checks.append(
            f"trades_per_day={trades_per_day:.4f} < min_trades_per_day={gate['min_trades_per_day']:.4f}"
        )

    if metrics["total_trades"] == 0:
        warnings.append("No trades were produced in validation; this is only a smoke pass, not strategy evidence.")
    if validation_days is None:
        warnings.append(f"Unable to parse validation timerange for cadence checks: {timerange}")

    passed = not failed_checks
    validation_result = {
        **backtest_result,
        "passed": passed,
        "gate": gate,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "validation_days": validation_days,
        "trades_per_day": trades_per_day,
    }
    _record_validation_result(validation_result)
    return validation_result


def _timerange_days(timerange: str) -> int | None:
    if "-" not in timerange:
        return None
    start_text, end_text = timerange.split("-", 1)
    try:
        start = datetime.strptime(start_text, "%Y%m%d")
        end = datetime.strptime(end_text, "%Y%m%d")
    except ValueError:
        return None
    if end < start:
        return None
    return (end - start).days + 1


def _record_validation_result(validation_result: dict[str, Any]) -> None:
    db_service = _db_service()
    db_service.init_schema()
    strategy_slug = validation_result["strategy_slug"]
    profile_name = validation_result["profile_name"]
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into strategy_validation_results(
                  strategy_slug, profile_name, timerange, passed, metrics, gate,
                  warnings, failed_checks, artifact_path
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    strategy_slug,
                    profile_name,
                    validation_result["timerange"],
                    validation_result["passed"],
                    Json(validation_result["metrics"]),
                    Json(validation_result["gate"]),
                    Json(validation_result["warnings"]),
                    Json(validation_result["failed_checks"]),
                    validation_result["backtest_zip"],
                ),
            )
            cur.execute(
                """
                update strategy_profiles
                set validation = jsonb_set(
                    coalesce(validation, '{}'::jsonb),
                    '{last_result}',
                    %s::jsonb,
                    true
                  ),
                  updated_at = now()
                where strategy_slug = %s and profile_name = %s
                """,
                (Json(validation_result), strategy_slug, profile_name),
            )
