#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path
from services.config_service import print_config, print_config_usage, set_default_config_value
from services.execution_service import run_backtest, run_backtest_phase, run_hyperopt, runtime_param_snapshot_path
from services.generation_service import GENERATED_DIR, ensure_generated_strategy
from services.profile_service import (
    ensure_default_profile,
    get_active_profile_name,
    load_profile,
)
from services.profile_workflow_service import activate_profile, create_profile, import_hyperopt_profile, list_profiles, promote_profile, validate_profile
from services.runtime_service import STRATEGY_DIR, sync_runtime_profile
from services.spec_service import (
    SPEC_DIR,
    build_protections,
    get_config_path,
    get_cost_model,
    get_effective_spec,
    get_risk_model,
    get_timeranges,
    load_spec,
)

PROFILE_BT_RESULT_DIR = Path("/freqtrade/user_data/backtest_results/profile_validation")
CONFIG_DIR = Path("/freqtrade/user_data/config.json")


def cmd_list(args):
    """列出所有策略"""
    print("\n=== 策略规范 ===")
    for f in sorted(SPEC_DIR.glob("*.yaml")):
        print(f"  - {f.stem}")
    
    print("\n=== 已生成策略 ===")
    for f in sorted(GENERATED_DIR.glob("*.py")):
        print(f"  - {f.stem}")

    print("\n=== Profiles ===")
    for f in sorted(SPEC_DIR.glob("*.yaml")):
        name = f.stem
        spec = load_spec(name)
        ensure_default_profile(name, spec)
        active, profiles = list_profiles(name, spec)
        print(f"  - {name}: active={active}, profiles={[profile['name'] for profile in profiles]}")
    
    print()


def cmd_generate(args):
    name = args.name
    print(f"生成策略: {name}")
    
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    output_file = ensure_generated_strategy(name, spec)
    runtime_json = sync_runtime_profile(name, spec, profile)
    
    print(f"  生成完成: {output_file}")
    print(f"  复制到: {STRATEGY_DIR / f'auto_{name}.py'}")
    print(f"  运行参数快照: {runtime_json}")
    print(f"  使用 profile: {profile['profile_name']}")
    print(f"\n  当前仓库以 strategies/ 为单一策略源码目录，无需额外 docker cp 同步。")


