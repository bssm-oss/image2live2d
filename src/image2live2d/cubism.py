from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .contracts import CapabilityClassification, validate_export_request, validate_model3_bundle, validate_real_export_provenance
from .runtime import run_runtime_smoke
from .storage import ensure_dir, now_iso, read_json, write_json, write_text


DEFAULT_EXPORT_TIMEOUT_SECONDS = 120
COMMON_MACOS_EDITOR_PATHS = [
    "/Applications/Live2D Cubism 5 Editor.app",
    "/Applications/Live2D Cubism 4 Editor.app",
    "/Applications/Live2D Cubism Editor.app",
    str(Path.home() / "Applications/Live2D Cubism 5 Editor.app"),
    str(Path.home() / "Applications/Live2D Cubism 4 Editor.app"),
]
KNOWN_CUBISM_COMMANDS = ["CubismEditor", "CubismEditor5", "CubismEditor4", "Live2D", "live2d", "moc3", "CubismMoc3", "csm", "csmc"]


def run_export(export_request_path: Path, export_result_path: Path, *, timeout_seconds: int | None = None) -> dict[str, Any]:
    request = read_json(export_request_path)
    errors = validate_export_request(request)
    if errors:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "invalid_export_request",
            errors,
        )

    command = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
    if not command:
        return _run_demo_adapter(request, export_result_path)
    return _run_real_command(
        command,
        request,
        export_request_path,
        export_result_path,
        timeout_seconds=timeout_seconds or DEFAULT_EXPORT_TIMEOUT_SECONDS,
    )


