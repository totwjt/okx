from __future__ import annotations

from typing import Any

from psycopg2.extras import Json

from app.services.evidence_gate_service import run_evidence_check
from app.services.jobs_service import create_job, init_job_schema, start_job_process
from app.services.paper_run_service import current_paper_run
from app.services.registry_service import get_strategy, list_strategies, list_strategy_profiles
from app.services.runtime_alignment_service import runtime_alignment
from app.services.system_check import _load_strategy_services


LIFECYCLE_STATUS_ORDER = [
    "draft",
    "generated",
    "backtested",
    "validated",
    "paper_active",
    "live_candidate",
    "live_active",
    "archived",
]

STATUS_DEFINITIONS = {
    "draft": {
        "title_zh": "草稿",
        "description_zh": "策略或参数档案仍在假设和定义阶段，不能作为运行候选。",
        "related_content_zh": "关联 strategy_specs、strategy_profiles，以及原始 spec/profile 导入来源。",
    },
    "generated": {
        "title_zh": "已生成",
        "description_zh": "已具备生成 Freqtrade runtime 运行文件的条件，或已生成运行产物记录。",
        "related_content_zh": "关联 strategy_runtime_artifacts 中的 runtime 策略文件和参数文件 hash。",
    },
    "backtested": {
        "title_zh": "已回测",
        "description_zh": "已完成至少一次 train、validation、test 或 custom 回测任务。",
        "related_content_zh": "关联 web_jobs.backtest 任务结果和 backtest artifact 路径。",
    },
    "validated": {
        "title_zh": "已验证",
        "description_zh": "已通过 validation gate，可进入模拟盘候选讨论。",
        "related_content_zh": "关联 strategy_validation_results、profile.validation 和 promotion event。",
    },
    "paper_active": {
        "title_zh": "模拟盘生效",
        "description_zh": "当前 profile 已作为 dry-run 模拟盘运行配置生效。",
        "related_content_zh": "关联 active profile、runtime artifact、Freqtrade dry_run 运行摘要和风险摘要。",
    },
    "live_candidate": {
        "title_zh": "实盘候选",
        "description_zh": "模拟盘证据满足要求，进入实盘前候选复核阶段。",
        "related_content_zh": "关联 paper evidence、risk summary、promotion event 和人工审批记录。",
    },
    "live_active": {
        "title_zh": "实盘生效",
        "description_zh": "当前 profile 已被声明为实盘生效配置，必须唯一且可审计回滚。",
        "related_content_zh": "关联 live promotion event、runtime alignment、风险检查和回滚记录。",
    },
    "archived": {
        "title_zh": "已归档",
        "description_zh": "策略或 profile 不再参与生成和运行，仅保留历史证据。",
        "related_content_zh": "关联历史 promotion event、validation/backtest 结果和归档原因。",
    },
}

