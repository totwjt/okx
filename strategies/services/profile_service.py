import copy
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


PROFILE_ROOT_DIR = Path("/freqtrade/user_data/strategies/profiles")
PROFILE_DEFAULT_NAME = "default"
PARAM_FACTOR_MAP = {
    "ma_period": ("ma", "period"),
    "rsi_period": ("rsi", "period"),
    "rsi_oversold": ("rsi_oversold", "value"),
    "rsi_overbought": ("rsi_overbought", "value"),
}


def profile_dir(name: str) -> Path:
    return PROFILE_ROOT_DIR / name


def profile_path(name: str, profile_name: str) -> Path:
    return profile_dir(name) / f"{profile_name}.yaml"


def active_profile_path(name: str) -> Path:
    return profile_dir(name) / "_active.yaml"


def ensure_profile_dir(name: str) -> Path:
    pdir = profile_dir(name)
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


def extract_default_overrides(spec: dict) -> dict:
    factors = spec.get("factors", {})
    factor_overrides: dict[str, dict] = {}
    for factor_name, field_name in PARAM_FACTOR_MAP.values():
        factor = factors.get(factor_name)
        if not factor:
            continue
        factor_overrides.setdefault(factor_name, {})
        if field_name in factor:
            factor_overrides[factor_name][field_name] = factor[field_name]

    overrides: dict[str, object] = {"factors": factor_overrides, "risk_model": {}}
    for key in [
        "stoploss",
        "minimal_roi",
        "trailing_stop",
        "trailing_stop_positive",
        "trailing_stop_positive_offset",
        "trailing_only_offset_is_reached",
    ]:
        if key in spec:
            overrides[key] = spec[key]
    risk_model = spec.get("risk_model", {})
    if "max_open_trades" in risk_model:
        overrides["risk_model"]["max_open_trades"] = risk_model["max_open_trades"]
    return overrides


def default_profile_payload(name: str, spec: dict, profile_name: str = PROFILE_DEFAULT_NAME) -> dict:
    return {
        "profile_name": profile_name,
        "strategy_name": name,
        "status": "draft",
        "source": "spec_defaults",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overrides": extract_default_overrides(spec),
    }


def ensure_default_profile(name: str, spec: dict) -> None:
    ensure_profile_dir(name)
    dpath = profile_path(name, PROFILE_DEFAULT_NAME)
    if not dpath.exists():
        with open(dpath, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_profile_payload(name, spec), f, allow_unicode=True, sort_keys=False)
    apath = active_profile_path(name)
    if not apath.exists():
        with open(apath, "w", encoding="utf-8") as f:
            yaml.safe_dump({"active_profile": PROFILE_DEFAULT_NAME}, f, allow_unicode=True, sort_keys=False)