def probe_export_command(command: str | None = None) -> dict[str, Any]:
    """Probe the configured Cubism export command without running an export.

    Commands may support the optional convention:
    `<command> --probe <probe_result_json>`.
    If they do not, this still reports whether the executable is present.
    """
    command = command if command is not None else os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
    if not command:
        return {
            "version": "1",
            "status": "missing_env",
            "available": False,
            "command": None,
            "supports_probe": False,
            "errors": ["LIVE2D_CUBISM_EXPORT_COMMAND is not set"],
            "created_at": now_iso(),
        }

    parts = shlex.split(command, posix=os.name != "nt")
    if not parts:
        return {
            "version": "1",
            "status": "empty_command",
            "available": False,
            "command": command,
            "supports_probe": False,
            "errors": ["LIVE2D_CUBISM_EXPORT_COMMAND is empty"],
            "created_at": now_iso(),
        }

    executable = parts[0]
    executable_error = _executable_error(executable)
    if executable_error:
        return {
            "version": "1",
            "status": executable_error[0],
            "available": False,
            "command": command,
            "supports_probe": False,
            "errors": [executable_error[1]],
            "created_at": now_iso(),
        }

    with tempfile.TemporaryDirectory() as tmp:
        probe_result_path = Path(tmp) / "probe_result.json"
        try:
            completed = subprocess.run(
                [*parts, "--probe", str(probe_result_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "version": "1",
                "status": "probe_timeout",
                "available": True,
                "command": command,
                "supports_probe": False,
                "errors": [str(exc)],
                "created_at": now_iso(),
            }
        except OSError as exc:
            return {
                "version": "1",
                "status": "probe_execution_failed",
                "available": False,
                "command": command,
                "supports_probe": False,
                "errors": [str(exc)],
                "created_at": now_iso(),
            }

        if probe_result_path.exists():
            try:
                result = read_json(probe_result_path)
            except Exception as exc:
                return {
                    "version": "1",
                    "status": "malformed_probe_result",
                    "available": True,
                    "command": command,
                    "supports_probe": True,
                    "errors": [str(exc)],
                    "created_at": now_iso(),
                }
            return {
                **result,
                "version": result.get("version", "1"),
                "available": result.get("available", completed.returncode == 0),
                "command": command,
                "supports_probe": True,
                "created_at": result.get("created_at", now_iso()),
            }

    return {
        "version": "1",
        "status": "command_available_probe_unsupported",
        "available": True,
        "command": command,
        "supports_probe": False,
        "errors": [],
        "created_at": now_iso(),
    }


def preflight_real_export(input_path: Path | None = None, command: str | None = None) -> dict[str, Any]:
    command_value = command if command is not None else os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
    configured_editor = os.environ.get("LIVE2D_CUBISM_EDITOR_PATH")
    editor_candidates = _editor_candidates(configured_editor)
    found_editors = [path for path in editor_candidates if Path(path).exists()]
    path_commands = {name: shutil.which(name) for name in KNOWN_CUBISM_COMMANDS if shutil.which(name)}

    blockers: list[dict[str, str]] = []
    warnings: list[str] = [
        "Official Live2D guidance says cmo3 -> moc3 command-line export is not supported.",
        "A single flat image is not enough for a production Live2D model; a rigged .cmo3 or layered PSD plus Cubism rigging is required.",
    ]

    if input_path is not None:
        if not input_path.exists():
            blockers.append({"code": "input_not_found", "message": f"input not found: {input_path}"})
        elif input_path.suffix.lower() not in {".cmo3", ".psd"}:
            blockers.append(
                {
                    "code": "flat_image_not_rigged_source",
                    "message": "input is not a rigged .cmo3 project or layered .psd source that Cubism can export",
                }
            )

    if not command_value:
        blockers.append({"code": "missing_export_command", "message": "LIVE2D_CUBISM_EXPORT_COMMAND is not set"})
    if not found_editors:
        blockers.append({"code": "cubism_editor_not_found", "message": "Live2D Cubism Editor was not found in configured/common paths"})

    adapter_probe = probe_export_command(command_value) if command_value else None
    if adapter_probe and adapter_probe.get("available") is not True:
        blockers.append({"code": "adapter_unavailable", "message": f"adapter probe status: {adapter_probe.get('status')}"})

    return {
        "version": "1",
        "ready": not blockers,
        "status": "ready" if not blockers else "blocked",
        "input_path": str(input_path) if input_path is not None else None,
        "configured_export_command": command_value,
        "configured_editor_path": configured_editor,
        "editor_candidates": editor_candidates,
        "found_editors": found_editors,
        "path_commands": path_commands,
        "adapter_probe": adapter_probe,
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": _real_export_next_actions(blockers),
        "created_at": now_iso(),
    }


def _run_demo_adapter(request: dict[str, Any], export_result_path: Path) -> dict[str, Any]:
    bundle_dir = ensure_dir(Path(request["output_bundle_dir"]) / "demo_fixture_bundle")
    textures_dir = ensure_dir(bundle_dir / "textures")
    moc_marker = write_text(
        bundle_dir / "fixture-non-production.moc3.txt",
        "This is not a real .moc3. It exists only to validate local wiring.\n",
    )
    texture_marker = write_text(textures_dir / "texture_00.txt", "not a texture; demo fixture only\n")
    model3_path = write_json(
        bundle_dir / "fixture.model3.json",
        {
            "Version": 3,
            "FileReferences": {
                "Moc": moc_marker.name,
                "Textures": ["textures/texture_00.txt"],
            },
            "Meta": {
                "NonProductionFixture": True,
                "GeneratedBy": "image2live2d demo adapter",
            },
        },
    )
    write_text(
        bundle_dir / "README_NON_PRODUCTION.txt",
        "Demo fixture only. This bundle cannot satisfy real Cubism export validation.\n",
    )

    result = {
        "version": "1",
        "job_id": request["job_id"],
        "status": "ok",
        "classification": CapabilityClassification.DEMO_FIXTURE.value,
        "cubism_mode": "demo_adapter",
        "non_production_fixture": True,
        "bundle_dir": str(bundle_dir),
        "model3_path": str(model3_path),
        "generated_files": [str(model3_path), str(moc_marker), str(texture_marker)],
        "validation": {
            "passed": False,
            "errors": ["demo fixture cannot satisfy real export validation"],
        },
        "logs": ["LIVE2D_CUBISM_EXPORT_COMMAND was not set; demo adapter used."],
        "errors": [],
        "created_at": now_iso(),
    }
    write_json(export_result_path, result)
    return result


def _run_real_command(
    command: str,
    request: dict[str, Any],
    export_request_path: Path,
    export_result_path: Path,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    parts = shlex.split(command)
    if not parts:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "empty_export_command",
            ["LIVE2D_CUBISM_EXPORT_COMMAND is empty"],
        )

    executable = parts[0]
    executable_error = _executable_error(executable)
    if executable_error:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            executable_error[0].replace("command", "export_command"),
            [executable_error[1]],
        )

    ensure_dir(Path(request["output_bundle_dir"]))
    try:
        completed = subprocess.run(
            [*parts, str(export_request_path), str(export_result_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "export_command_timeout",
            [str(exc)],
        )
    except OSError as exc:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "export_command_execution_failed",
            [str(exc)],
        )

    if completed.returncode != 0:
        if export_result_path.exists():
            try:
                result = read_json(export_result_path)
            except Exception:
                result = None
            if isinstance(result, dict):
                normalized = _normalize_adapter_failure_result(
                    result,
                    request,
                    command=command,
                    timeout_seconds=timeout_seconds,
                    logs=[completed.stdout.strip()],
                )
                write_json(export_result_path, normalized)
                return normalized
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "export_command_failed",
            [completed.stderr.strip() or f"exit code {completed.returncode}"],
            logs=[completed.stdout.strip()],
        )

    if not export_result_path.exists():
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "missing_export_result",
            ["export command did not write result JSON"],
            logs=[completed.stdout.strip()],
        )

    try:
        result = read_json(export_result_path)
    except Exception as exc:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "malformed_export_result",
            [str(exc)],
            logs=[completed.stdout.strip()],
        )

    model3_value = result.get("model3_path")
    if not isinstance(model3_value, str):
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "missing_model3_path",
            ["export result missing model3_path"],
            logs=[completed.stdout.strip()],
        )

    requested_bundle_base = Path(request["output_bundle_dir"]).resolve()
    bundle_base = Path(result.get("bundle_dir") or request["output_bundle_dir"]).resolve()
    try:
        bundle_base.relative_to(requested_bundle_base)
    except ValueError:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "bundle_dir_outside_requested_output",
            [f"bundle_dir must resolve inside requested output_bundle_dir: {bundle_base}"],
            logs=[completed.stdout.strip()],
        )
    model3_path, model3_path_errors = _resolve_model3_path(Path(model3_value), bundle_base)
    if model3_path_errors:
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "model3_path_outside_bundle",
            model3_path_errors,
            logs=[completed.stdout.strip()],
        )

    if result.get("status") != "ok":
        return _write_failure(
            export_result_path,
            CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            "adapter_reported_failure",
            ["export result status was not ok"],
            logs=[completed.stdout.strip()],
        )

    shape_passed, validation_errors = validate_model3_bundle(model3_path, forbid_fixture=True)
    provenance_errors = validate_real_export_provenance(result)
    provenance_passed = not provenance_errors
    runtime_smoke = _run_configured_runtime_smoke(model3_path, export_result_path) if shape_passed and provenance_passed else None
    runtime_loaded = runtime_smoke is not None and runtime_smoke.get("status") == "loaded"
    real_export_errors: list[str] = []
    if shape_passed and provenance_passed and runtime_smoke is None:
        real_export_errors.append("independent real Cubism/runtime verification is not configured")
    elif shape_passed and provenance_passed and not runtime_loaded:
        real_export_errors.extend(_runtime_errors(runtime_smoke))
    classification = (
        CapabilityClassification.REAL_RUNTIME_LOADED
        if runtime_loaded
        else CapabilityClassification.CONTRACT_BUNDLE_SHAPE_VALIDATED
        if shape_passed and provenance_passed
        else CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED
    )
    all_validation_errors = [] if runtime_loaded else [*validation_errors, *provenance_errors, *real_export_errors]
    normalized = {
        **result,
        "version": result.get("version", "1"),
        "job_id": result.get("job_id", request["job_id"]),
        "status": "ok" if runtime_loaded else "failed",
        "classification": classification.value,
        "cubism_mode": "real_command",
        "non_production_fixture": False,
        "model3_path": str(model3_path),
        "validation": {
            "passed": runtime_loaded,
            "bundle_shape_passed": shape_passed,
            "provenance_passed": provenance_passed,
            "runtime_smoke_passed": runtime_loaded,
            "errors": all_validation_errors,
        },
        "runtime_smoke": runtime_smoke,
        "runtime_load_status": "loaded" if runtime_loaded else "not_configured" if runtime_smoke is None else "failed",
        "logs": [*(result.get("logs") or []), completed.stdout.strip()],
        "adapter_command": command,
        "adapter_timeout_seconds": timeout_seconds,
        "errors": all_validation_errors,
        "created_at": result.get("created_at", now_iso()),
    }
    write_json(export_result_path, normalized)
    return normalized


