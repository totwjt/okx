import sys
import tempfile
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai_runtime/mcp"))

from ai_ouyi_mcp.client import AiOuyiWebClient
from ai_ouyi_mcp.schemas import StaticValidateStrategyRequest


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = b"{}"
        self.headers = {"content-type": "application/json"}
        self.text = "{}"

    def json(self):
        return self._payload


class FakeSession:
    trust_env = False

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.responses.pop(0)


class AiOuyiWebClientPreflightTest(unittest.TestCase):
    def test_preflight_web_api_reports_healthy_checks(self):
        client = AiOuyiWebClient(base_url="http://web.example.test")
        client.session = FakeSession(
            [
                FakeResponse(payload={"status": "ok"}),
                FakeResponse(payload={"items": []}),
            ]
        )

        result = client.preflight_web_api()

        self.assertTrue(result.ok)
        self.assertTrue(result.data["healthy"])
        self.assertEqual(result.data["base_url"], "http://web.example.test")
        self.assertEqual(result.data["base_url_source"], "argument")
        self.assertEqual([check["path"] for check in result.data["checks"]], ["/api/health", "/api/strategies"])
        self.assertFalse(result.sop_step.advances)

    def test_preflight_web_api_returns_diagnostics_when_unreachable(self):
        client = AiOuyiWebClient(base_url="http://127.0.0.1:8123")
        client.session = FakeSession(error=requests.ConnectionError("operation not permitted"))

        result = client.preflight_web_api()

        self.assertFalse(result.ok)
        self.assertFalse(result.data["healthy"])
        self.assertEqual(result.error.type, "web_api_preflight_failed")
        self.assertIn("AI_OUYI_WEB_BASE_URL", result.error.message)
        self.assertEqual(result.data["checks"][0]["path"], "/api/health")
        self.assertIn("operation not permitted", result.data["checks"][0]["error"])
        self.assertTrue(result.data["checks"][0]["likely_sandbox_permission_issue"])
        self.assertTrue(result.data["likely_sandbox_permission_issue"])
        self.assertIn("local loopback", result.data["advice"].lower())
        self.assertFalse(result.sop_step.advances)


class AiOuyiWebClientStaticValidateTest(unittest.TestCase):
    def test_static_validate_strategy_passes_for_materialized_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir)
            (runtime_dir / "auto_demo.py").write_text(
                '''
class DemoStrategy:
    timeframe = "15m"
    can_short = False

    def populate_entry_trend(self, dataframe, metadata):
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
''',
                encoding="utf-8",
            )
            (runtime_dir / "auto_demo.json").write_text('{"strategy_name": "DemoStrategy"}', encoding="utf-8")
            client = AiOuyiWebClient(base_url="http://web.example.test")

            result = client.static_validate_strategy(
                StaticValidateStrategyRequest(
                    strategy_slug="demo",
                    expected_timeframe="15m",
                    expected_can_short=False,
                    runtime_dir=str(runtime_dir),
                )
            )

            self.assertTrue(result.ok)
            self.assertTrue(result.data["passed"])
            self.assertEqual(result.data["class"]["class_name"], "DemoStrategy")
            self.assertEqual(result.sop_step.current, 6)
            self.assertEqual(result.sop_step.next, 7)

    def test_static_validate_strategy_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir)
            (runtime_dir / "auto_demo.py").write_text(
                '''
class DemoStrategy:
    timeframe = "5m"
    can_short = False

    def populate_entry_trend(self, dataframe, metadata):
        dataframe["enter_long"] = 0
        return dataframe
''',
                encoding="utf-8",
            )
            (runtime_dir / "auto_demo.json").write_text('{"strategy_name": "OtherStrategy"}', encoding="utf-8")
            client = AiOuyiWebClient(base_url="http://web.example.test")

            result = client.static_validate_strategy(
                StaticValidateStrategyRequest(
                    strategy_slug="demo",
                    expected_timeframe="15m",
                    expected_can_short=False,
                    runtime_dir=str(runtime_dir),
                )
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.error.type, "web_api_error")
            self.assertEqual(result.error.message, "Static validation failed")
            self.assertFalse(result.error.detail["passed"])
            failed_checks = {check["name"] for check in result.error.detail["checks"] if not check["ok"]}
            self.assertIn("timeframe_matches_expected", failed_checks)
            self.assertIn("entry_exit_signal_columns", failed_checks)
            self.assertIn("params_strategy_name_matches_class", failed_checks)
            self.assertFalse(result.sop_step.advances)


if __name__ == "__main__":
    unittest.main()
