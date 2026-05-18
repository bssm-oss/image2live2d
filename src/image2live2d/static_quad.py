from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .contracts import CapabilityClassification, SAFE_ID_PATTERN, validate_model3_bundle
from .runtime import run_runtime_smoke
from .storage import ensure_dir, now_iso, write_json


def generate_static_quad_live2d(
    input_image: Path,
    output_dir: Path,
    *,
    model_name: str = "static_quad",
    core_js_path: Path | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Generate a genuine but static one-ArtMesh Live2D runtime bundle from a PNG.

    This is intentionally not a rigging pipeline. The generated model is a single
    textured quad whose `.moc3` must still pass the normal runtime smoke before it
    can be classified as runtime-loadable.
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
            errors=[{"code": "png_required", "messages": ["experimental static quad generation currently requires a PNG input"]}],
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
            errors=[{"code": "node_not_found", "messages": ["node is required for the static quad generator"]}],
        )

    ensure_dir(output_dir)
    script = Path(__file__).resolve().parents[2] / "scripts" / "static_quad_live2d.mjs"
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

    model3_path = output_dir / f"{model_name}.model3.json"
    if completed.returncode != 0:
        return _write_report(
            output_dir,
            status="failed",
            classification=CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED,
            errors=[{"code": "static_quad_generation_failed", "messages": [completed.stderr.strip() or "generator failed"]}],
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

    runtime_result = None
    classification = CapabilityClassification.CONTRACT_BUNDLE_SHAPE_VALIDATED
    status = "completed"
    errors: list[dict[str, Any]] = []
    if core_js_path is not None:
        runtime_result = run_runtime_smoke(model3_path, output_dir / "runtime_smoke.json", core_js_path=core_js_path)
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
        "generator_mode": "experimental_static_quad",
        "model3_path": str(model3_path.resolve()) if model3_path is not None else None,
        "runtime_result": runtime_result,
        "errors": errors,
        "logs": logs or [],
        "limitations": [
            "This is a genuine static Live2D runtime bundle when runtime smoke passes.",
            "It is not a rigged character model and does not infer parts, deformers, physics, or motions from the image.",
        ],
        "created_at": now_iso(),
    }
    write_json(output_dir / "static_quad_report.json", report)
    return report
