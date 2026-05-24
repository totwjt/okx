from __future__ import annotations

import json
import subprocess
from typing import Any

from app.services.system_check import PROJECT_ROOT


SCAN_SCRIPT = r"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path("/freqtrade/user_data/data/okx/futures")
EXTERNAL_FUNDING_DIR = Path("/freqtrade/user_data/external_data/funding_rates/okx")
FILE_RE = re.compile(r"^(?P<pair>.+)-(?P<timeframe>[^-]+)-(?P<kind>futures|mark|funding_rate)\.feather$")


def pair_label(raw: str) -> str:
    parts = raw.split("_")
    if len(parts) >= 3:
        return f"{parts[0]}/{parts[1]}:{parts[2]}"
    return raw


def expected_delta(timeframe: str, kind: str) -> pd.Timedelta:
    if kind == "funding_rate":
        return pd.Timedelta(hours=8)
    unit = timeframe[-1:]
    value = int(timeframe[:-1])
    if unit == "m":
        return pd.Timedelta(minutes=value)
    if unit == "h":
        return pd.Timedelta(hours=value)
    if unit == "d":
        return pd.Timedelta(days=value)
    return pd.Timedelta(0)


def iso(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def scan_gaps(dates: pd.Series, delta: pd.Timedelta) -> dict:
    if len(dates) < 2 or delta <= pd.Timedelta(0):
        return {"gap_count": 0, "missing_intervals": 0, "max_gap_seconds": 0, "samples": []}
    ordered = pd.to_datetime(dates, utc=True).dropna().drop_duplicates().sort_values()
    diffs = ordered.diff().dropna()
    gap_mask = diffs > delta
    gap_count = int(gap_mask.sum())
    missing = 0
    samples = []
    max_gap_seconds = 0
    for idx, gap in diffs[gap_mask].items():
        missing_here = max(int(gap / delta) - 1, 0)
        missing += missing_here
        max_gap_seconds = max(max_gap_seconds, int(gap.total_seconds()))
        if len(samples) < 5:
            pos = ordered.index.get_loc(idx)
            prev_value = ordered.iloc[pos - 1] if pos > 0 else None
            samples.append(
                {
                    "from": iso(prev_value),
                    "to": iso(ordered.loc[idx]),
                    "gap_seconds": int(gap.total_seconds()),
                    "missing_intervals": missing_here,
                }
            )
    return {
        "gap_count": gap_count,
        "missing_intervals": missing,
        "max_gap_seconds": max_gap_seconds,
        "samples": samples,
    }


def scan_feather(path: Path) -> dict:
    match = FILE_RE.match(path.name)
    if not match:
        return {"file": str(path), "filename": path.name, "kind": "unknown", "ok": False, "error": "unrecognized filename"}
    meta = match.groupdict()
    try:
        df = pd.read_feather(path, columns=["date"])
        dates = pd.to_datetime(df["date"], utc=True).dropna().drop_duplicates().sort_values()
        delta = expected_delta(meta["timeframe"], meta["kind"])
        gaps = scan_gaps(dates, delta)
        return {
            "ok": True,
            "source": "freqtrade_feather",
            "file": str(path),
            "filename": path.name,
            "pair_key": meta["pair"],
            "pair": pair_label(meta["pair"]),
            "timeframe": meta["timeframe"],
            "kind": meta["kind"],
            "rows": int(len(df)),
            "unique_timestamps": int(len(dates)),
            "start": iso(dates.iloc[0]) if len(dates) else None,
            "end": iso(dates.iloc[-1]) if len(dates) else None,
            "expected_interval_seconds": int(delta.total_seconds()) if delta > pd.Timedelta(0) else None,
            **gaps,
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": "freqtrade_feather",
            "file": str(path),
            "filename": path.name,
            "pair_key": meta["pair"],
            "pair": pair_label(meta["pair"]),
            "timeframe": meta["timeframe"],
            "kind": meta["kind"],
            "error": str(exc),
        }


def scan_external_csv(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        dates = pd.to_datetime([row.get("date") for row in rows], utc=True, errors="coerce")
        dates = pd.Series(dates).dropna().drop_duplicates().sort_values()
        delta = pd.Timedelta(hours=8)
        gaps = scan_gaps(dates, delta)
        inst_id = path.stem
        return {
            "ok": True,
            "source": "external_csv",
            "file": str(path),
            "filename": path.name,
            "pair_key": inst_id,
            "pair": inst_id.replace("-SWAP", "").replace("-", "/") + ":USDT",
            "timeframe": "8h",
            "kind": "funding_rate",
            "rows": len(rows),
            "unique_timestamps": int(len(dates)),
            "start": iso(dates.iloc[0]) if len(dates) else None,
            "end": iso(dates.iloc[-1]) if len(dates) else None,
            "expected_interval_seconds": int(delta.total_seconds()),
            **gaps,
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": "external_csv",
            "file": str(path),
            "filename": path.name,
            "kind": "funding_rate",
            "error": str(exc),
        }


datasets = []
for path in sorted(DATA_DIR.glob("*.feather")):
    datasets.append(scan_feather(path))
for path in sorted(EXTERNAL_FUNDING_DIR.glob("*.csv")):
    datasets.append(scan_external_csv(path))

coverage = {"ohlcv": [], "funding": []}
for row in datasets:
    if row.get("kind") == "funding_rate":
        coverage["funding"].append(row)
    elif row.get("kind") in {"futures", "mark"}:
        coverage["ohlcv"].append(row)

summary = {
    "dataset_count": len(datasets),
    "ohlcv_count": len(coverage["ohlcv"]),
    "funding_count": len(coverage["funding"]),
    "gap_dataset_count": sum(1 for row in datasets if row.get("gap_count", 0) > 0),
    "error_count": sum(1 for row in datasets if not row.get("ok")),
}

print(json.dumps({"ok": True, "summary": summary, "coverage": coverage}, ensure_ascii=False))
"""


def factors_health() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "exec", "-i", "freqtrade", "python", "-c", SCAN_SCRIPT],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "summary": {}, "coverage": {"ohlcv": [], "funding": []}, "error": str(exc)}

    if result.returncode != 0:
        return {
            "ok": False,
            "summary": {},
            "coverage": {"ohlcv": [], "funding": []},
            "error": result.stderr.strip() or result.stdout.strip(),
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "summary": {},
            "coverage": {"ohlcv": [], "funding": []},
            "error": f"failed to parse factor scan output: {exc}",
            "raw": result.stdout[-1000:],
        }
