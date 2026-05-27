import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies"))

from services.runtime_service import build_freqtrade_params


class RuntimeServiceTest(unittest.TestCase):
    def test_build_freqtrade_params_exports_all_generated_factor_params(self):
        spec = yaml.safe_load((ROOT / "strategies/spec/okx_sol_crash_rebound_v2.yaml").read_text())

        params = build_freqtrade_params("okx_sol_crash_rebound_v2", spec, "default")["params"]

        self.assertEqual(params["buy"]["ma_period"], 96)
        self.assertEqual(params["buy"]["rsi_period"], 14)
        self.assertEqual(params["buy"]["rsi_oversold"], 26)
        self.assertEqual(params["buy"]["bb_period"], 28)
        self.assertEqual(params["buy"]["bb_std"], 2.1)
        self.assertEqual(params["buy"]["volume_ma_period"], 24)
        self.assertEqual(params["buy"]["volume_ratio_threshold"], 1.2)
        self.assertEqual(params["buy"]["atr_period"], 14)
        self.assertEqual(params["buy"]["atr_entry_max"], 0.065)
        self.assertEqual(params["buy"]["zscore_period"], 48)
        self.assertEqual(params["buy"]["zscore_entry_abs"], 1.1)
        self.assertEqual(params["sell"]["atr_exit_max"], 0.08)
        self.assertEqual(params["sell"]["zscore_exit_abs"], 0.45)


if __name__ == "__main__":
    unittest.main()
