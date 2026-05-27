import sys
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai_runtime/mcp"))

from ai_ouyi_mcp.client import AiOuyiWebClient


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
        self.assertFalse(result.sop_step.advances)


if __name__ == "__main__":
    unittest.main()