STEP_TEMPLATES = [
    {
        "key": "hypothesis",
        "title_zh": "策略假设",
        "description_zh": "确认策略名称、说明、交易假设和适用市场已经进入注册表。",
        "required": True,
        "inputs": ["策略想法", "策略名称", "中文说明"],
        "outputs": ["strategy_specs 基础记录"],
    },
    {
        "key": "definition",
        "title_zh": "策略定义",
        "description_zh": "确认 spec JSON 已登记，并能定位指标、入场、出场和风控定义摘要。",
        "required": True,
        "inputs": ["strategies/spec/*.yaml 导入结果", "strategy_specs.spec"],
        "outputs": ["数据库中的策略定义摘要"],
    },
    {
        "key": "profile",
        "title_zh": "参数档案",
        "description_zh": "确认 profile 存在，记录状态、来源、覆盖参数和验证摘要。",
        "required": True,
        "inputs": ["strategies/profiles/<strategy>/*.yaml 导入结果", "profile overrides"],
        "outputs": ["strategy_profiles 记录"],
    },
    {
        "key": "runtime_artifact",
        "title_zh": "生成运行产物",
        "description_zh": "确认已 materialize 出 Freqtrade runtime 策略文件和参数文件元数据。",
        "required": True,
        "inputs": ["strategy_specs", "strategy_profiles", "registry materialize"],
        "outputs": ["strategy_runtime_artifacts hash 与路径"],
    },
    {
        "key": "train",
        "title_zh": "train 调优",
        "description_zh": "确认已有 train 阶段回测证据，避免直接用 validation/test 调参。",
        "required": True,
        "inputs": ["train timerange", "runtime artifact"],
        "outputs": ["web_jobs.backtest train 结果"],
    },
    {
        "key": "validation",
        "title_zh": "validation 验证",
        "description_zh": "确认固定验证区间和 validation gate 结果可回查。",
        "required": True,
        "inputs": ["validation timerange", "gate 阈值", "backtest metrics"],
        "outputs": ["strategy_validation_results", "profile.validation.last_result"],
    },
    {
        "key": "test",
        "title_zh": "test 留出测试",
        "description_zh": "确认留出测试集只用于最终复核，不用于调参。",
        "required": True,
        "inputs": ["test timerange", "已通过 validation 的 profile"],
        "outputs": ["web_jobs.backtest test 结果"],
    },
    {
        "key": "paper",
        "title_zh": "paper 模拟盘",
        "description_zh": "确认 profile 已进入模拟盘状态，并可关联 dry-run 运行证据。",
        "required": True,
        "inputs": ["validated profile", "runtime artifact", "dry_run Freqtrade"],
        "outputs": ["paper_active profile", "模拟盘运行摘要"],
    },
    {
        "key": "live_candidate",
        "title_zh": "live_candidate 实盘候选",
        "description_zh": "确认模拟盘证据和风险复核足以进入实盘候选。",
        "required": True,
        "inputs": ["paper evidence", "risk summary", "人工晋级理由"],
        "outputs": ["live_candidate promotion event"],
    },
    {
        "key": "live_active",
        "title_zh": "live_active 实盘生效",
        "description_zh": "确认实盘配置唯一生效，并保留审计和回滚依据。",
        "required": True,
        "inputs": ["live_candidate profile", "risk approval", "runtime alignment"],
        "outputs": ["live_active profile", "promotion event"],
    },
    {
        "key": "archived",
        "title_zh": "archived 归档",
        "description_zh": "确认不再运行的 profile 有归档状态或仍保留可追溯历史。",
        "required": False,
        "inputs": ["归档原因", "历史证据"],
        "outputs": ["archived profile 或历史保留记录"],
    },
]

THESIS_FIELDS = {
    "one_liner": "策略一句话描述",
    "return_source": "收益来源假设",
    "suitable_market": "适用市场状态",
    "unsuitable_market": "不适用市场状态",
    "invalidation": "失效条件",
    "observed_metrics": "观察指标",
    "review_conclusion": "复盘结论",
    "next_action": "下一步动作",
}


def _db_service() -> Any:
    db_service, _runtime_service = _load_strategy_services()
    return db_service


def lifecycle_strategies() -> list[dict[str, Any]]:
    return list_strategies()


def strategy_lifecycle(strategy_slug: str) -> dict[str, Any] | None:
    strategy = get_strategy(strategy_slug)
    if not strategy:
        return None
    profiles = list_strategy_profiles(strategy_slug) or []
    default_profile = next((profile for profile in profiles if profile.get("is_active")), None)
    if default_profile is None and profiles:
        default_profile = profiles[0]
    return {
        "strategy": strategy,
        "profiles": profiles,
        "default_profile_name": default_profile.get("profile_name") if default_profile else None,
        "status_definitions": STATUS_DEFINITIONS,
    }


