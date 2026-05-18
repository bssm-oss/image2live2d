from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .contracts import validate_job_manifest
from .providers import run_stub_analysis
from .storage import ensure_dir, write_json


class ModelServiceState:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = ensure_dir(output_dir)
        self.jobs: dict[str, dict[str, Any]] = {}


class ModelServiceHandler(BaseHTTPRequestHandler):
    state: ModelServiceState
    max_body_bytes = 1_000_000

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"status": "ok", "provider_modes": ["stub"]})
            return

        parts = parsed.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "jobs":
            job = self.state.jobs.get(parts[1])
            self._json(200 if job else 404, job or {"error": "job not found"})
            return

        if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "artifacts":
            job = self.state.jobs.get(parts[1])
            if not job:
                self._json(404, {"error": "job not found"})
                return
            self._json(200, {"job_id": parts[1], "artifacts": job.get("artifacts", [])})
            return

        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            body = self._read_body()
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return

        if parsed.path == "/jobs":
            errors = validate_job_manifest(body)
            if errors:
                self._json(400, {"errors": errors})
                return
            job_id = body["job_id"]
            if job_id in self.state.jobs:
                self._json(409, {"error": "job already exists", "job_id": job_id})
                return
            job_dir = ensure_dir(self.state.output_dir / job_id)
            manifest_path = write_json(job_dir / "job_manifest.json", body)
            self.state.jobs[job_id] = {"manifest": body, "manifest_path": str(manifest_path), "artifacts": []}
            self._json(201, {"job_id": job_id, "manifest_path": str(manifest_path)})
            return

        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "jobs" and parts[2] == "analyze":
            job = self.state.jobs.get(parts[1])
            if not job:
                self._json(404, {"error": "job not found"})
                return
            job_dir = ensure_dir(self.state.output_dir / parts[1])
            result = run_stub_analysis(job["manifest"], job_dir)
            job["artifacts"] = result["artifact_paths"]
            self._json(200, result)
            return

        self._json(404, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length > self.max_body_bytes:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("malformed JSON request body") from exc
        if not isinstance(parsed, dict):
            raise ValueError("JSON request body must be an object")
        return parsed

    def _json(self, status: int, data: dict[str, Any]) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(host: str, port: int, output_dir: Path) -> None:
    handler = type("ConfiguredModelServiceHandler", (ModelServiceHandler,), {})
    handler.state = ModelServiceState(output_dir)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"model service listening on http://{host}:{port}")
    server.serve_forever()
