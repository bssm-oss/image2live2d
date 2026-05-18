from __future__ import annotations

import shutil
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any

from .contracts import CapabilityClassification, SAFE_ID_PATTERN, validate_model3_bundle
from .runtime import run_runtime_smoke
from .storage import ensure_dir, now_iso, write_json


def generate_auto_rig_live2d(
    input_image: Path,
    output_dir: Path,
    *,
    model_name: str = "auto_rig",
    core_js_path: Path | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Generate a heuristic multi-part Live2D runtime bundle from a PNG.

    The generated bundle contains multiple ArtMeshes, warp deformers, standard
    parameters, an idle motion, and physics settings. It is runtime-validated
    when a Cubism Core JS path is supplied. The decomposition is geometric and
    heuristic, not learned semantic segmentation.
    """
    if not input_image.exists():
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "input_not_found", "messages": [f"input image not found: {input_image}"]}],
        )
    if input_image.suffix.lower() != ".png":
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "png_required", "messages": ["heuristic auto-rig generation currently requires a PNG input"]}],
        )
    if SAFE_ID_PATTERN.fullmatch(model_name) is None:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "invalid_model_name", "messages": ["model name must be 1-128 safe characters: letters, digits, _, ., -"]}],
        )

    node = shutil.which("node")
    if node is None:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "node_not_found", "messages": ["node is required for the heuristic auto-rig generator"]}],
        )

    ensure_dir(output_dir)
    script = _generator_script_path()
    try:
        completed = subprocess.run(
            [
                node,
                str(script),
                "--input-image",
                str(input_image),
                "--output-dir",
                str(output_dir),
                "--model-name",
                model_name,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "auto_rig_generation_timeout", "messages": [str(exc)]}],
        )
    except OSError as exc:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "auto_rig_execution_failed", "messages": [str(exc)]}],
        )

    model3_path = output_dir / f"{model_name}.model3.json"
    if completed.returncode != 0:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "auto_rig_generation_failed", "messages": [completed.stderr.strip() or "generator failed"]}],
            logs=[completed.stdout.strip()],
            model3_path=model3_path,
        )

    shape_passed, shape_errors = validate_model3_bundle(model3_path, forbid_fixture=True, require_binary_signatures=True)
    if not shape_passed:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "bundle_validation_failed", "messages": shape_errors}],
            logs=[completed.stdout.strip()],
            model3_path=model3_path,
        )

    aux_errors = _validate_auto_rig_auxiliary_files(model3_path, model_name)
    if aux_errors:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "auxiliary_validation_failed", "messages": aux_errors}],
            logs=[completed.stdout.strip()],
            model3_path=model3_path,
        )

    runtime_result = None
    classification = CapabilityClassification.CONTRACT_BUNDLE_SHAPE_VALIDATED
    status = "completed"
    errors: list[dict[str, Any]] = []
    if core_js_path is not None:
        runtime_result = run_runtime_smoke(model3_path, output_dir / "runtime_smoke.json", core_js_path=core_js_path, timeout_seconds=timeout_seconds)
        if runtime_result.get("status") == "loaded":
            classification = CapabilityClassification.REAL_RUNTIME_LOADED
        else:
            status = "failed"
            classification = CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED
            errors = runtime_result.get("errors", [])

    return _write_report(
        output_dir,
        status=status,
        classification=classification,
        errors=errors,
        logs=[completed.stdout.strip()],
        model3_path=model3_path,
        runtime_result=runtime_result,
    )


def _generator_script_path() -> Path:
    packaged = Path(str(files("image2live2d").joinpath("js/auto_rig_live2d.mjs")))
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "scripts" / "auto_rig_live2d.mjs"


def _validate_auto_rig_auxiliary_files(model3_path: Path, model_name: str) -> list[str]:
    import json

    errors: list[str] = []
    bundle = model3_path.parent
    motion_path = bundle / "motions" / "idle.motion3.json"
    physics_path = bundle / f"{model_name}.physics3.json"
    cdi_path = bundle / f"{model_name}.cdi3.json"
    plan_path = bundle / "auto_rig_plan.json"

    try:
        motion = json.loads(motion_path.read_text(encoding="utf-8"))
        curves = motion.get("Curves")
        meta = motion.get("Meta", {})
        if not isinstance(curves, list) or meta.get("CurveCount") != len(curves):
            errors.append("idle.motion3.json Meta.CurveCount must match Curves length")
        for curve in curves if isinstance(curves, list) else []:
            if curve.get("Target") != "Parameter" or not isinstance(curve.get("Id"), str) or not isinstance(curve.get("Segments"), list):
                errors.append("idle.motion3.json curves must target parameter IDs with segment arrays")
                break
    except Exception as exc:
        errors.append(f"idle.motion3.json is invalid: {exc}")

    try:
        physics = json.loads(physics_path.read_text(encoding="utf-8"))
        settings = physics.get("PhysicsSettings")
        meta = physics.get("Meta", {})
        if not isinstance(settings, list) or meta.get("PhysicsSettingCount") != len(settings):
            errors.append("physics3.json Meta.PhysicsSettingCount must match PhysicsSettings length")
        total_inputs = 0
        total_outputs = 0
        total_vertices = 0
        for setting in settings if isinstance(settings, list) else []:
            inputs = setting.get("Input")
            outputs = setting.get("Output")
            vertices = setting.get("Vertices")
            if not isinstance(inputs, list) or not isinstance(outputs, list) or not isinstance(vertices, list):
                errors.append("physics3.json settings must contain Input, Output, and Vertices arrays")
                break
            total_inputs += len(inputs)
            total_outputs += len(outputs)
            total_vertices += len(vertices)
        if meta.get("TotalInputCount") != total_inputs or meta.get("TotalOutputCount") != total_outputs or meta.get("VertexCount") != total_vertices:
            errors.append("physics3.json Meta totals must match setting array counts")
    except Exception as exc:
        errors.append(f"physics3.json is invalid: {exc}")

    try:
        cdi = json.loads(cdi_path.read_text(encoding="utf-8"))
        if not isinstance(cdi.get("Parameters"), list) or not all(isinstance(item.get("Id"), str) for item in cdi.get("Parameters", [])):
            errors.append("cdi3.json Parameters must be an array of string IDs")
        if not isinstance(cdi.get("Parts"), list) or not all(isinstance(item.get("Id"), str) for item in cdi.get("Parts", [])):
            errors.append("cdi3.json Parts must be an array of string IDs")
    except Exception as exc:
        errors.append(f"cdi3.json is invalid: {exc}")

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(plan.get("parts"), list) or len(plan["parts"]) < 8:
            errors.append("auto_rig_plan.json must describe generated heuristic parts")
    except Exception as exc:
        errors.append(f"auto_rig_plan.json is invalid: {exc}")

    return errors


def _write_report(
    output_dir: Path,
    *,
    status: str,
    classification: CapabilityClassification,
    errors: list[dict[str, Any]],
    logs: list[str] | None = None,
    model3_path: Path | None = None,
    runtime_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = {
        "version": "1",
        "status": status,
        "capability_classification": classification.value,
        "generator_mode": "heuristic_auto_rig",
        "model3_path": str(model3_path.resolve()) if model3_path is not None else None,
        "runtime_result": runtime_result,
        "errors": errors,
        "logs": logs or [],
        "generated_features": [
            "heuristic-region-artmeshes",
            "warp-deformers",
            "expression-parameters",
            "standard-parameters",
            "idle-motion",
            "physics-settings",
        ],
        "limitations": [
            "This is a runtime-loadable generated Live2D bundle when runtime smoke passes.",
            "Part decomposition is heuristic layout-based, not learned pixel-accurate semantic segmentation.",
            "It creates a usable generated rig scaffold, but does not guarantee commercial-quality full rigging for arbitrary images.",
        ],
        "created_at": now_iso(),
    }
    write_json(output_dir / "auto_rig_report.json", report)
    return report
