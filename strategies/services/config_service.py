import pprint
import sys

import yaml

from services.profile_service import PARAM_FACTOR_MAP, default_profile_payload, save_profile
from services.spec_service import SPEC_DIR, get_risk_model


def print_config(name: str, spec: dict, active_profile: dict) -> None:
    print(f"\n=== {name} 配置 ===")
    print(f"\nActive profile: {active_profile['profile_name']} ({active_profile.get('status', 'draft')})")
    print(f"\n交易模式: {spec.get('trading_mode', 'spot')}")
    print(f"时间框架: {spec.get('timeframe')}")
    print(f"支持做空: {spec.get('can_short')}")

    print("\n--- 因子配置 ---")
    factors = spec.get("factors", {})
    for fname, fconfig in factors.items():
        if fconfig.get("enabled", False):
            print(f"\n{fname}:")
            if "range" in fconfig:
                print(f"  范围: {fconfig['range']}")
            if "value" in fconfig:
                print(f"  默认值: {fconfig['value']}")
            if "period" in fconfig:
                print(f"  周期: {fconfig['period']}")

    print("\n--- 当前默认参数基线 ---")
    for key, (factor_name, field_name) in PARAM_FACTOR_MAP.items():
        factor = factors.get(factor_name, {})
        if field_name in factor:
            print(f"  {key}: {factor[field_name]}")

    print("\n--- 当前 active profile 覆盖值 ---")
    pprint.pprint(active_profile.get("overrides", {}), sort_dicts=False)

    print("\n--- 风控模型 ---")
    risk_model = get_risk_model(spec)
    for key, value in risk_model.items():
        if key != "notes":
            print(f"  {key}: {value}")

    print()


def set_default_config_value(name: str, spec: dict, key: str, raw_value: str) -> float | str:
    try:
        value = float(raw_value)
    except ValueError:
        value = raw_value

    if key not in PARAM_FACTOR_MAP:
        print(f"错误: 暂不支持设置参数 {key}")
        print(f"支持的参数: {', '.join(PARAM_FACTOR_MAP.keys())}")
        sys.exit(1)

    factor_name, field_name = PARAM_FACTOR_MAP[key]
    if "factors" not in spec or factor_name not in spec["factors"]:
        print(f"错误: 规范中找不到参数对应的因子 {factor_name}")
        sys.exit(1)

    spec["factors"][factor_name][field_name] = value

    spec_file = SPEC_DIR / f"{name}.yaml"
    with open(spec_file, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False)
    save_profile(name, default_profile_payload(name, spec))
    return value


def print_config_usage(name: str) -> None:
    print("用法:")
    print(f"  python cli.py config {name} --list      # 列出配置")
    print(f"  python cli.py config {name} --set ma_period 200  # 设置参数")