def _write_failure(
    export_result_path: Path,
    classification: CapabilityClassification,
    code: str,
    errors: list[str],
    logs: list[str] | None = None,
) -> dict[str, Any]:
    result = {
        "version": "1",
        "status": "failed",
        "classification": classification.value,
        "cubism_mode": "real_command",
        "non_production_fixture": False,
        "bundle_dir": None,
        "model3_path": None,
        "generated_files": [],
        "validation": {"passed": False, "errors": errors},
        "logs": logs or [],
        "errors": [{"code": code, "messages": errors}],
        "created_at": now_iso(),
    }
    write_json(export_result_path, result)
    return result


def _normalize_adapter_failure_result(
    result: dict[str, Any],
    request: dict[str, Any],
    *,
    command: str,
    timeout_seconds: int,
    logs: list[str],
) -> dict[str, Any]:
    adapter_errors = result.get("errors")
    validation_errors: list[str] = []
    if isinstance(adapter_errors, list):
        for error in adapter_errors:
            if isinstance(error, dict):
                messages = error.get("messages")
                if isinstance(messages, list):
                    validation_errors.extend(str(message) for message in messages)
                elif "message" in error:
                    validation_errors.append(str(error["message"]))
            elif isinstance(error, str):
                validation_errors.append(error)
    if not validation_errors:
        validation_errors.append("adapter command failed after writing result JSON")

    result_logs = result.get("logs") if isinstance(result.get("logs"), list) else []
    return {
        **result,
        "version": result.get("version", "1"),
        "job_id": result.get("job_id", request.get("job_id")),
        "status": "failed",
        "classification": CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED.value,
        "cubism_mode": "real_command",
        "non_production_fixture": False,
        "bundle_dir": result.get("bundle_dir"),
        "model3_path": result.get("model3_path"),
        "generated_files": result.get("generated_files", []),
        "validation": {"passed": False, "errors": validation_errors},
        "logs": [*result_logs, *logs],
        "adapter_command": command,
        "adapter_timeout_seconds": timeout_seconds,
        "errors": adapter_errors if isinstance(adapter_errors, list) else validation_errors,
        "created_at": result.get("created_at", now_iso()),
    }