def profile_lifecycle(strategy_slug: str, profile_name: str) -> dict[str, Any] | None:
    strategy = get_strategy(strategy_slug)
    profiles = list_strategy_profiles(strategy_slug)
    if not strategy or profiles is None:
        return None
    profile = next((row for row in profiles if row["profile_name"] == profile_name), None)
    if not profile:
        return None

    paper_run = current_paper_run(strategy_slug, profile_name)
    context = {
        **_load_profile_context(strategy_slug, profile_name),
        "paper_run": paper_run,
    }
    steps = _build_steps(strategy, profile, context)
    alignment = runtime_alignment(strategy_slug, profile_name)
    thesis = _profile_thesis(profile)
    current_step = next((step for step in steps if step["status"] in {"blocked", "pending"}), steps[-1])
    blocked_reasons = [reason for step in steps for reason in step["blocked_reasons"] if step["status"] == "blocked"]
    blocked_reasons.extend(alignment.get("blocked_reasons") or [])
    next_actions = [action for step in steps for action in step["next_actions"] if step["status"] in {"blocked", "pending"}]
    completed_count = sum(1 for step in steps if step["status"] == "completed")

    return {
        "strategy": strategy,
        "profile": profile,
        "status_definitions": STATUS_DEFINITIONS,
        "summary": {
            "current_status": profile["status"],
            "current_status_zh": STATUS_DEFINITIONS.get(profile["status"], {}).get("title_zh", profile["status"]),
            "current_step_key": current_step["key"],
            "current_step_title_zh": current_step["title_zh"],
            "completed_steps": completed_count,
            "total_steps": len(steps),
            "blocked_reasons": blocked_reasons[:8],
            "next_actions": next_actions[:8],
        },
        "assistant_plan": _assistant_plan(current_step["key"], strategy, profile, context),
        "alignment": alignment,
        "paper_run": paper_run,
        "thesis": thesis,
        "thesis_required_fields": THESIS_FIELDS,
        "promotion_events": context["promotions"][:8],
        "steps": steps,
    }


def advance_profile(
    strategy_slug: str,
    profile_name: str,
    *,
    candidate_count: int = 3,
) -> dict[str, Any]:
    lifecycle = profile_lifecycle(strategy_slug, profile_name)
    if not lifecycle:
        raise RuntimeError(f"profile lifecycle not found: {strategy_slug}/{profile_name}")
    step_key = lifecycle["summary"]["current_step_key"]
    jobs: list[dict[str, Any]] = []
    notes: list[str] = []

    if step_key in {"hypothesis", "definition", "profile"}:
        return {
            "advanced": False,
            "step_key": step_key,
            "jobs": jobs,
            "notes_zh": [
                "当前步骤需要补充策略假设、spec 或参数档案内容。",
                "建议在 Codex 终端对话中让 AI 生成 spec/profile 草稿，再从工作台刷新。",
            ],
        }
    if step_key == "runtime_artifact":
        job = create_job("materialize", {"strategy_slug": strategy_slug, "profile_name": profile_name})
        if not job.get("deduped"):
            start_job_process(int(job["id"]))
        jobs.append(job)
        notes.append("已创建运行产物生成任务；完成后工作台会进入 train 调优。")
    elif step_key == "train":
        job = create_job(
            "optimization",
            {
                "strategy_slug": strategy_slug,
                "baseline_profile": profile_name,
                "candidate_count": max(3, min(candidate_count, 6)),
                "run_backtests": True,
            },
        )
        if not job.get("deduped"):
            start_job_process(int(job["id"]))
        jobs.append(job)
        notes.append("已创建自动候选参数与 train 回测任务；候选不会自动晋级。")
    elif step_key == "validation":
        job = create_job(
            "validation",
            {
                "strategy_slug": strategy_slug,
                "profile_name": profile_name,
                "min_trades": 30,
                "min_profit": 0,
                "min_profit_factor": 1.05,
                "max_drawdown": 0.25,
                "min_winrate": 0.35,
                "min_avg_profit": 0,
                "min_trades_per_day": 0.05,
                "max_repeats": 1,
            },
        )
        if not job.get("deduped"):
            start_job_process(int(job["id"]))
        jobs.append(job)
        notes.append("已创建 validation gate；同参数档案同区间默认只保留一个非失败任务。")
    elif step_key == "test":
        job = create_job(
            "backtest",
            {
                "strategy_slug": strategy_slug,
                "profile_name": profile_name,
                "phase": "test",
                "max_repeats": 1,
            },
        )
        if not job.get("deduped"):
            start_job_process(int(job["id"]))
        jobs.append(job)
        notes.append("已创建 test 留出回测；test 结果只用于复核，不用于调参。")
    else:
        return {
            "advanced": False,
            "step_key": step_key,
            "jobs": jobs,
            "notes_zh": ["paper/live/归档阶段需要人工确认，不由自动推进直接处理。"],
        }

    return {
        "advanced": bool(jobs),
        "step_key": step_key,
        "jobs": jobs,
        "notes_zh": notes,
    }


