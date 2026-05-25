from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json

from app.services.paper_service import _safe_api_get
from app.services.runtime_alignment_service import runtime_alignment
from app.services.system_check import _load_strategy_services


PAPER_RUN_SCHEMA_SQL = """
create table if not exists web_paper_runs (
  id bigserial primary key,
  run_name text not null,
  strategy_slug text not null,
  profile_name text not null,
  artifact_hash text,
  config_hash text,
  dry_run boolean not null default true,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  start_balance numeric,
  current_balance numeric,
  natural_closed_trades int not null default 0,
  force_trades int not null default 0,
  pnl numeric,
  max_drawdown numeric,
  status text not null default 'collecting_samples',
  review_conclusion text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint web_paper_runs_status_check
    check (status in ('collecting_samples', 'ready_for_review', 'review_failed', 'review_passed', 'stopped'))
);

create index if not exists web_paper_runs_current_idx
  on web_paper_runs(strategy_slug, profile_name, started_at desc);
"""


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def init_paper_run_schema() -> None:
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(PAPER_RUN_SCHEMA_SQL)


def create_paper_run(
    strategy_slug: str,
    profile_name: str,
    run_name: str | None = None,
    start_balance: float | None = None,
) -> dict[str, Any]:
    init_paper_run_schema()
    snapshot = _paper_snapshot(strategy_slug, profile_name)
    resolved_start = start_balance if start_balance is not None else snapshot.get("current_balance")
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into web_paper_runs(
                  run_name, strategy_slug, profile_name, artifact_hash, config_hash,
                  dry_run, start_balance, current_balance, natural_closed_trades,
                  force_trades, pnl, max_drawdown, status, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    run_name or f"{strategy_slug}/{profile_name} paper",
                    strategy_slug,
                    profile_name,
                    snapshot.get("artifact_hash"),
                    snapshot.get("config_hash"),
                    bool(snapshot.get("dry_run", True)),
                    resolved_start,
                    snapshot.get("current_balance"),
                    snapshot["natural_closed_trades"],
                    snapshot["force_trades"],
                    _pnl(resolved_start, snapshot.get("current_balance")),
                    snapshot.get("max_drawdown"),
                    _sample_status(snapshot["natural_closed_trades"]),
                    Json(snapshot),
                ),
            )
            return dict(cur.fetchone())


def current_paper_run(strategy_slug: str | None = None, profile_name: str | None = None) -> dict[str, Any] | None:
    init_paper_run_schema()
    db_service = _db_service()
    filters = ["status in ('collecting_samples', 'ready_for_review', 'review_failed', 'review_passed')"]
    values: list[Any] = []
    if strategy_slug:
        filters.append("strategy_slug = %s")
        values.append(strategy_slug)
    if profile_name:
        filters.append("profile_name = %s")
        values.append(profile_name)
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select *
                from web_paper_runs
                where {' and '.join(filters)}
                order by started_at desc, id desc
                limit 1
                """,
                values,
            )
            row = cur.fetchone()
    if not row:
        return None
    return refresh_paper_run(int(row["id"]))


def refresh_paper_run(run_id: int) -> dict[str, Any]:
    init_paper_run_schema()
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from web_paper_runs where id = %s", (run_id,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"paper run not found: {run_id}")
            run = dict(row)
            snapshot = _paper_snapshot(run["strategy_slug"], run["profile_name"])
            current_balance = snapshot.get("current_balance")
            status = run["status"]
            if status in {"collecting_samples", "ready_for_review"}:
                status = _sample_status(snapshot["natural_closed_trades"])
            cur.execute(
                """
                update web_paper_runs
                set artifact_hash = %s,
                    config_hash = %s,
                    dry_run = %s,
                    current_balance = %s,
                    natural_closed_trades = %s,
                    force_trades = %s,
                    pnl = %s,
                    max_drawdown = %s,
                    status = %s,
                    metadata = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (
                    snapshot.get("artifact_hash"),
                    snapshot.get("config_hash"),
                    bool(snapshot.get("dry_run", True)),
                    current_balance,
                    snapshot["natural_closed_trades"],
                    snapshot["force_trades"],
                    _pnl(run.get("start_balance"), current_balance),
                    snapshot.get("max_drawdown"),
                    status,
                    Json(snapshot),
                    run_id,
                ),
            )
            return dict(cur.fetchone())