def cmd_backtest(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    timeranges = get_timeranges(spec)
    phase = args.phase or "train"
    timerange = args.timerange or timeranges[phase]
    config_path = get_config_path(spec)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    run_backtest(
        strategy_name=name,
        phase=phase,
        timerange=timerange,
        config_path=config_path,
        cost_model=cost_model,
        risk_model=risk_model,
        enable_protections=bool(build_protections(spec)),
    )


def cmd_validate(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    config_path = get_config_path(spec)
    timeranges = get_timeranges(spec)

    print(f"运行分段验证: {name}")
    print(f"  train: {timeranges['train']}")
    print(f"  validation: {timeranges['validation']}")
    print(f"  test: {timeranges['test']}")

    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    enable_protections = bool(build_protections(spec))
    for phase in ["train", "validation", "test"]:
        run_backtest_phase(
            strategy_name=name,
            config_path=config_path,
            label=phase.upper(),
            timerange=timeranges[phase],
            fee=cost_model.get("fee"),
            risk_model=risk_model,
            enable_protections=enable_protections,
        )


def cmd_optimize(args):
    name = args.name
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    opt_config = spec.get('optimization', {})
    epochs = args.epochs or opt_config.get('epochs', 200)
    timerange = args.timerange or spec.get('train_timerange') or opt_config.get('timerange', "20250101-20250930")
    config_path = get_config_path(spec)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    
    print(f"运行参数优化: {name}")
    print(f"  迭代次数: {epochs}")
    print(f"  时间范围: {timerange}")
    print(f"  阶段: train")
    if cost_model.get('fee') is not None:
        print(f"  fee: {cost_model['fee']}")
    if risk_model:
        print(f"  风控边界: max_open_trades={risk_model.get('max_open_trades')}, max_daily_loss_pct={risk_model.get('max_daily_loss_pct')}, max_drawdown_pct={risk_model.get('max_drawdown_pct')}")

    run_hyperopt(
        strategy_name=name,
        epochs=epochs,
        timerange=timerange,
        config_path=config_path,
        hyperopt_loss=opt_config.get("hyperopt_loss"),
        fee=cost_model.get("fee"),
        enable_protections=bool(build_protections(spec)),
    )

    result_file = runtime_param_snapshot_path(name)
    if result_file.exists():
        print(f"\n优化参数已保存到: {result_file}")


def cmd_run(args):
    """运行完整流程"""
    name = args.name
    
    print(f"=== 运行完整流程: {name} ===\n")
    
    spec, profile = get_effective_spec(name, getattr(args, "profile", None))
    print("[1/4] 生成策略...")
    output_file = ensure_generated_strategy(name, spec)
    sync_runtime_profile(name, spec, profile)
    print(f"  完成: {output_file}\n")
    
    opt_config = spec.get('optimization', {})
    epochs = opt_config.get('epochs', 200)
    timeranges = get_timeranges(spec)
    config_path = get_config_path(spec)
    cost_model = get_cost_model(spec)
    risk_model = get_risk_model(spec)
    enable_protections = bool(build_protections(spec))
    
    print(f"[2/4] 训练集参数优化 (epochs={epochs})...")
    run_hyperopt(
        strategy_name=name,
        epochs=epochs,
        timerange=timeranges["train"],
        config_path=config_path,
        hyperopt_loss=opt_config.get("hyperopt_loss"),
        fee=cost_model.get("fee"),
        enable_protections=enable_protections,
    )
    print()
    
    print("[3/4] 验证集回测...")
    run_backtest_phase(
        strategy_name=name,
        config_path=config_path,
        label="VALIDATION",
        timerange=timeranges["validation"],
        fee=cost_model.get("fee"),
        risk_model=risk_model,
        enable_protections=enable_protections,
    )
    
    print("\n[4/4] 测试集回测...")
    run_backtest_phase(
        strategy_name=name,
        config_path=config_path,
        label="TEST",
        timerange=timeranges["test"],
        fee=cost_model.get("fee"),
        risk_model=risk_model,
        enable_protections=enable_protections,
    )
    
    print("\n=== 完成 ===")


def cmd_config(args):
    name = args.name
    
    spec = load_spec(name)
    ensure_default_profile(name, spec)
    active_profile = load_profile(name, spec)
    
    if args.list:
        print_config(name, spec, active_profile)
        return
    
    if args.set:
        key, value = args.set
        value = set_default_config_value(name, spec, key, value)
        
        print(f"已设置默认参数 {key} = {value}")
        print("请重新生成策略: generate", name)
        return
    
    print_config_usage(name)


def cmd_profile(args):
    name = args.name
    spec = load_spec(name)
    ensure_default_profile(name, spec)

    if args.profile_command == "list":
        _, profiles = list_profiles(name, spec)
        print(f"\n=== {name} profiles ===")
        for profile in profiles:
            mark = "*" if profile["active"] else " "
            print(f"{mark} {profile['name']}  status={profile['status']}  source={profile['source']}")
        print()
        return

    if args.profile_command == "show":
        profile = load_profile(name, spec, args.profile_name)
        pprint.pprint(profile, sort_dicts=False)
        return

    if args.profile_command == "create":
        from_profile_name = args.from_profile or get_active_profile_name(name, spec)
        ppath = create_profile(name, spec, args.profile_name, from_profile_name)
        print(f"已创建 profile: {ppath}")
        return

    if args.profile_command == "activate":
        runtime_json = activate_profile(name, spec, args.profile_name)
        print(f"已激活 profile: {args.profile_name}")
        print(f"运行参数快照: {runtime_json}")
        return

    if args.profile_command == "promote":
        _, activated, runtime_json = promote_profile(name, spec, args.profile_name, args.to_status)
        if activated:
            print(f"已晋级并激活 profile: {args.profile_name} -> {args.to_status}")
            print(f"运行参数快照: {runtime_json}")
            return
        print(f"已晋级 profile: {args.profile_name} -> {args.to_status}")
        return

    if args.profile_command == "import-hyperopt":
        ppath = import_hyperopt_profile(name, CONFIG_DIR, args.profile_name, args.hyperopt_filename)
        print(f"已从 hyperopt 结果导入 candidate profile: {ppath}")
        return

    if args.profile_command == "validate":
        validation_result, promoted = validate_profile(
            name=name,
            spec=spec,
            profile_name=args.profile_name,
            ensure_generated_strategy=ensure_generated_strategy,
            profile_bt_result_dir=PROFILE_BT_RESULT_DIR,
            timerange_override=args.timerange,
            min_trades=args.min_trades,
            min_profit=args.min_profit,
            min_profit_factor=args.min_profit_factor,
            max_drawdown=args.max_drawdown,
            promote_on_pass=args.promote_on_pass,
        )
        metrics = validation_result["metrics"]
        gate = validation_result["gate"]
        passed = validation_result["passed"]

        print(f"Validation profile: {validation_result['profile_name']}")
        print(f"Timerange: {validation_result['timerange']}")
        print(f"Backtest result: {validation_result['backtest_zip']}")
        print(f"total_trades={metrics['total_trades']}")
        print(f"profit_total={metrics['profit_total']:.6f}")
        print(f"profit_total_abs={metrics['profit_total_abs']:.6f} {metrics['stake_currency']}")
        print(f"profit_factor={metrics['profit_factor']:.4f}")
        print(f"max_drawdown_account={metrics['max_drawdown_account']:.4f}")
        print(
            f"Gate: min_trades>={gate['min_trades']}, min_profit>={gate['min_profit']}, "
            f"min_profit_factor>={gate['min_profit_factor']}, max_drawdown<={gate['max_drawdown']}"
        )
        print(f"Validation status: {'PASS' if passed else 'FAIL'}")

        if promoted:
            print(f"已自动晋级 profile -> validated: {validation_result['profile_name']}")
        if not passed:
            sys.exit(2)
        return

    print("支持的 profile 子命令: list/show/create/activate/promote/import-hyperopt/validate")


def main():
    parser = argparse.ArgumentParser(description="策略管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    subparsers.add_parser("list", help="列出所有策略")
    
    gen_parser = subparsers.add_parser("generate", help="生成策略代码")
    gen_parser.add_argument("name", help="策略名称")
    gen_parser.add_argument("--profile", help="使用指定 profile 生成运行快照")
    
    bt_parser = subparsers.add_parser("backtest", help="运行回测")
    bt_parser.add_argument("name", help="策略名称")
    bt_parser.add_argument("--timerange", "-t", help="时间范围")
    bt_parser.add_argument("--phase", choices=["train", "validation", "test"], help="使用 YAML 中的阶段时间范围")
    bt_parser.add_argument("--profile", help="使用指定 profile")
    
    validate_parser = subparsers.add_parser("validate", help="运行 train/validation/test 分段回测")
    validate_parser.add_argument("name", help="策略名称")
    validate_parser.add_argument("--profile", help="使用指定 profile")
    
    opt_parser = subparsers.add_parser("optimize", help="运行参数优化")
    opt_parser.add_argument("name", help="策略名称")
    opt_parser.add_argument("--epochs", "-e", type=int, help="迭代次数")
    opt_parser.add_argument("--timerange", "-t", help="时间范围")
    opt_parser.add_argument("--profile", help="使用指定 profile")
    
    run_parser = subparsers.add_parser("run", help="运行完整流程")
    run_parser.add_argument("name", help="策略名称")
    run_parser.add_argument("--profile", help="使用指定 profile")
    
    config_parser = subparsers.add_parser("config", help="查看/修改策略配置")
    config_parser.add_argument("name", help="策略名称")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="设置参数")
    config_parser.add_argument("--list", action="store_true", help="列出所有参数")

    profile_parser = subparsers.add_parser("profile", help="管理策略 profiles 与 promotion")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", help="profile 子命令")

    profile_list = profile_subparsers.add_parser("list", help="列出所有 profiles")
    profile_list.add_argument("name", help="策略名称")

    profile_show = profile_subparsers.add_parser("show", help="查看 profile 内容")
    profile_show.add_argument("name", help="策略名称")
    profile_show.add_argument("profile_name", nargs="?", help="profile 名称，默认 active")

    profile_create = profile_subparsers.add_parser("create", help="从现有 profile 复制创建 candidate")
    profile_create.add_argument("name", help="策略名称")
    profile_create.add_argument("profile_name", help="新 profile 名称")
    profile_create.add_argument("--from-profile", help="复制来源 profile，默认 active")

    profile_activate = profile_subparsers.add_parser("activate", help="激活 profile")
    profile_activate.add_argument("name", help="策略名称")
    profile_activate.add_argument("profile_name", help="profile 名称")

    profile_promote = profile_subparsers.add_parser("promote", help="晋级 profile 状态")
    profile_promote.add_argument("name", help="策略名称")
    profile_promote.add_argument("profile_name", help="profile 名称")
    profile_promote.add_argument("to_status", choices=["candidate", "validated", "paper_active", "live_active"], help="目标状态")

    profile_import = profile_subparsers.add_parser("import-hyperopt", help="从 hyperopt 结果导入 candidate profile")
    profile_import.add_argument("name", help="策略名称")
    profile_import.add_argument("profile_name", help="新 candidate profile 名称")
    profile_import.add_argument("hyperopt_filename", help="hyperopt 结果文件名")

    profile_validate = profile_subparsers.add_parser("validate", help="跑 validation timerange 回测并评估 profile gate")
    profile_validate.add_argument("name", help="策略名称")
    profile_validate.add_argument("profile_name", nargs="?", help="profile 名称，默认 active")
    profile_validate.add_argument("--timerange", "-t", help="覆盖 validation_timerange")
    profile_validate.add_argument("--min-trades", type=int, default=1, help="最低成交笔数")
    profile_validate.add_argument("--min-profit", type=float, default=0.0, help="最低 profit_total")
    profile_validate.add_argument("--min-profit-factor", type=float, default=1.0, help="最低 profit_factor")
    profile_validate.add_argument("--max-drawdown", type=float, default=0.30, help="允许的最大回撤比例")
    profile_validate.add_argument("--promote-on-pass", action="store_true", help="验证通过后自动晋级为 validated")
    
    args = parser.parse_args()
    
    if args.command == "list":
        cmd_list(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "optimize":
        cmd_optimize(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "profile":
        cmd_profile(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
