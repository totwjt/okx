"""
策略基类模板
Freqtrade 策略生成器的基类，提供通用的策略结构
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
import talib as ta

from freqtrade.strategy import (
    IStrategy,
    DecimalParameter,
    IntParameter,
    CategoricalParameter,
)


class BaseStrategy(IStrategy):
    """基类策略 - 所有生成的策略继承此类"""
    
    INTERFACE_VERSION = 3
    
    # ========== 基本设置 (可在YAML中覆盖) ==========
    can_short = False
    timeframe = "15m"
    
    # 止盈止损
    stoploss = -0.03
    minimal_roi = {"0": 0.01}
    
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    
    # 执行设置
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}
    
    plot_config = {}
    
    # ========== 参数定义 (子类必须定义) ==========
    # 格式: name = ParamType(min, max, default, space="buy/sell")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算所有指标 - 子类必须实现"""
        raise NotImplementedError("子类必须实现 populate_indicators")
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """设置入场信号 - 子类必须实现"""
        raise NotImplementedError("子类必须实现 populate_entry_trend")
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """设置出场信号 - 子类必须实现"""
        raise NotImplementedError("子类必须实现 populate_exit_trend")
    
    # ========== 辅助方法 ==========
    
    def get_ma(self, dataframe: DataFrame, period: int, ma_type: str = "SMA") -> DataFrame:
        """获取移动平均线"""
        if ma_type == "SMA":
            return ta.SMA(dataframe['close'], timeperiod=period)
        elif ma_type == "EMA":
            return ta.EMA(dataframe['close'], timeperiod=period)
        elif ma_type == "WMA":
            return ta.WMA(dataframe['close'], timeperiod=period)
        return ta.SMA(dataframe['close'], timeperiod=period)
    
    def get_rsi(self, dataframe: DataFrame, period: int) -> DataFrame:
        """获取RSI"""
        return ta.RSI(dataframe['close'], timeperiod=period)
    
    def get_bb(self, dataframe: DataFrame, period: int, std: float) -> tuple:
        """获取布林带"""
        return ta.BBANDS(
            dataframe['close'],
            timeperiod=period,
            nbdevup=std,
            nbdevdn=std
        )
    
    def get_macd(self, dataframe: DataFrame, fast: int, slow: int, signal: int) -> tuple:
        """获取MACD"""
        return ta.MACD(
            dataframe['close'],
            fastperiod=fast,
            slowperiod=slow,
            signalperiod=signal
        )
    
    def get_atr(self, dataframe: DataFrame, period: int) -> DataFrame:
        """获取ATR"""
        return ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=period)
    
    def get_adx(self, dataframe: DataFrame, period: int) -> DataFrame:
        """获取ADX"""
        return ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=period)


def generate_strategy_class(spec: dict) -> str:
    """
    根据策略规范生成策略类代码
    
    Args:
        spec: 策略规范字典
        
    Returns:
        str: 生成的Python代码
    """
    name = spec.get('name', 'Strategy')
    class_name = name.replace('-', '').replace(' ', '') + 'Strategy'
    
    # 基本设置
    can_short = spec.get('can_short', False)
    timeframe = spec.get('timeframe', '15m')
    stoploss = spec.get('stoploss', -0.03)
    minimal_roi = spec.get('minimal_roi', {"0": 0.01})
    trailing_stop = spec.get('trailing_stop', True)
    trailing_stop_positive = spec.get('trailing_stop_positive', 0.01)
    trailing_stop_positive_offset = spec.get('trailing_stop_positive_offset', 0.015)
    
    # 指标定义
    indicators_code = []
    params_code = []
    
    for ind in spec.get('indicators', []):
        ind_name = ind['name']
        ind_type = ind.get('type', 'SMA')
        param_name = ind['name'].lower()
        
        if ind_type == 'SMA':
            indicators_code.append(f"        dataframe['{param_name}'] = ta.SMA(dataframe['close'], timeperiod=self.{param_name}_period.value)")
            params_code.append(f"    {param_name}_period = IntParameter({ind['params'][0]}, {ind['params'][1]}, default={ind['params'][2]}, space=\"buy\")")
        elif ind_type == 'EMA':
            indicators_code.append(f"        dataframe['{param_name}'] = ta.EMA(dataframe['close'], timeperiod=self.{param_name}_period.value)")
            params_code.append(f"    {param_name}_period = IntParameter({ind['params'][0]}, {ind['params'][1]}, default={ind['params'][2]}, space=\"buy\")")
        elif ind_type == 'RSI':
            indicators_code.append(f"        dataframe['{param_name}'] = ta.RSI(dataframe['close'], timeperiod=self.{param_name}_period.value)")
            params_code.append(f"    {param_name}_period = IntParameter({ind['params'][0]}, {ind['params'][1]}, default={ind['params'][2]}, space=\"buy\")")
        elif ind_type == 'BB':
            bb_upper, bb_middle, bb_lower = ind['name'].lower(), ind['name'].lower(), ind['name'].lower()
            indicators_code.append(f"        dataframe['bb_upper'], dataframe['bb_middle'], dataframe['bb_lower'] = ta.BBANDS(dataframe['close'], timeperiod=self.bb_period.value, nbdevup=self.bb_std.value, nbdevdn=self.bb_std.value)")
            params_code.append(f"    bb_period = IntParameter({ind['params'][0]}, {ind['params'][1]}, default={ind['params'][2]}, space=\"buy\")")
            params_code.append(f"    bb_std = DecimalParameter({ind.get('std', [1.5, 3.0, 2.0])[0]}, {ind.get('std', [1.5, 3.0, 2.0])[1]}, default={ind.get('std', [1.5, 3.0, 2.0])[2]}, decimals=1, space=\"buy\")")
    
    # 入场条件
    entry_code = spec.get('entry_conditions', {})
    long_condition = entry_code.get('long', 'False')
    short_condition = entry_code.get('short', 'False')
    
    # 出场条件
    exit_code = spec.get('exit_conditions', {})
    long_exit = exit_code.get('long', 'False')
    short_exit = exit_code.get('short', 'False')
    
    # 生成代码
    code = f'''"""
{spec.get('description', name)} - 自动生成策略
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
    minimal_roi = {minimal_roi}
    
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
        
        # 做多条件
        long_condition = {long_condition}
        dataframe.loc[long_condition, 'enter_long'] = 1
        
        # 做空条件
        short_condition = {short_condition}
        dataframe.loc[short_condition, 'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        
        # 平多条件
        exit_long_condition = {long_exit}
        dataframe.loc[exit_long_condition, 'exit_long'] = 1
        
        # 平空条件
        exit_short_condition = {short_exit}
        dataframe.loc[exit_short_condition, 'exit_short'] = 1
        
        return dataframe
'''
    
    return code
