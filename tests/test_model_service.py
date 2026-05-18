from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.model_service import ModelServiceState, ModelServiceHandler  # noqa: E402
from http.server import ThreadingHTTPServer


class ModelServiceTests(unittest.TestCase):
    def test_health_returns_ok_and_stub_provider(self) -> None:
        server, thread = self._server()
        try:
            body = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/health").read().decode("utf-8"))
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["provider_modes"], ["stub"])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_malformed_json_returns_400(self) -> None:
        server, thread = self._server()
        try:
            url = f"http://127.0.0.1:{server.server_port}/jobs"
            request = urllib.request.Request(url, data=b"{bad", headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            error = caught.exception
            self.assertEqual(error.code, 400)
            body = json.loads(error.read().decode("utf-8"))
            error.close()
            self.assertEqual(body["error"], "malformed JSON request body")
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_non_object_json_returns_400(self) -> None:
        server, thread = self._server()
        try:
            url = f"http://127.0.0.1:{server.server_port}/jobs"
            request = urllib.request.Request(url, data=b"[]", headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            error = caught.exception
            self.assertEqual(error.code, 400)
            body = json.loads(error.read().decode("utf-8"))
            error.close()
            self.assertEqual(body["error"], "JSON request body must be an object")
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_invalid_manifest_returns_400_without_writing_job(self) -> None:
        server, thread = self._server()
        try:
            url = f"http://127.0.0.1:{server.server_port}/jobs"
            manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
            manifest["job_id"] = "../bad"
            request = urllib.request.Request(
                url,
                data=json.dumps(manifest).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as missing:
                urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/jobs/../bad")
            missing.exception.close()
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_duplicate_job_id_returns_409(self) -> None:
        server, thread = self._server()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
            payload = json.dumps(manifest).encode("utf-8")
            first = urllib.request.Request(base + "/jobs", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(first).close()
            second = urllib.request.Request(base + "/jobs", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(second)
            self.assertEqual(caught.exception.code, 409)
            caught.exception.close()
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_job_lifecycle_create_get_analyze_artifacts(self) -> None:
        server, thread = self._server()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
            request = urllib.request.Request(
                base + "/jobs",
                data=json.dumps(manifest).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            created = json.loads(urllib.request.urlopen(request).read().decode("utf-8"))
            self.assertEqual(created["job_id"], "thin-e2e-example")
            stored = json.loads(urllib.request.urlopen(base + "/jobs/thin-e2e-example").read().decode("utf-8"))
            self.assertEqual(stored["manifest"]["job_id"], "thin-e2e-example")
            analyze = urllib.request.Request(base + "/jobs/thin-e2e-example/analyze", method="POST")
            analysis = json.loads(urllib.request.urlopen(analyze).read().decode("utf-8"))
            self.assertEqual(analysis["provider_mode"], "stub")
            artifacts = json.loads(urllib.request.urlopen(base + "/jobs/thin-e2e-example/artifacts").read().decode("utf-8"))
            self.assertEqual(len(artifacts["artifacts"]), 3)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def _server(self) -> tuple[ThreadingHTTPServer, threading.Thread]:
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        handler = type("TestModelServiceHandler", (ModelServiceHandler,), {})
        handler.state = ModelServiceState(Path(tmp.name))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread


if __name__ == "__main__":
    unittest.main()
