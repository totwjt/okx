from __future__ import annotations

from typing import Any

from app.services.jobs_service import init_job_schema
from app.services.paper_service import _safe_api_get
from app.services.registry_service import get_strategy
from app.services.runtime_alignment_service import runtime_alignment
from app.services.system_check import _load_strategy_services


PROTECTED_STATUS_ORDER = {
    "validated": 1,
    "paper_active": 2,
    "live_candidate": 3,
    "live_active": 4,
}


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def run_evidence_check(
    strategy_slug: str,
    profile_name: str,
    target_status: str = "validated",
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_target = target_status if target_status in PROTECTED_STATUS_ORDER else "validated"
    gate = {
        "min_backtest_trades": 1,
        "min_validation_trades": 1,
        "min_profit_factor": 1.0,
        "max_drawdown": 0.30,
        "max_side_imbalance": 0.85,
        "max_exit_reason_concentration": 0.80,
        "min_paper_natural_trades": 10,
        **(thresholds or {}),
    }
    context = _load_gate_context(strategy_slug, profile_name)
    checks = [
        _validation_check(context, gate),
        _timerange_separation_check(context),
        _runtime_artifact_check(context),
        _train_backtest_check(context, gate),
        _test_backtest_check(context, gate, normalized_target),
        _test_reuse_check(context),
        _custom_evidence_check(context),
        _side_balance_check(context, gate),
        _exit_reason_check(context, gate),
        _data_gap_check(context),
        _thesis_check(context, normalized_target),
        _paper_sample_check(context, gate, normalized_target),
        _force_trade_check(context, normalized_target),
    ]
    required_checks = [check for check in checks if check["required"]]
    failed_checks = [check for check in required_checks if not check["passed"]]
    warnings = [check for check in checks if check["status"] == "warning"]

    return {
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "target_status": normalized_target,
        "passed": not failed_checks,
        "thresholds": gate,
        "checks": checks,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "summary_zh": "证据闸门通过" if not failed_checks else f"{len(failed_checks)} 项证据未通过",
    }


def _load_gate_context(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    db_service = _db_service()
    db_service.init_schema()
    init_job_schema()
    strategy = get_strategy(strategy_slug)
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select profile_name, status, is_active, overrides, validation
                from strategy_profiles
                where strategy_slug = %s and profile_name = %s
                """,
                (strategy_slug, profile_name),
            )
            profile = cur.fetchone()

            cur.execute(
                """
                select id, timerange, passed, metrics, gate, warnings, failed_checks, artifact_path, created_at
                from strategy_validation_results
                where strategy_slug = %s and profile_name = %s
                order by created_at desc, id desc
                limit 1
                """,
                (strategy_slug, profile_name),
            )
            validation = cur.fetchone()

            cur.execute(
                """
                select id, job_type, status, payload, result, error_summary, created_at, finished_at
                from web_jobs
                where job_type in ('backtest', 'validation')
                  and (
                    payload->>'strategy_slug' = %s
                    or result->>'strategy_slug' = %s
                  )
                  and (
                    payload->>'profile_name' = %s
                    or result->>'profile_name' = %s
                  )
                order by created_at desc, id desc
                limit 100
                """,
                (strategy_slug, strategy_slug, profile_name, profile_name),
            )
            jobs = list(cur.fetchall())

            cur.execute(
                """
                select artifact_type, artifact_path, artifact_hash, metadata, created_at
                from strategy_runtime_artifacts
                where strategy_slug = %s and profile_name = %s
                order by created_at desc, id desc
                limit 20
                """,
                (strategy_slug, profile_name),
            )
            artifacts = list(cur.fetchall())

    paper = _paper_context(strategy_slug, profile_name)
    alignment = runtime_alignment(strategy_slug, profile_name)
    return {
        "strategy": strategy,
        "profile": dict(profile) if profile else None,
        "validation": dict(validation) if validation else None,
        "jobs": jobs,
        "artifacts": artifacts,
        "alignment": alignment,
        "paper": paper,
    }


def _paper_context(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    trades_payload = _safe_api_get("trades?limit=200")
    trades = []
    if trades_payload.get("ok") and isinstance(trades_payload.get("data"), dict):
        trades = trades_payload["data"].get("trades", []) or []
    closed = [trade for trade in trades if not trade.get("is_open")]
    force = [trade for trade in closed if _is_force_trade(trade)]
    natural = [trade for trade in closed if not _is_force_trade(trade)]
    return {
        "ok": bool(trades_payload.get("ok")),
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "closed_trades": closed,
        "natural_closed_trades": natural,
        "force_trades": force,
        "error": trades_payload.get("error"),
    }


def _is_force_trade(trade: dict[str, Any]) -> bool:
    text = " ".join(
        str(trade.get(key) or "")
        for key in ("enter_tag", "exit_reason", "open_order_id", "close_order_id")
    ).lower()
    return "force" in text or "forced" in text


def _latest_phase_job(context: dict[str, Any], phase: str) -> dict[str, Any] | None:
    for job in context["jobs"]:
        payload = job.get("payload") or {}
        result = job.get("result") or {}
        if payload.get("phase") == phase or result.get("phase") == phase:
            return dict(job)
    return None


def _metrics(job_or_validation: dict[str, Any] | None) -> dict[str, Any]:
    if not job_or_validation:
        return {}
    result = job_or_validation.get("result") or job_or_validation
    return result.get("metrics") or {}


def _check(
    key: str,
    title_zh: str,
    passed: bool,
    details_zh: str,
    *,
    required: bool = True,
    status: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_status = status or ("passed" if passed else "failed")
    return {
        "key": key,
        "title_zh": title_zh,
        "passed": passed,
        "required": required,
        "status": resolved_status,
        "details_zh": details_zh,
        "evidence": evidence or {},
    }


def _validation_check(context: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    validation = context["validation"]
    if not validation:
        return _check("validation_evidence", "Validation 证据", False, "缺少 strategy_validation_results 记录。")
    metrics = _metrics(validation)
    failures = list(validation.get("failed_checks") or [])
    if not validation.get("passed"):
        return _check(
            "validation_evidence",
            "Validation 证据",
            False,
            "最新 validation gate 未通过：" + "；".join(failures or ["passed=false"]),
            evidence={"validation_id": validation["id"], "timerange": validation["timerange"]},
        )
    total_trades = int(metrics.get("total_trades") or 0)
    profit_factor = float(metrics.get("profit_factor") or 0)
    drawdown = float(metrics.get("max_drawdown_account") or 0)
    failed = []
    if total_trades < int(gate["min_validation_trades"]):
        failed.append(f"validation 交易数 {total_trades} < {gate['min_validation_trades']}")
    if profit_factor < float(gate["min_profit_factor"]):
        failed.append(f"利润因子 {profit_factor:.4f} < {gate['min_profit_factor']}")
    if drawdown > float(gate["max_drawdown"]):
        failed.append(f"最大回撤 {drawdown:.4f} > {gate['max_drawdown']}")
    return _check(
        "validation_evidence",
        "Validation 证据",
        not failed,
        "最新 validation 证据满足阈值。" if not failed else "；".join(failed),
        evidence={"validation_id": validation["id"], "metrics": metrics, "timerange": validation["timerange"]},
    )


def _timerange_separation_check(context: dict[str, Any]) -> dict[str, Any]:
    spec = (context.get("strategy") or {}).get("spec") or {}
    train = spec.get("train_timerange") or (spec.get("optimization") or {}).get("timerange")
    validation = spec.get("validation_timerange")
    test = spec.get("test_timerange")
    if not train or not validation or not test:
        return _check(
            "timerange_separation",
            "Train / Validation / Test 区间分离",
            False,
            "缺少 train、validation 或 test timerange 声明，无法证明数据用途分离。",
            evidence={"train": train, "validation": validation, "test": test},
        )
    unique = len({str(train), str(validation), str(test)}) == 3
    return _check(
        "timerange_separation",
        "Train / Validation / Test 区间分离",
        unique,
        "三个数据用途区间声明互不相同。" if unique else "train、validation、test 存在重复区间。",
        evidence={"train": train, "validation": validation, "test": test},
    )


def _runtime_artifact_check(context: dict[str, Any]) -> dict[str, Any]:
    alignment = context.get("alignment") or {}
    if alignment:
        return _check(
            "runtime_artifact_alignment",
            "Runtime Artifact 对齐",
            bool(alignment.get("ok")),
            alignment.get("summary_zh") or "runtime alignment 状态未知",
            evidence={
                "status": alignment.get("status"),
                "blocked_reasons": alignment.get("blocked_reasons"),
            },
        )
    types = {row["artifact_type"] for row in context["artifacts"]}
    missing = []
    if "freqtrade_strategy_py" not in types:
        missing.append("缺少策略 runtime artifact")
    if "freqtrade_params_json" not in types:
        missing.append("缺少参数 runtime artifact")
    return _check(
        "runtime_artifact_alignment",
        "Runtime Artifact 对齐",
        not missing,
        "runtime artifact 元数据完整。" if not missing else "；".join(missing),
        evidence={"artifact_types": sorted(types)},
    )


def _train_backtest_check(context: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    job = _latest_phase_job(context, "train")
    if not job:
        return _check("train_backtest", "Train 回测样本", False, "缺少 train 阶段回测任务。")
    metrics = _metrics(job)
    trades = int(metrics.get("total_trades") or 0)
    passed = job["status"] == "success" and trades >= int(gate["min_backtest_trades"])
    return _check(
        "train_backtest",
        "Train 回测样本",
        passed,
        "train 回测样本满足最低交易数。" if passed else f"train 回测未成功或交易数 {trades} 不足。",
        evidence={"job_id": job["id"], "status": job["status"], "metrics": metrics},
    )


def _test_backtest_check(context: dict[str, Any], gate: dict[str, Any], target_status: str) -> dict[str, Any]:
    required = PROTECTED_STATUS_ORDER[target_status] >= PROTECTED_STATUS_ORDER["paper_active"]
    job = _latest_phase_job(context, "test")
    if not job:
        return _check("test_backtest", "Test 留出测试", not required, "缺少 test 阶段回测任务。", required=required)
    metrics = _metrics(job)
    trades = int(metrics.get("total_trades") or 0)
    passed = job["status"] == "success" and trades >= int(gate["min_backtest_trades"])
    return _check(
        "test_backtest",
        "Test 留出测试",
        passed or not required,
        "test 留出测试满足最低交易数。" if passed else f"test 回测未成功或交易数 {trades} 不足。",
        required=required,
        evidence={"job_id": job["id"], "status": job["status"], "metrics": metrics},
    )


def _test_reuse_check(context: dict[str, Any]) -> dict[str, Any]:
    test_jobs = [job for job in context["jobs"] if (job.get("payload") or {}).get("phase") == "test" or (job.get("result") or {}).get("phase") == "test"]
    if len(test_jobs) <= 1:
        return _check(
            "test_reuse",
            "Test 留出集污染提示",
            True,
            "test 留出集尚未被反复使用。",
            required=False,
            status="warning" if len(test_jobs) == 1 else "passed",
            evidence={"test_job_count": len(test_jobs)},
        )
    return _check(
        "test_reuse",
        "Test 留出集污染提示",
        True,
        f"当前 profile 已有 {len(test_jobs)} 次 test 记录，避免据此反复调参。",
        required=False,
        status="warning",
        evidence={"test_job_count": len(test_jobs)},
    )


def _custom_evidence_check(context: dict[str, Any]) -> dict[str, Any]:
    custom_jobs = [job for job in context["jobs"] if (job.get("payload") or {}).get("phase") == "custom" or (job.get("result") or {}).get("phase") == "custom"]
    return _check(
        "custom_not_promotion_evidence",
        "Custom 诊断结果",
        True,
        "custom 结果仅用于诊断，默认不作为 promotion evidence。"
        if custom_jobs
        else "没有 custom 诊断结果参与晋级证据。",
        required=False,
        status="warning" if custom_jobs else "passed",
        evidence={"custom_job_count": len(custom_jobs)},
    )


def _side_balance_check(context: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    validation = context["validation"]
    metrics = _metrics(validation)
    long_count = metrics.get("long_trades") or metrics.get("long_count")
    short_count = metrics.get("short_trades") or metrics.get("short_count")
    if long_count is None or short_count is None:
        return _check(
            "side_balance",
            "Long / Short 均衡",
            True,
            "当前 metrics 缺少 long/short 拆分，先作为 warning 展示。",
            required=False,
            status="warning",
            evidence={"available_metric_keys": sorted(metrics.keys())},
        )
    total = int(long_count) + int(short_count)
    dominant = max(int(long_count), int(short_count)) / total if total else 1
    passed = dominant <= float(gate["max_side_imbalance"])
    return _check(
        "side_balance",
        "Long / Short 均衡",
        passed,
        "多空交易分布未严重失衡。" if passed else f"单侧交易占比 {dominant:.2%} 超过阈值。",
        evidence={"long_trades": long_count, "short_trades": short_count, "dominant_ratio": dominant},
    )


def _exit_reason_check(context: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    validation = context["validation"]
    metrics = _metrics(validation)
    reasons = metrics.get("exit_reasons") or metrics.get("exit_reason_counts")
    if not isinstance(reasons, dict) or not reasons:
        return _check(
            "exit_reason_concentration",
            "退出原因集中度",
            True,
            "当前 metrics 缺少 exit reason 分布，先作为 warning 展示。",
            required=False,
            status="warning",
            evidence={"available_metric_keys": sorted(metrics.keys())},
        )
    total = sum(int(value or 0) for value in reasons.values())
    dominant = max(int(value or 0) for value in reasons.values()) / total if total else 1
    passed = dominant <= float(gate["max_exit_reason_concentration"])
    return _check(
        "exit_reason_concentration",
        "退出原因集中度",
        passed,
        "退出原因没有过度集中。" if passed else f"最大退出原因占比 {dominant:.2%} 超过阈值。",
        evidence={"exit_reasons": reasons, "dominant_ratio": dominant},
    )


def _data_gap_check(context: dict[str, Any]) -> dict[str, Any]:
    return _check(
        "data_gap",
        "数据缺口",
        True,
        "第一版 evidence gate 不直接扫描全量数据缺口；请结合因子数据页复核。",
        required=False,
        status="warning",
    )


def _thesis_check(context: dict[str, Any], target_status: str) -> dict[str, Any]:
    required = PROTECTED_STATUS_ORDER[target_status] >= PROTECTED_STATUS_ORDER["live_candidate"]
    validation = (context.get("profile") or {}).get("validation") or {}
    thesis = validation.get("thesis") if isinstance(validation, dict) else {}
    required_keys = {
        "one_liner": "策略一句话描述",
        "return_source": "收益来源假设",
        "suitable_market": "适用市场状态",
        "unsuitable_market": "不适用市场状态",
        "invalidation": "失效条件",
        "observed_metrics": "观察指标",
        "review_conclusion": "复盘结论",
        "next_action": "下一步动作",
    }
    missing = [
        label
        for key, label in required_keys.items()
        if not isinstance(thesis, dict) or not str(thesis.get(key) or "").strip()
    ]
    return _check(
        "strategy_thesis",
        "策略假设与复盘记录",
        not missing or not required,
        "thesis 完整。" if not missing else "缺少 thesis 字段：" + "、".join(missing),
        required=required,
        evidence={"missing_fields": missing},
    )


def _paper_sample_check(context: dict[str, Any], gate: dict[str, Any], target_status: str) -> dict[str, Any]:
    required = PROTECTED_STATUS_ORDER[target_status] >= PROTECTED_STATUS_ORDER["live_candidate"]
    natural = len(context["paper"]["natural_closed_trades"])
    passed = natural >= int(gate["min_paper_natural_trades"])
    return _check(
        "paper_natural_samples",
        "Paper 自然成交样本",
        passed or not required,
        "paper 自然成交样本满足阈值。" if passed else f"自然成交样本 {natural} < {gate['min_paper_natural_trades']}，需要 COLLECT_MORE_SAMPLES。",
        required=required,
        evidence={"natural_closed_trades": natural, "paper_api_ok": context["paper"]["ok"]},
    )


def _force_trade_check(context: dict[str, Any], target_status: str) -> dict[str, Any]:
    required = PROTECTED_STATUS_ORDER[target_status] >= PROTECTED_STATUS_ORDER["live_candidate"]
    force = len(context["paper"]["force_trades"])
    passed = force == 0
    return _check(
        "force_trade_contamination",
        "Force 交易污染",
        passed or not required,
        "paper 样本未发现 force-enter / force-exit。" if passed else f"发现 {force} 笔疑似 force 交易，不能作为 live_candidate 证据。",
        required=required,
        evidence={"force_trades": force},
    )