def review_paper_run(run_id: int, passed: bool, conclusion: str) -> dict[str, Any]:
    if not conclusion.strip():
        raise RuntimeError("review conclusion is required")
    init_paper_run_schema()
    status = "review_passed" if passed else "review_failed"
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update web_paper_runs
                set status = %s,
                    review_conclusion = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (status, conclusion, run_id),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"paper run not found: {run_id}")
            return dict(row)


def stop_paper_run(run_id: int, conclusion: str | None = None) -> dict[str, Any]:
    init_paper_run_schema()
    db_service = _db_service()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update web_paper_runs
                set status = 'stopped',
                    ended_at = %s,
                    review_conclusion = coalesce(%s, review_conclusion),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (datetime.now(timezone.utc), conclusion, run_id),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"paper run not found: {run_id}")
            return dict(row)


def _paper_snapshot(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    alignment = runtime_alignment(strategy_slug, profile_name)
    balance = _safe_api_get("balance")
    profit = _safe_api_get("profit")
    trades_payload = _safe_api_get("trades?limit=200")

    trades = []
    if trades_payload.get("ok") and isinstance(trades_payload.get("data"), dict):
        trades = trades_payload["data"].get("trades", []) or []
    closed = [trade for trade in trades if not trade.get("is_open")]
    force = [trade for trade in closed if _is_force_trade(trade)]
    natural = [trade for trade in closed if not _is_force_trade(trade)]

    balance_data = balance.get("data") if balance.get("ok") and isinstance(balance.get("data"), dict) else {}
    profit_data = profit.get("data") if profit.get("ok") and isinstance(profit.get("data"), dict) else {}
    current_balance = _as_float(balance_data.get("total_bot") or balance_data.get("total"), None)
    latest_artifact_hash = None
    artifacts = alignment.get("sources", {}).get("runtime_json") or {}
    if artifacts.get("artifact_hash"):
        latest_artifact_hash = artifacts["artifact_hash"]

    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "artifact_hash": latest_artifact_hash,
        "config_hash": (alignment.get("sources", {}).get("config") or {}).get("config_hash"),
        "dry_run": (alignment.get("sources", {}).get("config") or {}).get("dry_run"),
        "current_balance": current_balance,
        "natural_closed_trades": len(natural),
        "force_trades": len(force),
        "pnl_abs": _as_float(profit_data.get("profit_closed_coin"), None),
        "max_drawdown": _as_float(profit_data.get("max_drawdown"), None),
        "alignment_status": alignment.get("status"),
        "api": {
            "balance_ok": balance.get("ok", False),
            "profit_ok": profit.get("ok", False),
            "trades_ok": trades_payload.get("ok", False),
            "errors": {
                "balance": balance.get("error"),
                "profit": profit.get("error"),
                "trades": trades_payload.get("error"),
            },
        },
        "review_signal": _sample_status(len(natural)).upper()
        if len(natural) >= 10
        else "COLLECT_MORE_SAMPLES",
    }


def _sample_status(natural_closed_trades: int) -> str:
    return "ready_for_review" if natural_closed_trades >= 10 else "collecting_samples"


def _is_force_trade(trade: dict[str, Any]) -> bool:
    text = " ".join(str(trade.get(key) or "") for key in ("enter_tag", "exit_reason")).lower()
    return "force" in text or "forced" in text


def _as_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _pnl(start_balance: Any, current_balance: Any) -> float | None:
    start = _as_float(start_balance, None)
    current = _as_float(current_balance, None)
    if start is None or current is None:
        return None
    return current - start