def promote_profile(
    strategy_slug: str,
    profile_name: str,
    to_status: str,
    reason: str,
) -> dict[str, Any]:
    if to_status not in {"validated", "paper_active", "live_candidate", "live_active"}:
        raise RuntimeError(f"unsupported promotion target: {to_status}")
    if not reason.strip():
        raise RuntimeError("promotion reason is required")

    gate = run_evidence_check(strategy_slug, profile_name, to_status)
    if not gate["passed"]:
        return {
            "promoted": False,
            "strategy_slug": strategy_slug,
            "profile_name": profile_name,
            "to_status": to_status,
            "reason": reason,
            "evidence": gate,
            "failed_checks": gate["failed_checks"],
        }

    db_service = _db_service()
    db_service.promote_profile(strategy_slug, profile_name, to_status, reason)
    return {
        "promoted": True,
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "to_status": to_status,
        "reason": reason,
        "evidence": gate,
    }


def demote_profile(
    strategy_slug: str,
    profile_name: str,
    to_status: str,
    reason: str,
) -> dict[str, Any]:
    if to_status not in {"validated", "archived"}:
        raise RuntimeError(f"unsupported demotion target: {to_status}")
    if not reason.strip():
        raise RuntimeError("demotion reason is required")
    db_service = _db_service()
    db_service.promote_profile(strategy_slug, profile_name, to_status, reason)
    return {
        "demoted": True,
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "to_status": to_status,
        "reason": reason,
    }


def update_profile_thesis(
    strategy_slug: str,
    profile_name: str,
    thesis: dict[str, Any],
) -> dict[str, Any]:
    normalized = {key: str(thesis.get(key) or "").strip() for key in THESIS_FIELDS}
    db_service = _db_service()
    db_service.init_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update strategy_profiles
                set validation = jsonb_set(
                    coalesce(validation, '{}'::jsonb),
                    '{thesis}',
                    %s::jsonb,
                    true
                  ),
                  updated_at = now()
                where strategy_slug = %s and profile_name = %s
                returning profile_name, validation
                """,
                (Json(normalized), strategy_slug, profile_name),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"profile not found: {strategy_slug}/{profile_name}")
    return {
        "updated": True,
        "strategy_slug": strategy_slug,
        "profile_name": profile_name,
        "thesis": normalized,
    }


def _load_profile_context(strategy_slug: str, profile_name: str) -> dict[str, Any]:
    db_service = _db_service()
    db_service.init_schema()
    init_job_schema()
    with db_service.connect() as conn:
        with conn.cursor() as cur:
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

            cur.execute(
                """
                select id, timerange, passed, metrics, gate, warnings, failed_checks, artifact_path, created_at
                from strategy_validation_results
                where strategy_slug = %s and profile_name = %s
                order by created_at desc, id desc
                limit 5
                """,
                (strategy_slug, profile_name),
            )
            validations = list(cur.fetchall())

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
                limit 50
                """,
                (strategy_slug, strategy_slug, profile_name, profile_name),
            )
            jobs = list(cur.fetchall())

            cur.execute(
                """
                select id, from_status, to_status, reason, metadata, created_at
                from strategy_promotion_events
                where strategy_slug = %s and profile_name = %s
                order by created_at desc, id desc
                limit 20
                """,
                (strategy_slug, profile_name),
            )
            promotions = list(cur.fetchall())

    return {
        "artifacts": artifacts,
        "validations": validations,
        "jobs": jobs,
        "promotions": promotions,
    }


