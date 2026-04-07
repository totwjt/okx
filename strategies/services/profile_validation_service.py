import json
import subprocess
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
        "max_drawdown_account": max_drawdown,
        "stake_currency": metrics.get("stake_currency", "USDT"),
    }


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

    gate = {
        "min_trades": min_trades,
        "min_profit": min_profit,
        "min_profit_factor": min_profit_factor,
        "max_drawdown": max_drawdown,
    }
    passed = (
        metrics["total_trades"] >= min_trades
        and metrics["profit_total"] >= min_profit
        and metrics["profit_factor"] >= min_profit_factor
        and metrics["max_drawdown_account"] <= max_drawdown
    )

    return {
        "profile_name": profile_name,
        "timerange": timerange,
        "backtest_zip": str(latest_zip),
        "metrics": metrics,
        "gate": gate,
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
