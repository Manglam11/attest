import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import httpx


def fresh_modules(tmpdir: str):
    os.environ["EVAL_DIR"] = tmpdir
    os.environ["QUOTA_DIR"] = tmpdir
    os.environ["ENGINE_URL"] = "http://engine.test"
    os.environ["PACE_SECONDS"] = "0"
    for name in ("app.quota", "app.eval.latency"):
        sys.modules.pop(name, None)
    import app.quota as quota
    import app.eval.latency as latency
    return quota, latency


class LatencySamplingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.quota, self.latency = fresh_modules(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_run_never_reuses_stored_latency(self):
        seeded = {
            "samples": [
                {"question": q, "latency_s": 999.0, "day": "2020-01-01"}
                for q in self.latency.ANSWERABLE
            ]
        }
        Path(self.tmp.name, "latency_samples.json").write_text(json.dumps(seeded))

        def handler(request):
            if request.url.path == "/health":
                return httpx.Response(200, json={"status": "alive"})
            return httpx.Response(
                200,
                json={"question": "x", "answer": "a", "tool_calls": [], "contexts": [], "latency_s": 4.2},
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        samples = self.latency.run_with_client(client, n=3)
        fresh = samples[len(self.latency.ANSWERABLE):]
        self.assertEqual(len(fresh), 3)
        for sample in fresh:
            self.assertEqual(sample["latency_s"], 4.2)
            self.assertNotEqual(sample["latency_s"], 999.0)

    def test_health_gate_blocks_on_connection_failure(self):
        def handler(request):
            raise httpx.ConnectError("connection refused", request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with self.assertRaises(self.latency.EngineUnhealthy):
            self.latency.check_health(client)

    def test_health_gate_blocks_on_bad_response(self):
        def handler(request):
            return httpx.Response(500, json={"detail": "internal error"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with self.assertRaises(self.latency.EngineUnhealthy):
            self.latency.check_health(client)

    def test_quota_gate_blocks_on_worst_case_not_average(self):
        Path(self.tmp.name, "agent_calls.json").write_text(
            json.dumps({"date": self.quota._today(), "count": 17})
        )
        history = [{"question": "q", "calls_this_ask": c} for c in (2, 2, 2, 3, 2)]
        self.latency.check_quota(history)
        history.append({"question": "q", "calls_this_ask": 4})
        with self.assertRaises(self.latency.QuotaExceeded):
            self.latency.check_quota(history)

    def test_quota_gate_falls_back_to_measured_default_with_no_history(self):
        Path(self.tmp.name, "agent_calls.json").write_text(
            json.dumps({"date": self.quota._today(), "count": 17})
        )
        with self.assertRaises(self.latency.QuotaExceeded):
            self.latency.check_quota([])


if __name__ == "__main__":
    unittest.main()
