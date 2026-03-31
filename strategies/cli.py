#!/usr/bin/env python3
import argparse
import json
import os
import sys
import yaml
from pathlib import Path


STRATEGY_DIR = Path("/freqtrade/user_data/strategies")
SPEC_DIR = Path("/freqtrade/user_data/strategies/spec")
GENERATED_DIR = Path("/freqtrade/user_data/strategies/generated")
RESULTS_DIR = Path("/freqtrade/user_data/strategies/results")
CONFIG_DIR = Path("/freqtrade/user_data/config.json")


def load_spec(name: str) -> dict:
    spec_file = SPEC_DIR / f"{name}.yaml"
    if not spec_file.exists():
        spec_file = SPEC_DIR / f"{name}.yml"
    
    if not spec_file.exists():
        print(f"错误: 找不到规范文件 {name}.yaml")
        sys.exit(1)
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def generate_strategy_v2(name: str, spec: dict) -> str:
    class_name = ''.join(word.capitalize() for word in name.replace('-', ' ').replace('_', ' ').split()) + 'Strategy'
    
    trading_mode = spec.get('trading_mode', 'spot')
    can_short = spec.get('can_short', False) if trading_mode == 'spot' else True
    timeframe = spec.get('timeframe', '15m')
    stoploss = spec.get('stoploss', -0.03)
    minimal_roi = spec.get('minimal_roi', {"0": 0.01})
    trailing_stop = spec.get('trailing_stop', True)
    trailing_stop_positive = spec.get('trailing_stop_positive', 0.01)
    trailing_stop_positive_offset = spec.get('trailing_stop_positive_offset', 0.015)
    
    added_params = set()
    params_code = []
    indicators_code = []
    
    factors = spec.get('factors', {})
    
    if factors.get('ma', {}).get('enabled', False):
        ma = factors['ma']
        param_name = 'ma_period'
        params_code.append(f"    {param_name} = IntParameter({ma['range'][0]}, {ma['range'][1]}, default={ma['period']}, space=\"{ma.get('space', 'buy')}\")")
        added_params.add(param_name)
        ma_type = ma.get('type', 'SMA')
        indicators_code.append(f"        dataframe['ma'] = ta.{ma_type}(dataframe['close'], timeperiod=self.ma_period.value)")
    
    if factors.get('rsi', {}).get('enabled', False):
        rsi = factors['rsi']
        param_name = 'rsi_period'
        params_code.append(f"    {param_name} = IntParameter({rsi['range'][0]}, {rsi['range'][1]}, default={rsi['period']}, space=\"{rsi.get('space', 'buy')}\")")
        added_params.add(param_name)
        indicators_code.append(f"        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=self.rsi_period.value)")
    
    if factors.get('rsi_oversold', {}).get('enabled', False):
        rsi_os = factors['rsi_oversold']
        params_code.append(f"    rsi_oversold = DecimalParameter({rsi_os['range'][0]}, {rsi_os['range'][1]}, default={rsi_os['value']}, decimals=1, space=\"{rsi_os.get('space', 'buy')}\")")
        added_params.add('rsi_oversold')
    
    if factors.get('rsi_overbought', {}).get('enabled', False):
        rsi_ob = factors['rsi_overbought']
        params_code.append(f"    rsi_overbought = DecimalParameter({rsi_ob['range'][0]}, {rsi_ob['range'][1]}, default={rsi_ob['value']}, decimals=1, space=\"{rsi_ob.get('space', 'sell')}\")")
        added_params.add('rsi_overbought')
    
    if factors.get('bb', {}).get('enabled', False):
        bb = factors['bb']
        params_code.append(f"    bb_period = IntParameter(10, 50, default={bb['period']}, space=\"buy\")")
        added_params.add('bb_period')
        std_range = bb.get('std_range', [1.5, 3.0])
        params_code.append(f"    bb_std = DecimalParameter({std_range[0]}, {std_range[1]}, default={bb.get('std', 2.0)}, decimals=1, space=\"buy\")")
        added_params.add('bb_std')
        indicators_code.append(f"        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)")
    
    if factors.get('volume', {}).get('enabled', False):
        vol = factors['volume']
        params_code.append(f"    volume_ma_period = IntParameter(10, 30, default={vol['ma_period']}, space=\"buy\")")
        added_params.add('volume_ma_period')
        params_code.append(f"    volume_ratio_threshold = DecimalParameter(1.0, 2.5, default={vol['ratio_threshold']}, decimals=1, space=\"buy\")")
        added_params.add('volume_ratio_threshold')
        indicators_code.append(f"        dataframe['volume_ma'] = dataframe['volume'].rolling(window=self.volume_ma_period.value).mean()")
        indicators_code.append(f"        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']")
    
    if factors.get('macd', {}).get('enabled', False):
        macd = factors['macd']
        params_code.append(f"    macd_fast = IntParameter(5, 15, default={macd['fast']}, space=\"buy\")")
        params_code.append(f"    macd_slow = IntParameter(15, 35, default={macd['slow']}, space=\"buy\")")
        params_code.append(f"    macd_signal = IntParameter(5, 15, default={macd['signal']}, space=\"buy\")")
        indicators_code.append(f"        dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=self.macd_fast.value, slowperiod=self.macd_slow.value, signalperiod=self.macd_signal.value)")
    
    for ind in spec.get('derived_indicators', []):
        ind_name = ind['name']
        formula = ind.get('formula', '')
        indicators_code.append(f"        dataframe['{ind_name}'] = {formula}")
    
    entry = spec.get('entry_conditions', {})
    long_entry = entry.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_entry = entry.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    exit_cond = spec.get('exit_conditions', {})
    long_exit = exit_cond.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_exit = exit_cond.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    code = f'''"""
{spec.get('description', name)} V{spec.get('version', '1.0')} - Auto-generated strategy
Trading Mode: {trading_mode}
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class {class_name}(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = {can_short}
    timeframe = "{timeframe}"
    
    stoploss = {stoploss}
    minimal_roi = {json.dumps(minimal_roi)}
    
    trailing_stop = {trailing_stop}
    trailing_stop_positive = {trailing_stop_positive}
    trailing_stop_positive_offset = {trailing_stop_positive_offset}
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
{chr(10).join(params_code)}
    
    startup_candle_count = 300
    
    order_types = {{
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }}
    
    order_time_in_force = {{"entry": "GTC", "exit": "GTC"}}
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
{chr(10).join(indicators_code)}
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        long_condition = {long_entry}
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = {short_entry}
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
'''
    
    return code


