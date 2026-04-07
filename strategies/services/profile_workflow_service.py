import sys
from pathlib import Path

from services.profile_service import (
    build_profile_from_hyperopt,
    create_profile_from_source,
    get_active_profile_name,
    list_profile_names,
    load_hyperopt_params,
    load_profile,
    save_profile,
    set_active_profile,
    update_profile_status,
)
from services.profile_validation_service import apply_validation_result, run_profile_validation
from services.runtime_service import strategy_class_name, sync_runtime_profile
from services.spec_service import apply_profile_overrides, build_protections, get_config_path, get_cost_model, get_timeranges


def list_profiles(name: str, spec: dict) -> tuple[str, list[dict]]:
    active = get_active_profile_name(name, spec)
    profiles = []
    for profile_name in list_profile_names(name):
        profile = load_profile(name, spec, profile_name)
        profiles.append(
            {
                "name": profile_name,
                "status": profile.get("status", "draft"),
                "source": profile.get("source", "-"),
                "active": profile_name == active,
            }
        )
    return active, profiles


def create_profile(name: str, spec: dict, profile_name: str, from_profile_name: str) -> Path:
    return create_profile_from_source(name, spec, profile_name, from_profile_name)


def activate_profile(name: str, spec: dict, profile_name: str) -> Path:
    profile = load_profile(name, spec, profile_name)
    set_active_profile(name, spec, profile_name)
    return sync_runtime_profile(name, apply_profile_overrides(spec, profile), profile)


def promote_profile(name: str, spec: dict, profile_name: str, to_status: str) -> tuple[dict, bool, Path | None]:
    profile, activated = update_profile_status(name, spec, profile_name, to_status)
    runtime_json = None
    if activated:
        runtime_json = sync_runtime_profile(name, apply_profile_overrides(spec, profile), profile)
    return profile, activated, runtime_json


def import_hyperopt_profile(name: str, config_path: Path, profile_name: str, hyperopt_filename: str) -> Path:
    params = load_hyperopt_params(config_path, hyperopt_filename)
    profile = build_profile_from_hyperopt(name, profile_name, hyperopt_filename, params)
    return save_profile(name, profile)


def validate_profile(
    *,
    name: str,
    spec: dict,
    profile_name: str | None,
    ensure_generated_strategy,
    profile_bt_result_dir: Path,
    timerange_override: str | None,
    min_trades: int,
    min_profit: float,
    min_profit_factor: float,
    max_drawdown: float,
    promote_on_pass: bool,
) -> tuple[dict, bool]:
    profile = load_profile(name, spec, profile_name)
    effective_spec = apply_profile_overrides(spec, profile)
    ensure_generated_strategy(name, effective_spec)
    sync_runtime_profile(name, effective_spec, profile)

    timeranges = get_timeranges(effective_spec)
    timerange = timerange_override or timeranges["validation"]
    config_path = get_config_path(effective_spec)
    cost_model = get_cost_model(effective_spec)

    try:
        validation_result = run_profile_validation(
            strategy_name=strategy_class_name(name),
            profile_name=profile["profile_name"],
            timerange=timerange,
            config_path=config_path,
            backtest_result_dir=profile_bt_result_dir,
            fee=cost_model.get("fee"),
            enable_protections=bool(build_protections(effective_spec)),
            min_trades=min_trades,
            min_profit=min_profit,
            min_profit_factor=min_profit_factor,
            max_drawdown=max_drawdown,
        )
    except RuntimeError as exc:
        print(f"错误: {exc}")
        sys.exit(1)

    promoted = apply_validation_result(profile, validation_result, promote_on_pass)
    save_profile(name, profile)
    return validation_result, promoted