def _build_steps(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for template in STEP_TEMPLATES:
        builder = STEP_BUILDERS[template["key"]]
        data = builder(strategy, profile, context)
        step = {
            **template,
            "status": data["status"],
            "evidence": data.get("evidence", []),
            "gate_checks": data.get("gate_checks", []),
            "blocked_reasons": data.get("blocked_reasons", []),
            "next_actions": data.get("next_actions", []),
            "substeps": data.get("substeps", []),
        }
        if not step["evidence"] and not step["blocked_reasons"]:
            step["blocked_reasons"] = ["当前步骤缺少可展示证据，请补充对应任务或数据库记录。"]
        steps.append(step)
    return steps


def _profile_thesis(profile: dict[str, Any]) -> dict[str, Any]:
    validation = profile.get("validation") or {}
    thesis = validation.get("thesis") if isinstance(validation, dict) else {}
    if not isinstance(thesis, dict):
        thesis = {}
    values = {key: str(thesis.get(key) or "") for key in THESIS_FIELDS}
    missing = [label for key, label in THESIS_FIELDS.items() if not values[key].strip()]
    return {
        "values": values,
        "missing_fields": missing,
        "complete": True,
        "recommended_missing_fields": missing,
    }


def _assistant_plan(
    step_key: str,
    strategy: dict[str, Any],
    profile: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    strategy_name = strategy.get("name") or strategy["slug"]
    prompt = (
        f"请作为 AI-OuYi 策略研究助手，基于 {strategy_name} / {profile['profile_name']} "
        "生成下一步可执行方案。需要说明参数变化、回测阶段、晋级条件和停止条件。"
    )
    plan_by_step = {
        "hypothesis": {
            "mode_zh": "AI 起草，人工确认",
            "can_auto_advance": False,
            "next_step_zh": "补齐中文策略假设、收益来源、适用市场和失效条件。",
        },
        "definition": {
            "mode_zh": "AI 起草，人工确认",
            "can_auto_advance": False,
            "next_step_zh": "生成或修复 spec，明确因子、入场、出场和风控定义。",
        },
        "profile": {
            "mode_zh": "AI 起草，人工确认",
            "can_auto_advance": False,
            "next_step_zh": "从 baseline 生成候选 profile，记录参数改动理由。",
        },
        "runtime_artifact": {
            "mode_zh": "程序单向推进",
            "can_auto_advance": True,
            "next_step_zh": "创建 materialize 任务，生成 runtime strategy 与 params artifact。",
        },
        "train": {
            "mode_zh": "AI 分支调优",
            "can_auto_advance": True,
            "next_step_zh": "生成 3-6 个候选参数档案，并分别跑 train 回测。",
        },
        "validation": {
            "mode_zh": "程序验证闸门",
            "can_auto_advance": True,
            "next_step_zh": "运行 validation gate；失败后回到候选参数池，不直接改 test。",
        },
        "test": {
            "mode_zh": "程序留出复核",
            "can_auto_advance": True,
            "next_step_zh": "仅对通过 validation 的 profile 跑 test 留出回测。",
        },
        "paper": {
            "mode_zh": "人工晋级",
            "can_auto_advance": False,
            "next_step_zh": "检查 runtime 对齐、validation/test 证据和风控后再创建模拟盘。",
        },
    }
    plan = plan_by_step.get(
        step_key,
        {
            "mode_zh": "人工复核",
            "can_auto_advance": False,
            "next_step_zh": "当前阶段涉及运行风险或归档，需要人工确认。",
        },
    )
    return {
        **plan,
        "codex_prompt_zh": prompt,
        "attempt_policy_zh": "同一策略、参数档案、阶段、timerange 默认只允许 1 个 pending/running/success 任务；需要重跑时显式 force。",
        "branching_policy_zh": "train 可产生多个候选 profile；validation/test 不调参，只验证和淘汰。",
        "recent_job_count": len(context.get("jobs") or []),
    }


def _status_rank(status: str) -> int:
    if status == "archived":
        return len(LIFECYCLE_STATUS_ORDER)
    try:
        return LIFECYCLE_STATUS_ORDER.index(status)
    except ValueError:
        return 0


def _at_least(status: str, target: str) -> bool:
    return _status_rank(status) >= _status_rank(target)


def _artifact_types(context: dict[str, Any]) -> set[str]:
    return {str(row["artifact_type"]) for row in context["artifacts"]}


def _latest_job(context: dict[str, Any], phase: str) -> dict[str, Any] | None:
    for job in context["jobs"]:
        payload = job.get("payload") or {}
        result = job.get("result") or {}
        if payload.get("phase") == phase or result.get("phase") == phase:
            return job
    return None


def _promotion_to(context: dict[str, Any], status: str) -> dict[str, Any] | None:
    return next((event for event in context["promotions"] if event.get("to_status") == status), None)


def _base_substep(key: str, title: str, status: str, evidence: list[dict[str, Any]], blocked: list[str]) -> dict[str, Any]:
    return {
        "key": key,
        "title_zh": title,
        "description_zh": title,
        "required": True,
        "status": status,
        "inputs": [],
        "outputs": [],
        "evidence": evidence,
        "gate_checks": [],
        "blocked_reasons": blocked,
        "next_actions": [],
        "substeps": [],
    }


def _hypothesis_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    evidence = [{"label_zh": "策略注册表", "value": strategy["slug"], "source": "strategy_specs.slug"}]
    blocked = []
    thesis = _profile_thesis(profile)
    if strategy.get("description"):
        evidence.append({"label_zh": "策略说明", "value": strategy["description"], "source": "strategy_specs.description"})
    else:
        blocked.append("strategy_specs.description 为空，缺少可读的策略假设说明。")
    if thesis["missing_fields"]:
        evidence.append({
            "label_zh": "profile thesis",
            "value": "建议补充：" + "、".join(thesis["missing_fields"]),
            "source": "strategy_profiles.validation.thesis",
        })
    else:
        evidence.append({"label_zh": "profile thesis", "value": "已补充", "source": "strategy_profiles.validation.thesis"})
    return {
        "status": "completed" if not blocked else "blocked",
        "evidence": evidence,
        "blocked_reasons": blocked,
        "next_actions": ["补齐策略中文假设和适用场景说明。"] if blocked else [],
        "substeps": [
            _base_substep("registered", "策略已进入 strategy_specs", "completed", evidence[:1], []),
            _base_substep("description", "策略假设说明", "completed" if strategy.get("description") else "blocked", evidence[1:], blocked),
        ],
    }


def _definition_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    spec = strategy.get("spec") or {}
    keys = sorted(spec.keys()) if isinstance(spec, dict) else []
    evidence = [{"label_zh": "spec 字段数", "value": len(keys), "source": "strategy_specs.spec"}] if keys else []
    blocked = [] if keys else ["strategy_specs.spec 为空，无法确认策略定义。"]
    required = {
        "factors": "因子定义",
        "entry_conditions": "入场条件",
        "exit_conditions": "出场条件",
        "train_timerange": "train 区间",
        "validation_timerange": "validation 区间",
        "test_timerange": "test 区间",
        "risk_model": "风险模型",
    }
    if keys:
        missing = [label for key, label in required.items() if not spec.get(key)]
        if missing:
            blocked.append("策略定义缺少：" + "、".join(missing))
    return {
        "status": "completed" if keys and not blocked else "blocked",
        "evidence": evidence + [{"label_zh": "定义摘要字段", "value": ", ".join(keys[:12]), "source": "strategy_specs.spec"}] if keys else [],
        "blocked_reasons": blocked,
        "next_actions": ["在策略定义步骤生成基础定义，或由 Codex 补齐正式 spec。"] if blocked else [],
    }


def _profile_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    overrides = profile.get("overrides") or {}
    validation = profile.get("validation") or {}
    evidence = [
        {"label_zh": "profile", "value": profile["profile_name"], "source": "strategy_profiles.profile_name"},
        {"label_zh": "当前状态", "value": profile["status"], "source": "strategy_profiles.status"},
        {"label_zh": "覆盖参数数量", "value": len(overrides), "source": "strategy_profiles.overrides"},
    ]
    blocked = []
    if not overrides:
        blocked.append("strategy_profiles.overrides 为空，需要确认是否为有意使用默认参数。")
    return {
        "status": "completed" if profile.get("profile_name") else "blocked",
        "evidence": evidence,
        "blocked_reasons": blocked,
        "next_actions": ["补充 profile 参数覆盖或在备注中确认默认参数。"] if blocked else [],
        "substeps": [
            _base_substep("profile_record", "profile 记录存在", "completed", evidence[:2], []),
            _base_substep(
                "profile_validation",
                "profile 验证摘要",
                "completed" if validation else "pending",
                [{"label_zh": "validation 字段数", "value": len(validation), "source": "strategy_profiles.validation"}] if validation else [],
                [] if validation else ["profile.validation 暂无验证摘要。"],
            ),
        ],
    }


def _runtime_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    types = _artifact_types(context)
    evidence = [
        {
            "label_zh": row["artifact_type"],
            "value": row["artifact_hash"][:12],
            "source": row["artifact_path"],
        }
        for row in context["artifacts"][:4]
    ]
    missing = []
    if "freqtrade_strategy_py" not in types:
        missing.append("缺少 freqtrade_strategy_py runtime artifact 记录。")
    if "freqtrade_params_json" not in types:
        missing.append("缺少 freqtrade_params_json runtime artifact 记录。")
    return {
        "status": "completed" if not missing else ("pending" if _at_least(profile["status"], "generated") else "blocked"),
        "evidence": evidence,
        "blocked_reasons": missing,
        "next_actions": ["在运行系统执行 materialize，生成并记录 runtime artifact。"] if missing else [],
    }


def _backtest_step(context: dict[str, Any], phase: str, required_status: str) -> dict[str, Any]:
    job = _latest_job(context, phase)
    if job:
        result = job.get("result") or {}
        metrics = result.get("metrics") or {}
        return {
            "status": "completed" if job["status"] == "success" else "blocked",
            "evidence": [
                {"label_zh": f"{phase} job", "value": f"#{job['id']} {job['status']}", "source": "web_jobs"},
                {"label_zh": "交易数", "value": metrics.get("total_trades", "-"), "source": "web_jobs.result.metrics"},
                {"label_zh": "timerange", "value": result.get("timerange", "-"), "source": "web_jobs.result.timerange"},
            ],
            "blocked_reasons": [] if job["status"] == "success" else [job.get("error_summary") or f"{phase} 回测任务未成功。"],
            "next_actions": [] if job["status"] == "success" else [f"修复失败原因后重新执行 {phase} 回测。"],
        }
    locked = not (_at_least(required_status, "generated") or _artifact_types(context))
    return {
        "status": "locked" if locked else "pending",
        "evidence": [],
        "blocked_reasons": [f"缺少 {phase} 回测任务结果。"],
        "next_actions": [f"在回测验证页使用 {phase} 数据用途发起回测。"],
    }


def _train_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return _backtest_step(context, "train", profile["status"])


def _validation_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    latest = context["validations"][0] if context["validations"] else None
    if latest:
        return {
            "status": "completed" if latest["passed"] else "blocked",
            "evidence": [
                {"label_zh": "validation result", "value": f"#{latest['id']} {'PASS' if latest['passed'] else 'FAIL'}", "source": "strategy_validation_results"},
                {"label_zh": "timerange", "value": latest["timerange"], "source": "strategy_validation_results.timerange"},
            ],
            "gate_checks": [
                {"label_zh": key, "value": value, "status": "configured"}
                for key, value in (latest.get("gate") or {}).items()
            ],
            "blocked_reasons": list(latest.get("failed_checks") or []),
            "next_actions": [] if latest["passed"] else ["调整参数后重新跑 validation gate；不要使用 test 区间调参。"],
        }
    return {
        "status": "pending" if _at_least(profile["status"], "backtested") else "locked",
        "evidence": [],
        "blocked_reasons": ["缺少 strategy_validation_results 验证记录。"],
        "next_actions": ["在回测验证页执行 validation gate。"],
    }


def _test_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return _backtest_step(context, "test", profile["status"])


def _paper_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event = _promotion_to(context, "paper_active")
    paper_run = context.get("paper_run")
    active = profile["status"] == "paper_active" or bool(event)
    evidence = [{"label_zh": "profile 状态", "value": profile["status"], "source": "strategy_profiles.status"}]
    if event:
        evidence.append({"label_zh": "promotion event", "value": f"#{event['id']}", "source": "strategy_promotion_events"})
    if paper_run:
        evidence.append({"label_zh": "模拟盘记录", "value": f"#{paper_run['id']} / {paper_run['status']}", "source": "web_paper_runs"})
    if active:
        blocked_reasons: list[str] = []
        next_actions: list[str] = []
    elif paper_run:
        blocked_reasons = ["已有模拟盘记录，但尚未人工晋级为 paper_active。"]
        next_actions = ["复核模拟盘证据后，人工点击晋级 paper_active。"]
    else:
        blocked_reasons = ["尚未创建模拟盘记录，或缺少 paper_active 晋级证据。"]
        next_actions = ["通过 validation/test 基础复核后，创建模拟盘记录并人工晋级。"]
    return {
        "status": "completed" if active else ("pending" if _at_least(profile["status"], "validated") else "locked"),
        "evidence": evidence,
        "blocked_reasons": blocked_reasons,
        "next_actions": next_actions,
    }


def _promotion_step(status: str, strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event = _promotion_to(context, status)
    reached = _at_least(profile["status"], status) or bool(event)
    return {
        "status": "completed" if reached else ("pending" if _at_least(profile["status"], "paper_active") else "locked"),
        "evidence": [
            {"label_zh": "profile 状态", "value": profile["status"], "source": "strategy_profiles.status"},
            {"label_zh": "promotion event", "value": f"#{event['id']}", "source": "strategy_promotion_events"},
        ] if event else [{"label_zh": "profile 状态", "value": profile["status"], "source": "strategy_profiles.status"}],
        "blocked_reasons": [] if reached else [f"尚未达到 {status} 状态，缺少对应 promotion evidence。"],
        "next_actions": [] if reached else [f"补齐前置证据后再进入 {status} 复核。"],
    }


def _live_candidate_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return _promotion_step("live_candidate", strategy, profile, context)


def _live_active_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return _promotion_step("live_active", strategy, profile, context)


def _archived_step(strategy: dict[str, Any], profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    event = _promotion_to(context, "archived")
    archived = profile["status"] == "archived" or bool(event)
    return {
        "status": "completed" if archived else "locked",
        "evidence": [{"label_zh": "profile 状态", "value": profile["status"], "source": "strategy_profiles.status"}],
        "blocked_reasons": [] if archived else ["当前 profile 未归档；活跃生命周期可继续推进。"],
        "next_actions": [] if archived else ["仅当停止研究或运行时，记录原因并归档。"],
    }


STEP_BUILDERS = {
    "hypothesis": _hypothesis_step,
    "definition": _definition_step,
    "profile": _profile_step,
    "runtime_artifact": _runtime_step,
    "train": _train_step,
    "validation": _validation_step,
    "test": _test_step,
    "paper": _paper_step,
    "live_candidate": _live_candidate_step,
    "live_active": _live_active_step,
    "archived": _archived_step,
}
