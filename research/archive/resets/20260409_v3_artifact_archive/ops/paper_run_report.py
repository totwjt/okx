#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from http.client import RemoteDisconnected
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
USER_DATA_DIR = REPO_ROOT / "execution" / "freqtrade" / "user_data"
DB_PATH = USER_DATA_DIR / "tradesv3.sqlite"
RUN_DIR = USER_DATA_DIR / "paper_runs"
REPORT_DIR = REPO_ROOT / "research" / "reports" / "paper_runs"
DEFAULT_STRATEGY = "MultiLsV3Strategy"
API_BASE = "http://127.0.0.1:8080/api/v1"
API_AUTH = base64.b64encode(b"freqtrade:freqtrade").decode()


@dataclass
class RunMarker:
    run_name: str
    started_at: str
    strategy: str
    active_profile: str
    notes: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def strategy_to_slug(strategy_name: str) -> str:
    if strategy_name.endswith("Strategy"):
        strategy_name = strategy_name[:-8]
    out: list[str] = []
    for i, ch in enumerate(strategy_name):
        if ch.isupper() and i > 0 and (not strategy_name[i - 1].isupper()):
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def parse_active_profile(strategy_name: str) -> str:
    active_profile_path = REPO_ROOT / "strategies" / "profiles" / strategy_to_slug(strategy_name) / "_active.yaml"
    if not active_profile_path.exists():
        return "unknown"
    for line in active_profile_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("active_profile:"):
            return line.split(":", 1)[1].strip() or "unknown"
    return "unknown"


def run_marker_path(run_name: str) -> Path:
    return RUN_DIR / f"{run_name}.json"


def report_path(run_name: str) -> Path:
    return REPORT_DIR / f"{run_name}.md"


