import subprocess
from pathlib import Path

from services.runtime_service import STRATEGY_DIR


def run_backtest_phase(
    *,
    strategy_name: str,
    config_path: str,
    label: str,
    timerange: str,
    fee: float | None,
    risk_model: dict,
    enable_protections: bool,
) -> None:
    print(f"\n[{label}] 回测")
    print(f"  时间范围: {timerange}")
    if fee is not None:
        print(f"  fee: {fee}")
    if risk_model.get("max_open_trades") is not None:
        print(f"  max_open_trades: {risk_model['max_open_trades']}")
    if risk_model.get("max_drawdown_pct") is not None:
        print(f"  max_drawdown_pct: {risk_model['max_drawdown_pct']}")

    cmd = ["freqtrade", "backtesting", "-c", config_path, "-s", strategy_name, "--timerange", timerange]
    if fee is not None:
        cmd.extend(["--fee", str(fee)])
    if enable_protections:
        cmd.append("--enable-protections")
    subprocess.run(cmd, check=True)


def run_backtest(
    *,
    strategy_name: str,
    phase: str,
    timerange: str,
    config_path: str,
    cost_model: dict,
    risk_model: dict,
    enable_protections: bool,
) -> None:
    print(f"运行回测: {strategy_name}")
    print(f"  阶段: {phase}")
    print(f"  时间范围: {timerange}")
    if cost_model.get("fee") is not None:
        print(f"  fee: {cost_model['fee']}")
    if cost_model.get("slippage_bps") is not None:
        print(f"  slippage_bps: {cost_model['slippage_bps']} (当前未自动注入 Freqtrade CLI)")
    if cost_model.get("funding_rate_included") is False:
        print("  funding_rate: 未纳入")
    if risk_model:
        print(
            "  风控边界: "
            f"max_open_trades={risk_model.get('max_open_trades')}, "
            f"max_daily_loss_pct={risk_model.get('max_daily_loss_pct')}, "
            f"max_drawdown_pct={risk_model.get('max_drawdown_pct')}"
        )

    cmd = ["freqtrade", "backtesting", "-c", config_path, "-s", strategy_name, "--timerange", timerange]
    if cost_model.get("fee") is not None:
        cmd.extend(["--fee", str(cost_model["fee"])])
    if enable_protections:
        cmd.append("--enable-protections")
    subprocess.run(cmd, check=True)


def run_hyperopt(
    *,
    strategy_name: str,
    epochs: int,
    timerange: str,
    config_path: str,
    hyperopt_loss: str | None,
    fee: float | None,
    enable_protections: bool,
) -> None:
    cmd = [
        "freqtrade",
        "hyperopt",
        "-c",
        config_path,
        "-s",
        strategy_name,
        "--timerange",
        timerange,
        "--epochs",
        str(epochs),
        "-j",
        "4",
    ]
    if hyperopt_loss:
        cmd.extend(["--hyperopt-loss", hyperopt_loss])
    if fee is not None:
        cmd.extend(["--fee", str(fee)])
    if enable_protections:
        cmd.append("--enable-protections")
    subprocess.run(cmd, check=True)


def runtime_param_snapshot_path(name: str) -> Path:
    return STRATEGY_DIR / f"auto_{name}.json"