def generate_strategy(name: str, spec: dict) -> str:
    return generate_strategy_v2(name, spec)
    
    can_short = spec.get('can_short', False)
    timeframe = spec.get('timeframe', '15m')
    stoploss = spec.get('stoploss', -0.03)
    minimal_roi = spec.get('minimal_roi', {"0": 0.01})
    trailing_stop = spec.get('trailing_stop', True)
    trailing_stop_positive = spec.get('trailing_stop_positive', 0.01)
    trailing_stop_positive_offset = spec.get('trailing_stop_positive_offset', 0.015)
    
    added_params = set()
    params_code = []
    indicators_code = []
    
    for ind in spec.get('indicators', []):
        ind_name = ind['name'].lower()
        ind_type = ind.get('type', 'SMA')
        params = ind.get('params', [10, 50, 20])
        
        if ind_type in ['SMA', 'EMA', 'WMA']:
            param_name = f"{ind_name}_period"
            if param_name not in added_params:
                params_code.append(f"    {param_name} = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add(param_name)
            indicators_code.append(f"        dataframe['{ind_name}'] = ta.{ind_type}(dataframe['close'], timeperiod=self.{param_name}.value)")
        elif ind_type == 'RSI':
            param_name = f"{ind_name}_period"
            if param_name not in added_params:
                params_code.append(f"    {param_name} = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add(param_name)
            indicators_code.append(f"        dataframe['{ind_name}'] = ta.RSI(dataframe['close'], timeperiod=self.{param_name}.value)")
        elif ind_type == 'BB':
            if 'bb_period' not in added_params:
                params_code.append(f"    bb_period = IntParameter({params[0]}, {params[1]}, default={params[2]}, space=\"buy\")")
                added_params.add('bb_period')
            std_params = ind.get('std', [1.5, 3.0, 2.0])
            if 'bb_std' not in added_params:
                params_code.append(f"    bb_std = DecimalParameter({std_params[0]}, {std_params[1]}, default={std_params[2]}, decimals=1, space=\"buy\")")
                added_params.add('bb_std')
            indicators_code.append(f"        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)")
    
    for ind in spec.get('derived_indicators', []):
        ind_name = ind['name']
        formula = ind.get('formula', '')
        indicators_code.append(f"        dataframe['{ind_name}'] = {formula}")
    
    entry = spec.get('entry_conditions', {})
    long_entry = entry.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_entry = entry.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    exit_cond = spec.get('exit_conditions', {})
    long_exit = exit_cond.get('long', 'False').replace('\n', ' ').replace('  ', ' ')
    short_exit = exit_cond.get('short', 'False').replace('\n', ' ').replace('  ', ' ')
    
    params = spec.get('params', {})
    for pname, pdata in params.items():
        if pname not in added_params:
            if 'rsi_oversold' in pname or 'rsi_overbought' in pname:
                params_code.append(f"    {pname} = DecimalParameter({pdata['min']}, {pdata['max']}, default={pdata['default']}, decimals=1, space=\"buy\" if 'oversold' in '{pname}' else \"sell\")")
            else:
                params_code.append(f"    {pname} = IntParameter({pdata['min']}, {pdata['max']}, default={pdata['default']}, space=\"buy\")")
            added_params.add(pname)
    
    code = f'''"""
{spec.get('description', name)} - Auto-generated strategy
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
)


class {class_name}(IStrategy):
    INTERFACE_VERSION = 3
    
    can_short = {can_short}
    timeframe = "{timeframe}"
    
    stoploss = {stoploss}
    minimal_roi = {json.dumps(minimal_roi)}
    
    trailing_stop = {trailing_stop}
    trailing_stop_positive = {trailing_stop_positive}
    trailing_stop_positive_offset = {trailing_stop_positive_offset}
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
{chr(10).join(params_code)}
    
    startup_candle_count = 300
    
    order_types = {{
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }}
    
    order_time_in_force = {{"entry": "GTC", "exit": "GTC"}}
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
{chr(10).join(indicators_code)}
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        long_condition = {long_entry}
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        short_condition = {short_entry}
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        rsi_oversold = self.rsi_oversold.value if hasattr(self, 'rsi_oversold') else 30
        rsi_overbought = self.rsi_overbought.value if hasattr(self, 'rsi_overbought') else 70
        
        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
'''
    
    return code


def cmd_list(args):
    """列出所有策略"""
    print("\n=== 策略规范 ===")
    for f in sorted(SPEC_DIR.glob("*.yaml")):
        print(f"  - {f.stem}")
    
    print("\n=== 已生成策略 ===")
    for f in sorted(GENERATED_DIR.glob("*.py")):
        print(f"  - {f.stem}")
    
    print()


def cmd_generate(args):
    name = args.name
    print(f"生成策略: {name}")
    
    spec = load_spec(name)
    code = generate_strategy(name, spec)
    
    output_file = GENERATED_DIR / f"{name}.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    strategy_file = STRATEGY_DIR / f"auto_{name}.py"
    with open(strategy_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"  生成完成: {output_file}")
    print(f"  复制到: {strategy_file}")
    print(f"\n  同步到本地:")
    print(f"    docker cp freqtrade:{output_file} /Users/wangjiangtao/Documents/AI/AI-OuYi/strategies/generated/")


def cmd_backtest(args):
    name = args.name
    timerange = args.timerange or "20250101-"
    
    strategy_file = GENERATED_DIR / f"{name}.py"
    if not strategy_file.exists():
        print(f"错误: 策略 {name} 尚未生成，请先运行 generate")
        sys.exit(1)
    
    spec = load_spec(name)
    trading_mode = spec.get('trading_mode', 'spot')
    
    config_path = "/freqtrade/user_data/config.json"
    if trading_mode == 'futures':
        config_path = "/freqtrade/user_data/config_futures.json"
        if not Path(config_path).exists():
            config_path = "/freqtrade/user_data/config.json"
    
    print(f"运行回测: {name}")
    print(f"  交易模式: {trading_mode}")
    print(f"  时间范围: {timerange}")
    
    os.system(f"freqtrade backtesting -c {config_path} -s {name} --timerange {timerange}")


def cmd_optimize(args):
    name = args.name
    epochs = args.epochs or 200
    timerange = args.timerange or "20250101-20251101"
    
    strategy_file = GENERATED_DIR / f"{name}.py"
    if not strategy_file.exists():
        print(f"错误: 策略 {name} 尚未生成，请先运行 generate")
        sys.exit(1)
    
    spec = load_spec(name)
    opt_config = spec.get('optimization', {})
    trading_mode = spec.get('trading_mode', 'spot')
    
    config_path = "/freqtrade/user_data/config.json"
    if trading_mode == 'futures':
        config_path = "/freqtrade/user_data/config_futures.json"
        if not Path(config_path).exists():
            config_path = "/freqtrade/user_data/config.json"
    
    print(f"运行参数优化: {name}")
    print(f"  迭代次数: {epochs}")
    print(f"  时间范围: {timerange}")
    print(f"  交易模式: {trading_mode}")
    
    cmd = f"freqtrade hyperopt -c {config_path} -s {name} --timerange {timerange} --epochs {epochs} -j 4"
    if opt_config.get('hyperopt_loss'):
        cmd += f" --hyperopt-loss {opt_config['hyperopt_loss']}"
    
    os.system(cmd)
    
    result_file = GENERATED_DIR / f"{name}.json"
    if result_file.exists():
        print(f"\n优化参数已保存到: {result_file}")


def cmd_run(args):
    """运行完整流程"""
    name = args.name
    
    print(f"=== 运行完整流程: {name} ===\n")
    
    print("[1/3] 生成策略...")
    spec = load_spec(name)
    code = generate_strategy(name, spec)
    output_file = GENERATED_DIR / f"{name}.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"  完成: {output_file}\n")
    
    opt_config = spec.get('optimization', {})
    epochs = opt_config.get('epochs', 200)
    timerange = opt_config.get('timerange', "20250101-20251101")
    
    print(f"[2/3] 参数优化 (epochs={epochs})...")
    cmd = f"freqtrade hyperopt -c /freqtrade/user_data/config.json -s {name} --timerange {timerange} --epochs {epochs} -j 4"
    if opt_config.get('hyperopt_loss'):
        cmd += f" --hyperopt-loss {opt_config['hyperopt_loss']}"
    os.system(cmd)
    print()
    
    test_timerange = spec.get('test_timerange', "20251101-")
    print(f"[3/3] 回测验证...")
    os.system(f"freqtrade backtesting -c /freqtrade/user_data/config.json -s {name} --timerange {test_timerange}")
    
    print("\n=== 完成 ===")


def cmd_config(args):
    name = args.name
    
    spec = load_spec(name)
    
    if args.list:
        print(f"\n=== {name} 配置 ===")
        print(f"\n交易模式: {spec.get('trading_mode', 'spot')}")
        print(f"时间框架: {spec.get('timeframe')}")
        print(f"支持做空: {spec.get('can_short')}")
        
        print("\n--- 因子配置 ---")
        factors = spec.get('factors', {})
        for fname, fconfig in factors.items():
            if fconfig.get('enabled', False):
                print(f"\n{fname}:")
                if 'range' in fconfig:
                    print(f"  范围: {fconfig['range']}")
                if 'value' in fconfig:
                    print(f"  默认值: {fconfig['value']}")
                if 'period' in fconfig:
                    print(f"  周期: {fconfig['period']}")
        
        print("\n--- config_overrides ---")
        overrides = spec.get('config_overrides', {})
        for k, v in overrides.items():
            print(f"  {k}: {v}")
        
        print()
        return
    
    if args.set:
        key, value = args.set
        try:
            value = float(value)
        except ValueError:
            pass
        
        if 'config_overrides' not in spec:
            spec['config_overrides'] = {}
        spec['config_overrides'][key] = value
        
        spec_file = SPEC_DIR / f"{name}.yaml"
        with open(spec_file, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, allow_unicode=True, default_flow_style=False)
        
        print(f"已设置 {key} = {value}")
        print("请重新生成策略: generate", name)
        return
    
    print(f"用法:")
    print(f"  python cli.py config {name} --list      # 列出配置")
    print(f"  python cli.py config {name} --set ma_period 200  # 设置参数")


def main():
    parser = argparse.ArgumentParser(description="策略管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    subparsers.add_parser("list", help="列出所有策略")
    
    gen_parser = subparsers.add_parser("generate", help="生成策略代码")
    gen_parser.add_argument("name", help="策略名称")
    
    bt_parser = subparsers.add_parser("backtest", help="运行回测")
    bt_parser.add_argument("name", help="策略名称")
    bt_parser.add_argument("--timerange", "-t", help="时间范围")
    
    opt_parser = subparsers.add_parser("optimize", help="运行参数优化")
    opt_parser.add_argument("name", help="策略名称")
    opt_parser.add_argument("--epochs", "-e", type=int, help="迭代次数")
    opt_parser.add_argument("--timerange", "-t", help="时间范围")
    
    run_parser = subparsers.add_parser("run", help="运行完整流程")
    run_parser.add_argument("name", help="策略名称")
    
    config_parser = subparsers.add_parser("config", help="查看/修改策略配置")
    config_parser.add_argument("name", help="策略名称")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="设置参数")
    config_parser.add_argument("--list", action="store_true", help="列出所有参数")
    
    args = parser.parse_args()
    
    if args.command == "list":
        cmd_list(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "optimize":
        cmd_optimize(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
