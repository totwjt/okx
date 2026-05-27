from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import AiOuyiWebClient
from .schemas import (
    CreateStrategyHypothesisRequest,
    EnsureDataRequest,
    GetJobRequest,
    GetStrategyStateRequest,
    MaterializeStrategyRequest,
    ReportSystemGapRequest,
    RunBacktestRequest,
    RunValidationGateRequest,
    ToolResult,
    UpdateStrategyDefinitionRequest,
)


mcp = FastMCP("ai-ouyi-strategy-research")


def _client(base_url: str | None = None) -> AiOuyiWebClient:
    return AiOuyiWebClient(base_url=base_url)


def _dump(result: ToolResult) -> dict[str, Any]:
    return result.model_dump(exclude_none=True)


@mcp.tool()
def preflight_web_api(base_url: str | None = None) -> dict[str, Any]:
    """Verify the configured Web API before running SOP Step 1 or job tools."""
    return _dump(_client(base_url=base_url).preflight_web_api())


@mcp.tool()
def create_strategy_hypothesis(
    slug: str,
    name: str,
    description: str,
    profile_name: str = "draft",
    thesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register a Step 1 strategy hypothesis through the Web API."""
    request = CreateStrategyHypothesisRequest(
        slug=slug,
        name=name,
        description=description,
        profile_name=profile_name,
        thesis=thesis or {},
    )
    return _dump(_client().create_strategy_hypothesis(request))


@mcp.tool()
def update_strategy_definition(
    slug: str,
    spec: dict[str, Any],
    profile_name: str | None = None,
    profile_overrides: dict[str, Any] | None = None,
    profile_status: str = "candidate",
    source: str = "ai_generated_spec",
    validation: dict[str, Any] | None = None,
    activate_profile: bool = True,
) -> dict[str, Any]:
    """Save the complete Step 2 strategy spec and optional Step 3 profile through the Web API."""
    request = UpdateStrategyDefinitionRequest(
        slug=slug,
        spec=spec,
        profile_name=profile_name,
        profile_overrides=profile_overrides,
        profile_status=profile_status,
        source=source,
        validation=validation or {},
        activate_profile=activate_profile,
    )
    return _dump(_client().update_strategy_definition(request))


@mcp.tool()
def ensure_data(
    strategy_slug: str,
    profile_name: str | None = None,
    pair: str | None = None,
    timeframe: str | None = None,
    trading_mode: str | None = None,
    timerange: str | None = None,
    erase: bool = False,
    no_parallel_download: bool = False,
    candle_types: list[str] | None = None,
    timeout_seconds: int | None = None,
    wait: bool = False,
    poll_interval_seconds: float = 2.0,
    timeout_wait_seconds: int = 1800,
) -> dict[str, Any]:
    """Launch Step 7 data preparation through the Web API."""
    request = EnsureDataRequest(
        strategy_slug=strategy_slug,
        profile_name=profile_name,
        pair=pair,
        timeframe=timeframe,
        trading_mode=trading_mode,
        timerange=timerange,
        erase=erase,
        no_parallel_download=no_parallel_download,
        candle_types=candle_types,
        timeout_seconds=timeout_seconds,
        wait=wait,
        poll_interval_seconds=poll_interval_seconds,
        timeout_wait_seconds=timeout_wait_seconds,
    )
    return _dump(_client().ensure_data(request))


@mcp.tool()
def materialize_strategy(
    strategy_slug: str,
    profile_name: str | None = None,
    wait: bool = False,
    poll_interval_seconds: float = 2.0,
    timeout_wait_seconds: int = 900,
) -> dict[str, Any]:
    """Launch Step 5 runtime artifact materialization through the Web API job queue."""
    request = MaterializeStrategyRequest(
        strategy_slug=strategy_slug,
        profile_name=profile_name,
        wait=wait,
        poll_interval_seconds=poll_interval_seconds,
        timeout_wait_seconds=timeout_wait_seconds,
    )
    return _dump(_client().materialize_strategy(request))


@mcp.tool()
def run_backtest(
    strategy_slug: str,
    profile_name: str | None = None,
    phase: str = "validation",
    timerange: str | None = None,
    force: bool = False,
    timeout_seconds: int | None = None,
    wait: bool = False,
    poll_interval_seconds: float = 2.0,
    timeout_wait_seconds: int = 1800,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Launch a Step 8 backtest job through the Web API."""
    request = RunBacktestRequest(
        strategy_slug=strategy_slug,
        profile_name=profile_name,
        phase=phase,
        timerange=timerange,
        force=force,
        timeout_seconds=timeout_seconds,
        wait=wait,
        poll_interval_seconds=poll_interval_seconds,
        timeout_wait_seconds=timeout_wait_seconds,
        extra_payload=extra_payload or {},
    )
    return _dump(_client().run_backtest(request))


@mcp.tool()
def run_validation_gate(
    strategy_slug: str,
    profile_name: str | None = None,
    timerange: str | None = None,
    min_trades: int = 5,
    min_profit_factor: float = 1.0,
    force: bool = False,
    timeout_seconds: int | None = None,
    wait: bool = False,
    poll_interval_seconds: float = 2.0,
    timeout_wait_seconds: int = 1800,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Launch the Step 8 validation gate through the Web API."""
    request = RunValidationGateRequest(
        strategy_slug=strategy_slug,
        profile_name=profile_name,
        timerange=timerange,
        min_trades=min_trades,
        min_profit_factor=min_profit_factor,
        force=force,
        timeout_seconds=timeout_seconds,
        wait=wait,
        poll_interval_seconds=poll_interval_seconds,
        timeout_wait_seconds=timeout_wait_seconds,
        extra_payload=extra_payload or {},
    )
    return _dump(_client().run_validation_gate(request))


@mcp.tool()
def get_strategy_state(slug: str) -> dict[str, Any]:
    """Fetch Step 4 registry state and profiles through the Web API."""
    request = GetStrategyStateRequest(slug=slug)
    return _dump(_client().get_strategy_state(request.slug))


@mcp.tool()
def get_job(
    job_id: int,
    wait: bool = False,
    poll_interval_seconds: float = 2.0,
    timeout_wait_seconds: int = 1800,
) -> dict[str, Any]:
    """Fetch a Web API job record, optionally waiting for terminal status."""
    request = GetJobRequest(
        job_id=job_id,
        wait=wait,
        poll_interval_seconds=poll_interval_seconds,
        timeout_wait_seconds=timeout_wait_seconds,
    )
    return _dump(
        _client().get_job(
            request.job_id,
            wait=request.wait,
            poll_interval_seconds=request.poll_interval_seconds,
            timeout_wait_seconds=request.timeout_wait_seconds,
        )
    )


@mcp.tool()
def report_system_gap(
    title: str,
    description: str,
    impact_scope: str,
    current_status: str = "open",
    recommended_api: str | None = None,
    recommended_ui: str | None = None,
    related_strategy_slug: str | None = None,
    blocking_step: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a system-level workflow/API gap as a local structured file until Web API support exists."""
    request = ReportSystemGapRequest(
        title=title,
        description=description,
        impact_scope=impact_scope,
        current_status=current_status,
        recommended_api=recommended_api,
        recommended_ui=recommended_ui,
        related_strategy_slug=related_strategy_slug,
        blocking_step=blocking_step,
        metadata=metadata or {},
    )
    return _dump(_client().report_system_gap(request))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
