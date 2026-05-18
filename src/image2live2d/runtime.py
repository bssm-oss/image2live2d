from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .contracts import validate_model3_bundle
from .storage import now_iso, read_json, write_json


DEFAULT_RUNTIME_TIMEOUT_SECONDS = 30


def run_runtime_smoke(
    model3_path: Path,
    result_path: Path,
    *,
    core_js_path: Path | None = None,
    command: str | None = None,
    timeout_seconds: int = DEFAULT_RUNTIME_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    shape_passed, shape_errors = validate_model3_bundle(model3_path, forbid_fixture=True, require_binary_signatures=True)
    if not shape_passed:
        return _write_runtime_result(
            result_path,
            status="failed",
            errors=[{"code": "bundle_validation_failed", "messages": shape_errors}],
            model3_path=model3_path,
            logs=[],
        )

    command_parts, extra_args_or_error = _runtime_command_parts(command, core_js_path)
    if isinstance(extra_args_or_error, dict):
        return _write_runtime_result(result_path, status="failed", errors=[extra_args_or_error], model3_path=model3_path, logs=[])

    try:
        completed = subprocess.run(
            [*command_parts, str(model3_path), str(result_path), *extra_args_or_error],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return _write_runtime_result(
            result_path,
            status="failed",
            errors=[{"code": "runtime_smoke_timeout", "messages": [str(exc)]}],
            model3_path=model3_path,
            logs=[],
        )
    except OSError as exc:
        return _write_runtime_result(
            result_path,
            status="failed",
            errors=[{"code": "runtime_smoke_execution_failed", "messages": [str(exc)]}],
            model3_path=model3_path,
            logs=[],
        )

    if not result_path.exists():
        return _write_runtime_result(
            result_path,
            status="failed",
            errors=[{"code": "missing_runtime_smoke_result", "messages": ["runtime smoke command did not write result JSON"]}],
            model3_path=model3_path,
            logs=[completed.stdout.strip()],
        )

    try:
        result = read_json(result_path)
    except Exception as exc:
        return _write_runtime_result(
            result_path,
            status="failed",
            errors=[{"code": "malformed_runtime_smoke_result", "messages": [str(exc)]}],
            model3_path=model3_path,
            logs=[completed.stdout.strip()],
        )

    expected_model3 = str(model3_path.resolve())
    reported_model3 = Path(str(result.get("model3_path", ""))).resolve() if result.get("model3_path") else None
    passed = completed.returncode == 0 and result.get("status") == "loaded" and result.get("consistency_passed") is True and reported_model3 == Path(expected_model3)
    normalized = {
        **result,
        "version": result.get("version", "1"),
        "status": "loaded" if passed else "failed",
        "model3_path": expected_model3,
        "runtime_load_status": "loaded" if passed else "failed",
        "logs": [*(result.get("logs") or []), completed.stdout.strip()],
        "errors": result.get("errors", []) if passed else _runtime_failure_errors(result, completed.stderr),
        "created_at": result.get("created_at", now_iso()),
    }
    write_json(result_path, normalized)
    return normalized


def _runtime_command_parts(command: str | None, core_js_path: Path | None) -> tuple[list[str], list[str] | dict[str, Any]]:
    if command:
        parts = shlex.split(command, posix=os.name != "nt")
        extra_args: list[str] = []
    else:
        script = Path(__file__).resolve().parents[2] / "scripts" / "live2d_runtime_smoke.js"
        node = shutil.which("node")
        if node is None:
            return [], {"code": "node_not_found", "messages": ["node is required for the built-in Cubism Core runtime smoke"]}
        core = core_js_path or (Path(os.environ["LIVE2D_CUBISM_CORE_JS"]) if os.environ.get("LIVE2D_CUBISM_CORE_JS") else None)
        if core is None:
            return [], {"code": "cubism_core_not_configured", "messages": ["set --core-js or LIVE2D_CUBISM_CORE_JS to live2dcubismcore.min.js"]}
        parts = [node, str(script)]
        extra_args = ["--core-js", str(core)]

    if not parts:
        return [], {"code": "empty_runtime_smoke_command", "messages": ["runtime smoke command is empty"]}
    executable = parts[0]
    if shutil.which(executable) is None and not Path(executable).exists():
        return [], {"code": "runtime_smoke_command_not_found", "messages": [f"command not found: {executable}"]}
    return parts, extra_args


def _runtime_failure_errors(result: dict[str, Any], stderr: str) -> list[dict[str, Any]]:
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        return errors
    if result.get("consistency_passed") is not True:
        return [{"code": "runtime_consistency_not_proven", "messages": ["runtime smoke did not report consistency_passed=true"]}]
    return [{"code": "runtime_smoke_failed", "messages": [stderr.strip() or "runtime smoke failed"]}]


def _write_runtime_result(
    result_path: Path,
    *,
    status: str,
    errors: list[dict[str, Any]],
    model3_path: Path,
    logs: list[str],
) -> dict[str, Any]:
    result = {
        "version": "1",
        "status": status,
        "runtime_load_status": "loaded" if status == "loaded" else "failed",
        "model3_path": str(model3_path.resolve()),
        "errors": errors,
        "logs": logs,
        "created_at": now_iso(),
    }
    write_json(result_path, result)
    return result
