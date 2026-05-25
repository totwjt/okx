from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.services.jobs_service import init_job_schema
from app.services.registry_service import list_strategy_profiles
from app.services.system_check import _load_strategy_services


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def optimization_assistant(strategy_slug: str, baseline_profile: str | None = None) -> dict[str, Any]:
    db_service = _db_service()
    spec, baseline = db_service.load_strategy_bundle(strategy_slug, baseline_profile)
    profiles = list_strategy_profiles(strategy_slug) or []
    jobs = _profile_jobs(strategy_slug)
    parameters = _extract_parameters(spec)
    candidates = [
        _candidate_summary(profile, baseline, parameters, jobs)
        for profile in profiles
    ]
    candidates.sort(key=lambda row: row["score"], reverse=True)
    return {
        "strategy_slug": strategy_slug,
        "baseline_profile": baseline["profile_name"],
        "parameters": parameters,
        "candidates": candidates,
        "scoring_zh": [
            "综合评分同时考虑收益、回撤、利润因子、交易数、胜率和 train-to-validation 衰减。",
            "低交易数、高回撤、参数贴边和 validation 衰减都会被标记，不能只按收益排序。",
        ],
    }


def save_draft_profile(
    strategy_slug: str,
    profile_name: str,
    baseline_profile: str | None,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    if not profile_name.strip():
        raise RuntimeError("profile_name is required")
    db_service = _db_service()
    _spec, baseline = db_service.load_strategy_bundle(strategy_slug, baseline_profile)
    merged = deepcopy(baseline.get("overrides") or {})
    _deep_merge(merged, overrides)
    profile = {
        "profile_name": profile_name,
        "status": "draft",
        "source": f"web_optimization:{baseline['profile_name']}",
        "overrides": merged,
        "validation": {
            "optimization_note": "Draft profile saved from lifecycle optimization assistant.",
        },
    }
    db_service.upsert_profile(strategy_slug, profile, is_active=False)
    return {"saved": True, "strategy_slug": strategy_slug, "profile_name": profile_name, "profile": profile}


def auto_tune_strategy(
    strategy_slug: str,
    baseline_profile: str | None = None,
    candidate_count: int = 3,
    run_backtests: bool = True,
) -> dict[str, Any]:
    count = max(3, min(int(candidate_count or 3), 12))
    db_service = _db_service()
    spec, baseline = db_service.load_strategy_bundle(strategy_slug, baseline_profile)
    parameters = _extract_parameters(spec)
    if not parameters:
        raise RuntimeError("no tunable parameters found in strategy spec")
    timerange = spec.get("train_timerange") or (spec.get("optimization") or {}).get("timerange")
    if not timerange:
        raise RuntimeError("train timerange is required for auto tuning")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    candidates = []
    for index in range(count):
        overrides = _candidate_overrides(parameters, index, count)
        profile_name = f"{baseline['profile_name']}_auto_{stamp}_{index + 1}"
        saved = save_draft_profile(strategy_slug, profile_name, baseline["profile_name"], overrides)
        candidates.append(
            {
                "profile_name": profile_name,
                "overrides": overrides,
                "diff": _diff_dict(baseline.get("overrides") or {}, saved["profile"]["overrides"]),
                "warnings_zh": ["自动调优候选，仅进入候选池，不自动晋级。"],
            }
        )

    backtest_jobs = []
    if run_backtests:
        from app.services.jobs_service import create_job, start_job_process

        for candidate in candidates:
            job = create_job(
                "backtest",
                {
                    "strategy_slug": strategy_slug,
                    "profile_name": candidate["profile_name"],
                    "phase": "train",
                    "timerange": timerange,
                },
            )
            start_job_process(int(job["id"]))
            backtest_jobs.append(job)

    return {
        "strategy_slug": strategy_slug,
        "baseline_profile": baseline["profile_name"],
        "timerange": timerange,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "backtest_jobs": backtest_jobs,
        "auto_promoted": False,
    }


def _profile_jobs(strategy_slug: str) -> dict[str, dict[str, Any]]:
    init_job_schema()
    db_service = _db_service()
    rows: dict[str, dict[str, Any]] = {}
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, job_type, status, payload, result, created_at, finished_at
                from web_jobs
                where job_type in ('backtest', 'validation')
                  and (
                    payload->>'strategy_slug' = %s
                    or result->>'strategy_slug' = %s
                  )
                order by created_at desc, id desc
                limit 200
                """,
                (strategy_slug, strategy_slug),
            )
            for row in cur.fetchall():
                result = row.get("result") or {}
                payload = row.get("payload") or {}
                profile = result.get("profile_name") or payload.get("profile_name")
                phase = result.get("phase") or payload.get("phase") or ("validation" if row["job_type"] == "validation" else None)
                if not profile or not phase:
                    continue
                rows.setdefault(profile, {})
                rows[profile].setdefault(phase, dict(row))
    return rows


def _candidate_overrides(
    parameters: list[dict[str, Any]],
    index: int,
    count: int,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    ratio = (index + 1) / (count + 1)
    for param in parameters[:10]:
        lower = float(param["min"])
        upper = float(param["max"])
        current = float(param["current"])
        span = upper - lower
        wave = (ratio - 0.5) * 0.7
        proposed = max(lower, min(upper, current + span * wave))
        if isinstance(param["current"], int):
            proposed_value: Any = int(round(proposed))
        else:
            proposed_value = round(proposed, 6)
        _set_path(overrides, param["path"], proposed_value)
    return overrides


def _extract_parameters(spec: dict[str, Any]) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    factors = spec.get("factors") or {}
    for factor_name, factor in factors.items():
        if not isinstance(factor, dict):
            continue
        for key, value in factor.items():
            bounds = None
            if key.endswith("range") and isinstance(value, list) and len(value) == 2:
                continue
            range_key = f"{key}_range"
            if isinstance(factor.get(range_key), list) and len(factor[range_key]) == 2:
                bounds = factor[range_key]
            elif key == "period" and isinstance(factor.get("range"), list) and len(factor["range"]) == 2:
                bounds = factor["range"]
            elif key == "std" and isinstance(factor.get("std_range"), list) and len(factor["std_range"]) == 2:
                bounds = factor["std_range"]
            if bounds and isinstance(value, (int, float)):
                params.append(
                    {
                        "path": f"factors.{factor_name}.{key}",
                        "title_zh": f"{factor_name}.{key}",
                        "current": value,
                        "min": bounds[0],
                        "max": bounds[1],
                        "source": "strategy_specs.spec.factors",
                    }
                )
    for key, bounds in {
        "stoploss": [-0.2, -0.01],
        "trailing_stop_positive": [0.001, 0.05],
        "trailing_stop_positive_offset": [0.002, 0.08],
    }.items():
        if isinstance(spec.get(key), (int, float)):
            params.append(
                {
                    "path": key,
                    "title_zh": key,
                    "current": spec[key],
                    "min": bounds[0],
                    "max": bounds[1],
                    "source": "strategy_specs.spec",
                }
            )
    return params


def _candidate_summary(
    profile: dict[str, Any],
    baseline: dict[str, Any],
    parameters: list[dict[str, Any]],
    jobs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    profile_name = profile["profile_name"]
    diff = _diff_dict(baseline.get("overrides") or {}, profile.get("overrides") or {})
    train_job = jobs.get(profile_name, {}).get("train")
    validation_job = jobs.get(profile_name, {}).get("validation")
    train_metrics = _metrics(train_job)
    validation_metrics = _metrics(validation_job)
    score, reasons, warnings = _score_candidate(train_metrics, validation_metrics, profile, parameters)
    return {
        "profile_name": profile_name,
        "status": profile["status"],
        "is_active": profile["is_active"],
        "diff": diff,
        "train_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "score": score,
        "reasons_zh": reasons,
        "warnings_zh": warnings,
    }


def _score_candidate(
    train: dict[str, Any],
    validation: dict[str, Any],
    profile: dict[str, Any],
    parameters: list[dict[str, Any]],
) -> tuple[float, list[str], list[str]]:
    trades = float(train.get("total_trades") or 0)
    profit = float(train.get("profit_total") or 0)
    drawdown = float(train.get("max_drawdown_account") or 0)
    profit_factor = float(train.get("profit_factor") or 0)
    winrate = float(train.get("winrate") or 0)
    score = profit * 120 + min(profit_factor, 3.0) * 15 + winrate * 20 + min(trades, 80) * 0.4 - drawdown * 120
    reasons = [
        f"收益贡献 {profit:.4f}，利润因子 {profit_factor:.2f}，胜率 {winrate:.2%}。",
        f"回撤惩罚 {drawdown:.2%}，交易数 {int(trades)}。",
    ]
    warnings: list[str] = []
    if trades < 10:
        warnings.append("低交易数候选，样本不足，不能仅凭收益判断。")
        score -= 25
    if drawdown > 0.20:
        warnings.append("最大回撤偏高，需要降低风险权重或扩大验证。")
        score -= 20
    validation_profit = validation.get("profit_total")
    if validation_profit is not None and profit > 0:
        decay = 1 - (float(validation_profit) / profit)
        if decay > 0.5:
            warnings.append(f"train-to-validation 衰减 {decay:.2%}，疑似过拟合。")
            score -= 20
    extreme = _extreme_parameters(profile.get("overrides") or {}, parameters)
    if extreme:
        warnings.append("参数贴近边界：" + "、".join(extreme[:4]))
        score -= min(len(extreme) * 5, 20)
    if not train:
        warnings.append("缺少 train 回测指标，评分仅按风险提示保守处理。")
        score = min(score, 0)
    return round(score, 2), reasons, warnings


def _metrics(job: dict[str, Any] | None) -> dict[str, Any]:
    if not job or job.get("status") != "success":
        return {}
    result = job.get("result") or {}
    return dict(result.get("metrics") or {})


def _diff_dict(left: dict[str, Any], right: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    rows = []
    keys = sorted(set(left.keys()) | set(right.keys()))
    for key in keys:
        path = f"{prefix}.{key}" if prefix else key
        a = left.get(key)
        b = right.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            rows.extend(_diff_dict(a, b, path))
        elif a != b:
            rows.append({"path": path, "baseline": a, "candidate": b})
    return rows


def _extreme_parameters(overrides: dict[str, Any], parameters: list[dict[str, Any]]) -> list[str]:
    extreme = []
    for param in parameters:
        value = _get_path(overrides, param["path"])
        if not isinstance(value, (int, float)):
            continue
        lower = float(param["min"])
        upper = float(param["max"])
        if upper == lower:
            continue
        ratio = (float(value) - lower) / (upper - lower)
        if ratio <= 0.08 or ratio >= 0.92:
            extreme.append(param["path"])
    return extreme


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    current = data
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
