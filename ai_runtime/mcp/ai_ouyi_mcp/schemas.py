from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TERMINAL_JOB_STATUSES = {"success", "failed"}


class ToolError(BaseModel):
    type: str
    message: str
    status_code: int | None = None
    detail: Any = None


class SopStep(BaseModel):
    advances: bool = False
    current: int | None = None
    next: int | None = None
    note: str | None = None


class ToolResult(BaseModel):
    ok: bool
    data: Any = None
    error: ToolError | None = None
    sop_step: SopStep | None = None


class CreateStrategyHypothesisRequest(BaseModel):
    slug: str = Field(min_length=3)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    profile_name: str = "draft"
    thesis: dict[str, Any] = Field(default_factory=dict)


class UpdateStrategyDefinitionRequest(BaseModel):
    slug: str = Field(min_length=3)
    spec: dict[str, Any] = Field(default_factory=dict)
    profile_name: str | None = None
    profile_overrides: dict[str, Any] | None = None
    profile_status: str = "candidate"
    source: str = "ai_generated_spec"
    validation: dict[str, Any] = Field(default_factory=dict)
    activate_profile: bool = True


class WaitOptions(BaseModel):
    wait: bool = False
    poll_interval_seconds: float = Field(default=2.0, gt=0)
    timeout_wait_seconds: int = Field(default=1800, gt=0)


class EnsureDataRequest(WaitOptions):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None
    pair: str | None = None
    timeframe: str | None = None
    trading_mode: str | None = None
    timerange: str | None = None
    erase: bool = False
    no_parallel_download: bool = False
    candle_types: list[str] | None = None
    timeout_seconds: int | None = None


class MaterializeStrategyRequest(WaitOptions):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None
    timeout_wait_seconds: int = Field(default=900, gt=0)


class RunBacktestRequest(WaitOptions):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None
    phase: str = "validation"
    timerange: str | None = None
    force: bool = False
    timeout_seconds: int | None = None
    extra_payload: dict[str, Any] = Field(default_factory=dict)


class RunValidationGateRequest(WaitOptions):
    strategy_slug: str = Field(min_length=1)
    profile_name: str | None = None
    timerange: str | None = None
    min_trades: int = Field(default=5, ge=0)
    min_profit_factor: float = Field(default=1.0, ge=0)
    force: bool = False
    timeout_seconds: int | None = None
    extra_payload: dict[str, Any] = Field(default_factory=dict)


class GetStrategyStateRequest(BaseModel):
    slug: str = Field(min_length=1)


class GetJobRequest(WaitOptions):
    job_id: int = Field(ge=1)


class ReportSystemGapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    impact_scope: str = Field(min_length=1)
    current_status: Literal["open", "mitigated", "fixed", "accepted"] = "open"
    recommended_api: str | None = None
    recommended_ui: str | None = None
    related_strategy_slug: str | None = None
    blocking_step: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