def _run_configured_runtime_smoke(model3_path: Path, export_result_path: Path) -> dict[str, Any] | None:
    command = os.environ.get("LIVE2D_RUNTIME_SMOKE_COMMAND")
    core_js = os.environ.get("LIVE2D_CUBISM_CORE_JS")
    if not command and not core_js:
        return None
    runtime_result_path = export_result_path.with_name("runtime_smoke_result.json")
    return run_runtime_smoke(model3_path, runtime_result_path, core_js_path=Path(core_js) if core_js else None, command=command)


def _runtime_errors(runtime_smoke: dict[str, Any] | None) -> list[str]:
    if runtime_smoke is None:
        return ["runtime smoke was not configured"]
    errors = runtime_smoke.get("errors")
    if not isinstance(errors, list) or not errors:
        return ["runtime smoke failed"]
    messages: list[str] = []
    for error in errors:
        if isinstance(error, dict):
            code = error.get("code", "runtime_smoke_failed")
            error_messages = error.get("messages")
            if isinstance(error_messages, list):
                messages.extend(f"{code}: {message}" for message in error_messages)
            else:
                messages.append(str(code))
        else:
            messages.append(str(error))
    return messages


def _executable_error(executable: str) -> tuple[str, str] | None:
    resolved = shutil.which(executable)
    if resolved is not None:
        return None
    path = Path(executable)
    if not path.exists():
        return "missing_command", f"command not found: {executable}"
    if not path.is_file():
        return "non_executable_command", f"command is not a file: {executable}"
    if not os.access(path, os.X_OK):
        return "non_executable_command", f"command is not executable: {executable}"
    return None


def _resolve_model3_path(model3_path: Path, bundle_base: Path) -> tuple[Path, list[str]]:
    resolved_base = bundle_base.resolve()
    candidates = [model3_path.resolve()] if model3_path.is_absolute() else [model3_path.resolve(), (bundle_base / model3_path).resolve()]
    for candidate in candidates:
        try:
            candidate.relative_to(resolved_base)
        except ValueError:
            continue
        return candidate, []
    return candidates[-1], [f"model3_path must resolve inside bundle_dir: {model3_path}"]


def _editor_candidates(configured_editor: str | None) -> list[str]:
    candidates: list[str] = []
    if configured_editor:
        candidates.append(configured_editor)
    if platform.system() == "Darwin":
        candidates.extend(path for path in COMMON_MACOS_EDITOR_PATHS if path not in candidates)
    return candidates


def _real_export_next_actions(blockers: list[dict[str, str]]) -> list[str]:
    codes = {blocker["code"] for blocker in blockers}
    actions: list[str] = []
    if "flat_image_not_rigged_source" in codes:
        actions.append("Create or provide a layered PSD or rigged .cmo3; a flat image cannot be exported to .moc3 directly.")
    if "cubism_editor_not_found" in codes:
        actions.append("Install Live2D Cubism Editor and set LIVE2D_CUBISM_EDITOR_PATH to the app bundle.")
    if "missing_export_command" in codes:
        actions.append("Set LIVE2D_CUBISM_EXPORT_COMMAND to an adapter that drives the official Cubism Editor workflow.")
    if "adapter_unavailable" in codes:
        actions.append("Run probe-cubism for adapter details and fix the adapter command before strict export.")
    if not actions:
        actions.append("Run demo-thin-e2e --require-real-cubism with the configured official adapter.")
    return actions
