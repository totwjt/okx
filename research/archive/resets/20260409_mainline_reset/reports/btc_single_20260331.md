# BTC Single-Instrument Research

Date: 2026-03-31
Pair: `BTC/USDT:USDT`
Framework: `Freqtrade 2026.2`
Primary splits:
- Train: `2025-01-01` to `2025-09-30`
- Validation: `2025-10-01` to `2025-11-30`
- Test: `2025-12-01` to `2026-03-31 04:30:00`

## Method

- Used a single-pair workflow on `BTC/USDT:USDT`.
- Kept all strategies on `15m` execution timeframe.
- Limited research to price/trend/volatility inputs because `funding_rate` history only starts on `2025-12-24 08:00:00`, which does not cover the train or validation ranges.
- Optimized each strategy once on the train split with `MultiMetricHyperOptLoss`.
- Exported one final parameter set per strategy to its strategy JSON file.
- Ranked strategies by merged out-of-sample performance on `2025-10-01` to `2026-03-31`.

## Final Ranking

| Rank | Strategy | Final OOS Result | Trades | Max DD | Validation | Test |
| --- | --- | --- | ---: | ---: | --- | --- |
| 1 | `BTCRegimePullbackStrategy` | `+0.56%` (`+5.556 USDT`) | 3 | `0.07%` | `+0.52%`, 1 trade | `+0.03%`, 2 trades |
| 2 | `MultiLsV2Strategy` | `-1.63%` (`-16.264 USDT`) | 6 | `1.63%` | `-0.29%`, 1 trade | `-1.35%`, 5 trades |
| 3 | `BTCDonchianTrendStrategy` | `-3.17%` (`-31.735 USDT`) | 28 | `3.92%` | `-0.48%`, 10 trades | `-2.73%`, 18 trades |

## Train Optimization Snapshot

| Strategy | Train Result | Trades | Max DD | Notes |
| --- | --- | ---: | ---: | --- |
| `MultiLsV2Strategy` | `+0.20%` | 13 | `1.20%` | Improvement versus baseline, but OOS failed. |
| `BTCRegimePullbackStrategy` | `+0.24%` | 4 | `0.10%` | Low frequency, but OOS stayed positive. |
| `BTCDonchianTrendStrategy` | `+0.59%` | 15 | `1.36%` | Best train result, but OOS degraded sharply. |

## Interpretation

- `BTCRegimePullbackStrategy` is the only strategy that remained positive on both validation and test.
- `BTCRegimePullbackStrategy` also has very low trade count, so it should be treated as the best current lead, not as a statistically mature result.
- `MultiLsV2Strategy` improved on train after optimization, but still failed on both validation and test.
- `BTCDonchianTrendStrategy` looked strongest in train, then broke down out-of-sample, which suggests overfitting to the train regime.

## Final Parameter Files

- `strategies/auto_multi_ls_v2.json`
- `strategies/btc_regime_pullback_strategy.json`
- `strategies/btc_donchian_trend_strategy.json`