def get_active_profile_name(name: str, spec: dict | None = None) -> str:
    if spec is not None:
        ensure_default_profile(name, spec)
    apath = active_profile_path(name)
    if not apath.exists():
        return PROFILE_DEFAULT_NAME
    with open(apath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("active_profile", PROFILE_DEFAULT_NAME)


def load_profile(name: str, spec: dict, profile_name: str | None = None) -> dict:
    ensure_default_profile(name, spec)
    resolved = profile_name or get_active_profile_name(name, spec)
    ppath = profile_path(name, resolved)
    if not ppath.exists():
        print(f"错误: 找不到 profile 文件 {resolved}.yaml")
        sys.exit(1)
    with open(ppath, "r", encoding="utf-8") as f:
        profile = yaml.safe_load(f) or {}
    profile.setdefault("profile_name", resolved)
    profile.setdefault("strategy_name", name)
    profile.setdefault("status", "draft")
    profile.setdefault("overrides", {})
    return profile


def save_profile(name: str, profile: dict) -> Path:
    ensure_profile_dir(name)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    ppath = profile_path(name, profile["profile_name"])
    with open(ppath, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, allow_unicode=True, sort_keys=False)
    return ppath


def set_active_profile(name: str, spec: dict, profile_name: str) -> None:
    ensure_default_profile(name, spec)
    ppath = profile_path(name, profile_name)
    if not ppath.exists():
        print(f"错误: profile 不存在: {profile_name}")
        sys.exit(1)
    with open(active_profile_path(name), "w", encoding="utf-8") as f:
        yaml.safe_dump({"active_profile": profile_name}, f, allow_unicode=True, sort_keys=False)


def list_profile_names(name: str) -> list[str]:
    return sorted([p.stem for p in profile_dir(name).glob("*.yaml") if not p.name.startswith("_")])


def create_profile_from_source(name: str, spec: dict, new_profile_name: str, from_profile_name: str) -> Path:
    source_profile = load_profile(name, spec, from_profile_name)
    new_profile = copy.deepcopy(source_profile)
    new_profile["profile_name"] = new_profile_name
    new_profile["status"] = "candidate"
    new_profile["source"] = f"profile:{from_profile_name}"
    return save_profile(name, new_profile)


def update_profile_status(name: str, spec: dict, profile_name: str, to_status: str) -> tuple[dict, bool]:
    profile = load_profile(name, spec, profile_name)
    profile["status"] = to_status
    save_profile(name, profile)
    activated = False
    if to_status in {"paper_active", "live_active"}:
        set_active_profile(name, spec, profile_name)
        activated = True
    return profile, activated


def build_profile_from_hyperopt(name: str, profile_name: str, hyperopt_filename: str, params: dict) -> dict:
    hp_params = params.get("params", {})
    factor_overrides: dict[str, dict] = {}
    if "ma_period" in hp_params:
        factor_overrides["ma"] = {"period": hp_params["ma_period"]}
    if "rsi_period" in hp_params:
        factor_overrides.setdefault("rsi", {})
        factor_overrides["rsi"]["period"] = hp_params["rsi_period"]
    if "rsi_oversold" in hp_params:
        factor_overrides["rsi_oversold"] = {"value": hp_params["rsi_oversold"]}
    if "rsi_overbought" in hp_params:
        factor_overrides["rsi_overbought"] = {"value": hp_params["rsi_overbought"]}
    if "bb_period" in hp_params or "bb_std" in hp_params:
        factor_overrides.setdefault("bb", {})
        if "bb_period" in hp_params:
            factor_overrides["bb"]["period"] = hp_params["bb_period"]
        if "bb_std" in hp_params:
            factor_overrides["bb"]["std"] = hp_params["bb_std"]
    if "volume_ma_period" in hp_params or "volume_ratio_threshold" in hp_params:
        factor_overrides.setdefault("volume", {})
        if "volume_ma_period" in hp_params:
            factor_overrides["volume"]["ma_period"] = hp_params["volume_ma_period"]
        if "volume_ratio_threshold" in hp_params:
            factor_overrides["volume"]["ratio_threshold"] = hp_params["volume_ratio_threshold"]

    overrides = {"factors": factor_overrides}
    for key in [
        "stoploss",
        "minimal_roi",
        "trailing_stop",
        "trailing_stop_positive",
        "trailing_stop_positive_offset",
        "trailing_only_offset_is_reached",
    ]:
        if key in params:
            overrides[key] = params[key]
    if "max_open_trades" in params:
        overrides["risk_model"] = {"max_open_trades": params["max_open_trades"]}
    return {
        "profile_name": profile_name,
        "strategy_name": name,
        "status": "candidate",
        "source": f"hyperopt:{hyperopt_filename}",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overrides": overrides,
    }


def load_hyperopt_params(config_path: Path, hyperopt_filename: str) -> dict:
    result = subprocess.run(
        [
            "freqtrade",
            "hyperopt-show",
            "-c",
            str(config_path),
            "--hyperopt-filename",
            hyperopt_filename,
            "--best",
            "--print-json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    json_line = None
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            json_line = line
            break
    if not json_line:
        print("错误: 未能从 hyperopt-show 输出中解析 JSON 参数")
        sys.exit(1)
    return json.loads(json_line)