def save_marker(marker: RunMarker) -> Path:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    path = run_marker_path(marker.run_name)
    path.write_text(
        json.dumps(marker.__dict__, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_marker(run_name: str) -> RunMarker:
    path = run_marker_path(run_name)
    if not path.exists():
        raise SystemExit(f"paper run marker not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunMarker(**data)


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def maybe_get_api_json(path: str) -> dict | None:
    req = Request(
        f"{API_BASE}/{path}",
        headers={"Authorization": f"Basic {API_AUTH}"},
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, RemoteDisconnected):
        return None


def summarize_run(marker: RunMarker) -> dict:
    conn = connect_db()
    cur = conn.cursor()

    started_at = marker.started_at
    strategy = marker.strategy

    cur.execute(
        """
        select
          count(*) as all_trades,
          sum(case when is_open = 1 then 1 else 0 end) as open_trades,
          sum(case when is_open = 0 then 1 else 0 end) as closed_trades,
          sum(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' then 1 else 0 end) as natural_closed_trades,
          sum(case when is_open = 0 and coalesce(enter_tag, '') = 'force_entry' then 1 else 0 end) as forced_closed_trades,
          sum(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' then coalesce(close_profit_abs, 0) else 0 end) as natural_closed_pnl,
          avg(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' then close_profit_abs end) as natural_avg_pnl_abs,
          avg(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' then close_profit end) as natural_avg_pnl_ratio,
          sum(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' and coalesce(close_profit_abs, 0) > 0 then 1 else 0 end) as natural_wins,
          sum(case when is_open = 0 and coalesce(enter_tag, '') != 'force_entry' and coalesce(close_profit_abs, 0) <= 0 then 1 else 0 end) as natural_losses,
          max(open_date) as last_open_date,
          max(close_date) as last_close_date
        from trades
        where strategy = ?
          and open_date >= ?
        """,
        (strategy, started_at),
    )
    summary = dict(cur.fetchone())

    cur.execute(
        """
        select
          pair,
          count(*) as trades,
          sum(coalesce(close_profit_abs, 0)) as pnl
        from trades
        where strategy = ?
          and open_date >= ?
          and is_open = 0
          and coalesce(enter_tag, '') != 'force_entry'
        group by pair
        order by pnl desc, trades desc
        """,
        (strategy, started_at),
    )
    pair_stats = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        select
          case when is_short = 1 then 'short' else 'long' end as side,
          count(*) as trades,
          sum(coalesce(close_profit_abs, 0)) as pnl
        from trades
        where strategy = ?
          and open_date >= ?
          and is_open = 0
          and coalesce(enter_tag, '') != 'force_entry'
        group by case when is_short = 1 then 'short' else 'long' end
        order by trades desc
        """,
        (strategy, started_at),
    )
    direction_stats = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        select
          coalesce(exit_reason, 'unknown') as exit_reason,
          count(*) as trades,
          sum(coalesce(close_profit_abs, 0)) as pnl
        from trades
        where strategy = ?
          and open_date >= ?
          and is_open = 0
          and coalesce(enter_tag, '') != 'force_entry'
        group by coalesce(exit_reason, 'unknown')
        order by trades desc, pnl desc
        """,
        (strategy, started_at),
    )
    exit_stats = [dict(row) for row in cur.fetchall()]

    cur.execute(
        """
        select
          id, pair, is_short, is_open, enter_tag, exit_reason,
          stake_amount, open_rate, close_rate, close_profit_abs, close_profit,
          open_date, close_date
        from trades
        where strategy = ?
          and open_date >= ?
        order by id desc
        limit 5
        """,
        (strategy, started_at),
    )
    recent_trades = [dict(row) for row in cur.fetchall()]

    natural_closed_trades = summary["natural_closed_trades"] or 0
    natural_wins = summary["natural_wins"] or 0
    winrate = (natural_wins / natural_closed_trades) if natural_closed_trades else 0.0

    api_balance = maybe_get_api_json("balance")
    api_profit = maybe_get_api_json("profit")
    api_status = maybe_get_api_json("status")

    return {
        "marker": marker.__dict__,
        "summary": summary,
        "winrate": winrate,
        "pair_stats": pair_stats,
        "direction_stats": direction_stats,
        "exit_stats": exit_stats,
        "recent_trades": recent_trades,
        "api_balance": api_balance,
        "api_profit": api_profit,
        "api_status": api_status,
    }


def verdict_from_summary(data: dict) -> tuple[str, list[str]]:
    summary = data["summary"]
    natural_closed_trades = summary["natural_closed_trades"] or 0
    natural_closed_pnl = summary["natural_closed_pnl"] or 0.0
    avg_ratio = summary["natural_avg_pnl_ratio"] or 0.0
    winrate = data["winrate"]

    findings: list[str] = []
    if natural_closed_trades < 10:
        findings.append(f"样本不足，当前自然平仓只有 {natural_closed_trades} 笔。")
    if natural_closed_pnl <= 0:
        findings.append(f"自然样本累计 PnL 为 {natural_closed_pnl:.6f} USDT，暂未转正。")
    if natural_closed_trades >= 5 and winrate < 0.45:
        findings.append(f"自然样本胜率只有 {winrate * 100:.2f}%。")
    if natural_closed_trades >= 5 and avg_ratio <= 0:
        findings.append(f"自然样本平均单笔收益为 {avg_ratio * 100:.4f}%。")

    if natural_closed_trades < 10:
        return "COLLECT_MORE_SAMPLES", findings
    if natural_closed_pnl <= 0 or avg_ratio <= 0:
        return "REVIEW_STRATEGY_BEFORE_PROMOTION", findings
    return "READY_FOR_DEEPER_REVIEW", findings


def render_report(data: dict) -> str:
    marker = data["marker"]
    summary = data["summary"]
    api_balance = data["api_balance"]
    api_profit = data["api_profit"]
    api_status = data["api_status"]
    verdict, findings = verdict_from_summary(data)

    natural_closed_trades = summary["natural_closed_trades"] or 0
    natural_closed_pnl = summary["natural_closed_pnl"] or 0.0
    natural_avg_pnl_abs = summary["natural_avg_pnl_abs"] or 0.0
    natural_avg_pnl_ratio = summary["natural_avg_pnl_ratio"] or 0.0
    winrate = data["winrate"]

    lines = [
        f"# Paper Run Report: {marker['run_name']}",
        "",
        "## Run Meta",
        f"- started_at: `{marker['started_at']}`",
        f"- strategy: `{marker['strategy']}`",
        f"- active_profile: `{marker['active_profile']}`",
        f"- notes: {marker['notes'] or '-'}",
        "",
        "## Current Verdict",
        f"- status: `{verdict}`",
    ]
    if findings:
        lines.append("- findings:")
        for item in findings:
            lines.append(f"  - {item}")
    else:
        lines.append("- findings: none")

    lines.extend(
        [
            "",
            "## Strategy Summary Since Start",
            f"- all_trades: {summary['all_trades'] or 0}",
            f"- open_trades: {summary['open_trades'] or 0}",
            f"- closed_trades: {summary['closed_trades'] or 0}",
            f"- natural_closed_trades: {natural_closed_trades}",
            f"- forced_closed_trades: {summary['forced_closed_trades'] or 0}",
            f"- natural_closed_pnl: {natural_closed_pnl:.6f} USDT",
            f"- natural_avg_pnl_abs: {natural_avg_pnl_abs:.6f} USDT",
            f"- natural_avg_pnl_ratio: {natural_avg_pnl_ratio * 100:.4f}%",
            f"- natural_winrate: {winrate * 100:.2f}%",
            f"- last_open_date: {summary['last_open_date'] or '-'}",
            f"- last_close_date: {summary['last_close_date'] or '-'}",
            "",
            "## API Snapshot",
        ]
    )

    if api_balance and api_profit and api_status is not None:
        lines.extend(
            [
                f"- balance_total: {api_balance.get('total', 0):.6f} {api_balance.get('stake', 'USDT')}",
                f"- balance_bot_owned: {api_balance.get('total_bot', 0):.6f} {api_balance.get('stake', 'USDT')}",
                f"- pnl_all: {api_profit.get('profit_all_coin', 0):.6f} {api_balance.get('stake', 'USDT')}",
                f"- pnl_all_percent: {api_profit.get('profit_all_percent', 0):.2f}%",
                f"- closed_trade_count: {api_profit.get('closed_trade_count', 0)}",
                f"- api_open_positions: {len(api_status)}",
            ]
        )
    else:
        lines.append("- api_snapshot: unavailable")

    def add_stat_section(title: str, rows: list[dict], label_key: str) -> None:
        lines.append("")
        lines.append(f"## {title}")
        if not rows:
            lines.append("- none")
            return
        for row in rows:
            lines.append(f"- {row[label_key]}: trades={row['trades']} pnl={(row['pnl'] or 0):.6f} USDT")

    add_stat_section("Pair Breakdown", data["pair_stats"], "pair")
    add_stat_section("Direction Breakdown", data["direction_stats"], "side")
    add_stat_section("Exit Reason Breakdown", data["exit_stats"], "exit_reason")

    lines.extend(["", "## Recent Trades"])
    if not data["recent_trades"]:
        lines.append("- none")
    else:
        for row in data["recent_trades"]:
            side = "short" if row["is_short"] else "long"
            pnl_abs = row["close_profit_abs"]
            pnl_ratio = row["close_profit"]
            pnl_text = "open" if pnl_abs is None else f"{pnl_abs:.6f} USDT ({(pnl_ratio or 0) * 100:.2f}%)"
            lines.append(
                f"- #{row['id']} {row['pair']} {side} open={row['is_open']} open_date={row['open_date']} "
                f"close_date={row['close_date'] or '-'} pnl={pnl_text} exit_reason={row['exit_reason'] or '-'}"
            )

    return "\n".join(lines) + "\n"


def cmd_start(args: argparse.Namespace) -> int:
    active_profile = parse_active_profile(args.strategy)
    marker = RunMarker(
        run_name=args.run_name,
        started_at=now_utc_iso(),
        strategy=args.strategy,
        active_profile=active_profile,
        notes=args.notes or "",
    )
    path = save_marker(marker)
    print(f"paper run started: {path}")
    print(json.dumps(marker.__dict__, ensure_ascii=False, indent=2))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    marker = load_marker(args.run_name)
    data = summarize_run(marker)
    report = render_report(data)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = report_path(args.run_name)
    out_path.write_text(report, encoding="utf-8")
    print(f"paper run report written: {out_path}")
    print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper-run lifecycle helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="create a paper-run marker")
    start.add_argument("run_name", help="paper run name")
    start.add_argument("--strategy", default=DEFAULT_STRATEGY, help="strategy name")
    start.add_argument("--notes", default="", help="operator notes")
    start.set_defaults(func=cmd_start)

    report = subparsers.add_parser("report", help="build a paper-run report")
    report.add_argument("run_name", help="paper run name")
    report.set_defaults(func=cmd_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
