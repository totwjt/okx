import json
import subprocess
from datetime import datetime
from pathlib import Path


def read_backtest_summary(zip_path: Path, strategy_name: str) -> dict:
    import zipfile

    with zipfile.ZipFile(zip_path) as z:
        json_member = next(
            (
                n for n in z.namelist()
                if n.endswith(".json") and "_config" not in n and "_signals" not in n and "_market_change" not in n
            ),
            None,
        )
        if not json_member:
            raise RuntimeError(f"Backtest zip missing result json: {zip_path}")
        payload = json.loads(z.read(json_member).decode("utf-8"))

    strategy_section = payload.get("strategy")
    if isinstance(strategy_section, dict):
        if strategy_name in strategy_section:
            return strategy_section[strategy_name]
        if len(strategy_section) == 1:
            return next(iter(strategy_section.values()))

    raise RuntimeError(f"Strategy metrics not found in backtest result: {zip_path}")


def latest_created_backtest_zip(before: set[str], result_dir: Path) -> Path:
    candidates = [p for p in result_dir.glob("*.zip") if p.name not in before]
    if not candidates:
        raise RuntimeError("未找到新的回测结果文件")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def normalize_backtest_metrics(metrics: dict) -> dict:
    total_trades = int(metrics.get("total_trades", 0) or 0)
    profit_total = float(metrics.get("profit_total", metrics.get("profit_total_ratio", 0)) or 0)
    profit_total_abs = float(metrics.get("profit_total_abs", 0) or 0)
    profit_factor = float(metrics.get("profit_factor", 0) or 0)
    wins = int(metrics.get("wins", metrics.get("win_trades", 0)) or 0)
    losses = int(metrics.get("losses", metrics.get("lose_trades", 0)) or 0)
    draws = int(metrics.get("draws", metrics.get("draw_trades", 0)) or 0)
    winrate = float(metrics.get("winrate", 0) or 0)
    avg_profit = float(metrics.get("profit_mean", metrics.get("avg_profit", 0)) or 0)
    expectancy = float(metrics.get("expectancy_ratio", metrics.get("expectancy", 0)) or 0)

    drawdown_candidates = [
        metrics.get("max_drawdown_account"),
        metrics.get("max_drawdown"),
        metrics.get("absolute_drawdown"),
    ]
    max_drawdown = 0.0
    for value in drawdown_candidates:
        if value is not None:
            max_drawdown = float(value)
            break

    return {
        "total_trades": total_trades,
        "profit_total": profit_total,
        "profit_total_abs": profit_total_abs,
        "profit_factor": profit_factor,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "winrate": winrate,
        "avg_profit": avg_profit,
        "expectancy_ratio": expectancy,
        "max_drawdown_account": max_drawdown,
        "stake_currency": metrics.get("stake_currency", "USDT"),
    }


def timerange_days(timerange: str) -> int | None:
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


def run_profile_validation(
    *,
    strategy_name: str,
    profile_name: str,
    timerange: str,
    config_path: str,
    backtest_result_dir: Path,
    fee: float | None,
    enable_protections: bool,
    min_trades: int,
    min_profit: float,
    min_profit_factor: float,
    max_drawdown: float,
    min_winrate: float,
    min_avg_profit: float,
    min_trades_per_day: float,
) -> dict:
    backtest_result_dir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in backtest_result_dir.glob("*.zip")}

    cmd = [
        "freqtrade",
        "backtesting",
        "-c",
        config_path,
        "-s",
        strategy_name,
        "--timerange",
        timerange,
        "--export",
        "trades",
        "--backtest-directory",
        str(backtest_result_dir),
    ]
    if fee is not None:
        cmd.extend(["--fee", str(fee)])
    if enable_protections:
        cmd.append("--enable-protections")

    subprocess.run(cmd, check=True)

    latest_zip = latest_created_backtest_zip(before, backtest_result_dir)
    metrics = normalize_backtest_metrics(read_backtest_summary(latest_zip, strategy_name))
    validation_days = timerange_days(timerange)
    trades_per_day = None
    if validation_days:
        trades_per_day = metrics["total_trades"] / validation_days

    gate = {
        "min_trades": min_trades,
        "min_profit": min_profit,
        "min_profit_factor": min_profit_factor,
        "max_drawdown": max_drawdown,
        "min_winrate": min_winrate,
        "min_avg_profit": min_avg_profit,
        "min_trades_per_day": min_trades_per_day,
    }
    failed_checks: list[str] = []
    warnings: list[str] = []

    if metrics["total_trades"] < min_trades:
        failed_checks.append(
            f"total_trades={metrics['total_trades']} < min_trades={min_trades}"
        )
    if metrics["profit_total"] < min_profit:
        failed_checks.append(
            f"profit_total={metrics['profit_total']:.6f} < min_profit={min_profit:.6f}"
        )
    if metrics["profit_factor"] < min_profit_factor:
        failed_checks.append(
            f"profit_factor={metrics['profit_factor']:.4f} < min_profit_factor={min_profit_factor:.4f}"
        )
    if metrics["max_drawdown_account"] > max_drawdown:
        failed_checks.append(
            f"max_drawdown_account={metrics['max_drawdown_account']:.4f} > max_drawdown={max_drawdown:.4f}"
        )
    if metrics["winrate"] < min_winrate:
        failed_checks.append(
            f"winrate={metrics['winrate']:.4f} < min_winrate={min_winrate:.4f}"
        )
    if metrics["avg_profit"] < min_avg_profit:
        failed_checks.append(
            f"avg_profit={metrics['avg_profit']:.6f} < min_avg_profit={min_avg_profit:.6f}"
        )
    if trades_per_day is not None and trades_per_day < min_trades_per_day:
        failed_checks.append(
            f"trades_per_day={trades_per_day:.4f} < min_trades_per_day={min_trades_per_day:.4f}"
        )

    if metrics["total_trades"] == 0:
        warnings.append("No trades were produced in validation; this is only a smoke pass, not strategy evidence.")
    if validation_days is None:
        warnings.append(f"Unable to parse validation timerange for cadence checks: {timerange}")

    passed = not failed_checks

    return {
        "profile_name": profile_name,
        "timerange": timerange,
        "backtest_zip": str(latest_zip),
        "metrics": metrics,
        "validation_days": validation_days,
        "trades_per_day": trades_per_day,
        "gate": gate,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "passed": passed,
    }


def apply_validation_result(profile: dict, validation_result: dict, promote_on_pass: bool) -> bool:
    profile.setdefault("validation", {})
    profile["validation"]["last_result"] = validation_result
    promoted = False
    if validation_result["passed"] and promote_on_pass:
        profile["status"] = "validated"
        promoted = True
    return promoted
