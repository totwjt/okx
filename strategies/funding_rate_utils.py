from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from pandas import DataFrame


FUNDING_RATE_BASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "external_data"
    / "funding_rates"
    / "okx"
)


def pair_to_okx_inst_id(pair: str) -> str:
    base_quote = pair.split(":")[0]
    return base_quote.replace("/", "-") + "-SWAP"


@lru_cache(maxsize=16)
def load_okx_funding_rate(inst_id: str) -> pd.DataFrame:
    path = FUNDING_RATE_BASE_DIR / f"{inst_id}.csv"
    if not path.exists():
        return pd.DataFrame(columns=["date", "funding_rate"])

    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        return pd.DataFrame(columns=["date", "funding_rate"])

    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["funding_rate"] = pd.to_numeric(df["funding_rate"], errors="coerce").fillna(0.0)
    return df[["date", "funding_rate"]].drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)


def merge_external_funding_rate(dataframe: DataFrame, pair: str) -> DataFrame:
    funding = load_okx_funding_rate(pair_to_okx_inst_id(pair))
    if funding.empty:
        dataframe["ext_funding_rate"] = 0.0
        return dataframe

    frame = dataframe.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    merged = pd.merge_asof(
        frame.sort_values("date"),
        funding,
        on="date",
        direction="backward",
    )
    merged["ext_funding_rate"] = merged["funding_rate"].fillna(0.0)
    return merged.drop(columns=["funding_rate"])
