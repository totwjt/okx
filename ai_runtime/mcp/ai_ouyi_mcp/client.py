from __future__ import annotations

import ast
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel

from .schemas import TERMINAL_JOB_STATUSES, SopStep, ToolError, ToolResult


DEFAULT_BASE_URL = "http://127.0.0.1:8123"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_GAPS_DIR = PROJECT_ROOT / "ai_runtime" / "mcp" / "system_gaps"
RUNTIME_STRATEGIES_DIR = PROJECT_ROOT / "execution" / "freqtrade" / "user_data" / "runtime_strategies"


class WebApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class AiOuyiWebClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: int = 30) -> None:
        self.base_url_source = "argument" if base_url else "AI_OUYI_WEB_BASE_URL" if os.getenv("AI_OUYI_WEB_BASE_URL") else "default"
        self.base_url = (base_url or os.getenv("AI_OUYI_WEB_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.trust_env = False

    def preflight_web_api(self) -> ToolResult:
        checks = [
            self._probe_endpoint("GET", "/api/health"),
            self._probe_endpoint("GET", "/api/strategies"),
        ]
        healthy = all(check.get("ok") for check in checks)
        permission_issue = any(self._is_likely_local_permission_error(check.get("error")) for check in checks)
        data = {
            "base_url": self.base_url,
            "base_url_source": self.base_url_source,
            "timeout_seconds": self.timeout_seconds,
            "checks": checks,
            "healthy": healthy,
            "likely_sandbox_permission_issue": permission_issue,
        }
        if permission_issue:
            data["advice"] = (
                "Local loopback access appears blocked by the current command sandbox. "
                "Run this MCP/Web API call with approved local network permission or set AI_OUYI_WEB_BASE_URL "
                "to a reachable Web API endpoint, then rerun preflight."
            )
        if healthy:
            return ToolResult(
                ok=True,
                data=data,
                sop_step=SopStep(advances=False, note="Web API preflight passed. Step 1 may proceed if the strategy hypothesis is ready."),
            )
        return ToolResult(
            ok=False,
            data=data,
            error=ToolError(
                type="web_api_preflight_failed",
                message=f"Web API preflight failed for {self.base_url}; configure AI_OUYI_WEB_BASE_URL or start the Web API.",
                detail=data,
            ),
            sop_step=SopStep(advances=False, note="Web API preflight failed; do not advance SOP Step."),
        )

    def create_strategy_hypothesis(self, payload: BaseModel) -> ToolResult:
        return self._wrap(
            lambda: self._request("POST", "/api/strategies", json_body=payload.model_dump()),
            SopStep(advances=True, current=1, next=2, note="Strategy hypothesis registered."),
        )

    def update_strategy_definition(self, payload: BaseModel) -> ToolResult:
        body = payload.model_dump(exclude={"slug"})
        return self._wrap(
            lambda: self._request("PUT", f"/api/strategies/{payload.slug}/definition", json_body=body),
            SopStep(
                advances=True,
                current=2,
                next=4,
                note="Complete spec saved. Treat Step 3 as complete only if profile overrides and status are intentional.",
            ),
        )

    def ensure_data(self, payload: BaseModel) -> ToolResult:
        body = payload.model_dump(
            exclude={"wait", "poll_interval_seconds", "timeout_wait_seconds"},
            exclude_none=True,
        )
        return self._create_job_or_wait(
            lambda: self._request("POST", "/api/data/ensure", json_body=body),
            wait=payload.wait,
            poll_interval_seconds=payload.poll_interval_seconds,
            timeout_wait_seconds=payload.timeout_wait_seconds,
            success_step=SopStep(advances=True, current=7, next=8, note="Data ensure job finished successfully."),
            pending_step=SopStep(advances=False, current=7, note="Data ensure job created; wait for terminal status before advancing."),
        )

    def materialize_strategy(self, payload: BaseModel) -> ToolResult:
        job_payload = payload.model_dump(
            exclude={"wait", "poll_interval_seconds", "timeout_wait_seconds"},
            exclude_none=True,
        )
        body = {"job_type": "materialize", "payload": job_payload}
        return self._create_job_or_wait(
            lambda: self._request("POST", "/api/jobs", json_body=body),
            wait=payload.wait,
            poll_interval_seconds=payload.poll_interval_seconds,
            timeout_wait_seconds=payload.timeout_wait_seconds,
            success_step=SopStep(advances=True, current=5, next=6, note="Materialize job finished successfully."),
            pending_step=SopStep(advances=False, current=5, note="Materialize job created; wait for terminal status before advancing."),
        )

    def static_validate_strategy(self, payload: BaseModel) -> ToolResult:
        return self._wrap(
            lambda: self._static_validate_strategy(payload),
            SopStep(advances=True, current=6, next=7, note="Static validation passed; data preparation may proceed."),
        )

    def run_backtest(self, payload: BaseModel) -> ToolResult:
        job_payload = self._job_payload(
            payload,
            exclude={"wait", "poll_interval_seconds", "timeout_wait_seconds", "extra_payload"},
        )
        body = {"job_type": "backtest", "payload": {**payload.extra_payload, **job_payload}}
        return self._create_job_or_wait(
            lambda: self._request("POST", "/api/jobs", json_body=body),
            wait=payload.wait,
            poll_interval_seconds=payload.poll_interval_seconds,
            timeout_wait_seconds=payload.timeout_wait_seconds,
            success_step=SopStep(advances=False, current=8, note="Backtest finished; validation gate is still required."),
            pending_step=SopStep(advances=False, current=8, note="Backtest job created; wait for evidence before interpreting."),
        )

    def run_validation_gate(self, payload: BaseModel) -> ToolResult:
        job_payload = self._job_payload(
            payload,
            exclude={"wait", "poll_interval_seconds", "timeout_wait_seconds", "extra_payload"},
        )
        body = {"job_type": "validation", "payload": {**payload.extra_payload, **job_payload}}
        return self._create_job_or_wait(
            lambda: self._request("POST", "/api/jobs", json_body=body),
            wait=payload.wait,
            poll_interval_seconds=payload.poll_interval_seconds,
            timeout_wait_seconds=payload.timeout_wait_seconds,
            success_step=SopStep(advances=True, current=8, next=9, note="Validation gate reached terminal status; AI must interpret quality."),
            pending_step=SopStep(advances=False, current=8, note="Validation job created; wait for terminal status before lifecycle decisions."),
        )

    def get_strategy_state(self, slug: str) -> ToolResult:
        def load() -> dict[str, Any]:
            strategy = self._request("GET", f"/api/strategies/{slug}")
            profiles = self._request("GET", f"/api/strategies/{slug}/profiles")
            return {"strategy": strategy, "profiles": profiles}

        return self._wrap(
            load,
            SopStep(advances=True, current=4, next=5, note="Registry state fetched; AI must verify it matches intended spec/profile."),
        )

    def get_job(self, job_id: int, *, wait: bool, poll_interval_seconds: float, timeout_wait_seconds: int) -> ToolResult:
        if wait:
            return self._wrap(
                lambda: self._wait_for_job(job_id, poll_interval_seconds, timeout_wait_seconds),
                SopStep(advances=False, note="Job evidence fetched at terminal status."),
            )
        return self._wrap(
            lambda: self._request("GET", f"/api/jobs/{job_id}"),
            SopStep(advances=False, note="Job evidence fetched."),
        )

    def report_system_gap(self, payload: BaseModel) -> ToolResult:
        def write_gap() -> dict[str, Any]:
            SYSTEM_GAPS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            safe_title = "".join(ch if ch.isalnum() else "_" for ch in payload.title.lower()).strip("_")[:60]
            path = SYSTEM_GAPS_DIR / f"{timestamp}_{safe_title or 'system_gap'}.json"
            record = {
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": "ai_ouyi_mcp_v1_local_gap_file",
                **payload.model_dump(exclude_none=True),
            }
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {"path": str(path), "gap": record, "known_missing_api": "POST /api/system-gaps"}

        return self._wrap(
            write_gap,
            SopStep(advances=False, note="System gap recorded locally because Web API does not have system-gap endpoints yet."),
        )

    def _create_job_or_wait(
        self,
        create_job: Any,
        *,
        wait: bool,
        poll_interval_seconds: float,
        timeout_wait_seconds: int,
        success_step: SopStep,
        pending_step: SopStep,
    ) -> ToolResult:
        def create_or_wait() -> Any:
            job = create_job()
            if wait:
                job_id = self._extract_job_id(job)
                if job_id is None:
                    raise WebApiError("API response does not include a job id", detail=job)
                return self._wait_for_job(job_id, poll_interval_seconds, timeout_wait_seconds)
            return job

        result = self._wrap(create_or_wait, success_step if wait else pending_step)
        if wait and result.ok and isinstance(result.data, dict) and result.data.get("status") != "success":
            result.sop_step = SopStep(advances=False, note="Job reached terminal non-success status; inspect error before advancing.")
        return result

    def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, json=json_body, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise WebApiError(
                f"Web API request failed: {exc}",
                detail={
                    "url": url,
                    "method": method,
                    "base_url": self.base_url,
                    "base_url_source": self.base_url_source,
                    "env_var": "AI_OUYI_WEB_BASE_URL",
                },
            ) from exc
        if response.status_code >= 400:
            detail = self._response_detail(response)
            raise WebApiError(
                f"Web API returned HTTP {response.status_code}",
                status_code=response.status_code,
                detail=detail,
            )
        return self._response_detail(response)

    def _probe_endpoint(self, method: str, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            return {
                "ok": False,
                "method": method,
                "path": path,
                "url": url,
                "error": str(exc),
                "likely_sandbox_permission_issue": self._is_likely_local_permission_error(str(exc)),
            }
        detail = self._response_detail(response)
        return {
            "ok": response.status_code < 400,
            "method": method,
            "path": path,
            "url": url,
            "status_code": response.status_code,
            "detail": detail,
        }

    def _static_validate_strategy(self, payload: BaseModel) -> dict[str, Any]:
        slug = str(payload.strategy_slug)
        self._validate_slug_for_path(slug)
        runtime_dir = Path(payload.runtime_dir).expanduser() if payload.runtime_dir else RUNTIME_STRATEGIES_DIR
        strategy_path = runtime_dir / f"auto_{slug}.py"
        params_path = runtime_dir / f"auto_{slug}.json"
        checks: list[dict[str, Any]] = []

        source = self._read_required_text(strategy_path, checks, "strategy_py_exists")
        params = self._read_json_if_present(params_path, checks)

        tree: ast.Module | None = None
        if source is not None:
            try:
                compile(source, str(strategy_path), "exec")
                checks.append({"name": "py_compile", "ok": True})
            except SyntaxError as exc:
                checks.append({"name": "py_compile", "ok": False, "error": f"{exc.__class__.__name__}: {exc}"})
            try:
                tree = ast.parse(source, filename=str(strategy_path))
                checks.append({"name": "ast_parse", "ok": True})
            except SyntaxError as exc:
                checks.append({"name": "ast_parse", "ok": False, "error": f"{exc.__class__.__name__}: {exc}"})

        class_info = self._extract_strategy_class_info(tree) if tree is not None else {}
        public_class_info = {key: value for key, value in class_info.items() if key != "class_node"}
        checks.append({"name": "strategy_class", "ok": bool(class_info), "detail": public_class_info or None})

        if payload.expected_timeframe is not None:
            actual = class_info.get("timeframe")
            checks.append(
                {
                    "name": "timeframe_matches_expected",
                    "ok": actual == payload.expected_timeframe,
                    "expected": payload.expected_timeframe,
                    "actual": actual,
                }
            )
        if payload.expected_can_short is not None:
            actual = class_info.get("can_short")
            checks.append(
                {
                    "name": "can_short_matches_expected",
                    "ok": actual is payload.expected_can_short,
                    "expected": payload.expected_can_short,
                    "actual": actual,
                }
            )

        method_columns = self._extract_dataframe_signal_columns(class_info.get("class_node"))
        checks.append(
            {
                "name": "entry_exit_signal_columns",
                "ok": {"enter_long", "enter_short", "exit_long", "exit_short"}.issubset(method_columns),
                "required": ["enter_long", "enter_short", "exit_long", "exit_short"],
                "actual": sorted(method_columns),
            }
        )

        if params is not None and class_info.get("class_name") is not None:
            params_strategy_name = params.get("strategy_name")
            checks.append(
                {
                    "name": "params_strategy_name_matches_class",
                    "ok": params_strategy_name == class_info.get("class_name"),
                    "expected": class_info.get("class_name"),
                    "actual": params_strategy_name,
                }
            )

        ok = all(check.get("ok") for check in checks)
        result = {
            "strategy_slug": slug,
            "runtime_dir": str(runtime_dir),
            "strategy_path": str(strategy_path),
            "params_path": str(params_path),
            "class": public_class_info or None,
            "checks": checks,
            "passed": ok,
        }
        if not ok:
            raise WebApiError("Static validation failed", detail=result)
        return result

    def _wait_for_job(self, job_id: int, poll_interval_seconds: float, timeout_wait_seconds: int) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_wait_seconds
        last_job: dict[str, Any] | None = None
        while time.monotonic() <= deadline:
            job = self._request("GET", f"/api/jobs/{job_id}")
            if not isinstance(job, dict):
                raise WebApiError("Job response is not an object", detail=job)
            last_job = job
            if str(job.get("status")) in TERMINAL_JOB_STATUSES:
                return job
            time.sleep(poll_interval_seconds)
        raise WebApiError(
            f"Timed out waiting for job {job_id}",
            detail={"job_id": job_id, "last_job": last_job, "timeout_wait_seconds": timeout_wait_seconds},
        )

    @staticmethod
    def _extract_job_id(job: Any) -> int | None:
        if not isinstance(job, dict):
            return None
        value = job.get("id") or job.get("job_id")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _response_detail(response: requests.Response) -> Any:
        if not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _job_payload(payload: BaseModel, *, exclude: set[str]) -> dict[str, Any]:
        return payload.model_dump(exclude=exclude, exclude_none=True)

    @staticmethod
    def _is_likely_local_permission_error(error: Any) -> bool:
        if not error:
            return False
        text = str(error).lower()
        return "operation not permitted" in text or "permission denied" in text

    @staticmethod
    def _validate_slug_for_path(slug: str) -> None:
        if not slug or "/" in slug or "\\" in slug or slug in {".", ".."}:
            raise WebApiError("Invalid strategy slug for runtime artifact lookup", detail={"strategy_slug": slug})

    @staticmethod
    def _read_required_text(path: Path, checks: list[dict[str, Any]], name: str) -> str | None:
        if not path.exists():
            checks.append({"name": name, "ok": False, "path": str(path), "error": "missing"})
            return None
        checks.append({"name": name, "ok": True, "path": str(path)})
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _read_json_if_present(path: Path, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not path.exists():
            checks.append({"name": "params_json_exists", "ok": False, "path": str(path), "error": "missing"})
            return None
        checks.append({"name": "params_json_exists", "ok": True, "path": str(path)})
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append({"name": "params_json_parse", "ok": False, "error": str(exc)})
            return None
        checks.append({"name": "params_json_parse", "ok": isinstance(value, dict)})
        return value if isinstance(value, dict) else None

    @staticmethod
    def _extract_strategy_class_info(tree: ast.Module | None) -> dict[str, Any]:
        if tree is None:
            return {}
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith("Strategy"):
                continue
            attrs: dict[str, Any] = {"class_name": node.name, "class_node": node}
            for statement in node.body:
                if not isinstance(statement, ast.Assign):
                    continue
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id in {"timeframe", "can_short"}:
                        attrs[target.id] = AiOuyiWebClient._literal_or_none(statement.value)
            return attrs
        return {}

    @staticmethod
    def _extract_dataframe_signal_columns(class_node: ast.ClassDef | None) -> set[str]:
        columns: set[str] = set()
        if class_node is None:
            return columns
        for node in ast.walk(class_node):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node.value in {"enter_long", "enter_short", "exit_long", "exit_short"}:
                columns.add(node.value)
        return columns

    @staticmethod
    def _literal_or_none(node: ast.AST) -> Any:
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _wrap(fn: Any, sop_step: SopStep) -> ToolResult:
        try:
            return ToolResult(ok=True, data=fn(), sop_step=sop_step)
        except WebApiError as exc:
            return ToolResult(
                ok=False,
                error=ToolError(
                    type="web_api_error",
                    message=str(exc),
                    status_code=exc.status_code,
                    detail=exc.detail,
                ),
                sop_step=SopStep(advances=False, note="Action failed; do not advance SOP Step."),
            )
        except Exception as exc:
            return ToolResult(
                ok=False,
                error=ToolError(type="runtime_error", message=str(exc)),
                sop_step=SopStep(advances=False, note="Action failed; do not advance SOP Step."),
            )
