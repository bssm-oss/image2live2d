from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .contracts import CapabilityClassification, validate_job_manifest
from .cubism import run_export
from .providers import run_stub_analysis
from .storage import ensure_dir, now_iso, read_json, write_json, write_text


def create_manifest(input_image: Path, output_dir: Path, *, job_id: str | None = None) -> dict[str, Any]:
    job_id = job_id or f"thin-e2e-{uuid.uuid4().hex[:8]}"
    return {
        "version": "1",
        "job_id": job_id,
        "created_at": now_iso(),
        "input": {
            "image_path": str(input_image),
            "declared_scope": "curated anime-style sample for thin e2e validation",
        },
        "output_dir": str(output_dir),
        "requested_parts": ["head", "face", "eyes", "mouth", "hair", "torso"],
        "quality_thresholds": {
            "min_layer_confidence": 0.60,
            "requires_capability_classification": True,
        },
        "cubism_adapter": {
            "mode": "env_or_demo",
            "require_real_export": False,
            "timeout_seconds": 120,
            "expected_outputs": ["model3.json", "moc3", "textures"],
        },
    }


def run_thin_e2e(
    input_image: Path,
    output_dir: Path,
    *,
    require_real_cubism: bool = False,
    export_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    if not input_image.exists():
        raise ValueError(f"input image not found: {input_image}")
    output_dir = ensure_dir(output_dir)
    manifest = create_manifest(input_image, output_dir)
    manifest_errors = validate_job_manifest(manifest)
    if manifest_errors:
        raise ValueError("Invalid manifest: " + "; ".join(manifest_errors))
    manifest_path = write_json(output_dir / "job_manifest.json", manifest)

    analysis = run_stub_analysis(manifest, output_dir)
    adapter_config = manifest.get("cubism_adapter", {})
    expected_outputs = adapter_config.get("expected_outputs", ["model3.json", "moc3", "textures"])
    timeout_seconds = export_timeout_seconds or int(adapter_config.get("timeout_seconds", 120))
    export_request = {
        "version": "1",
        "job_id": manifest["job_id"],
        "source_image": manifest["input"]["image_path"],
        "layer_plan_path": analysis["layer_plan_path"],
        "intermediate_asset_path": analysis["intermediate_asset_path"],
        "output_bundle_dir": str(output_dir / "cubism"),
        "expected_outputs": expected_outputs,
    }
    export_request_path = write_json(output_dir / "export_request.json", export_request)
    export_result_path = output_dir / "export_result.json"
    export_result = run_export(export_request_path, export_result_path, timeout_seconds=timeout_seconds)

    classification = export_result.get("classification", CapabilityClassification.DEMO_FIXTURE.value)
    preview_metadata = {
        "version": "1",
        "job_id": manifest["job_id"],
        "classification": classification,
        "model3_path": export_result.get("model3_path"),
        "bundle_dir": export_result.get("bundle_dir"),
        "runtime_load_status": export_result.get("runtime_load_status", "not_attempted"),
        "runtime_smoke": export_result.get("runtime_smoke"),
        "known_limitations": _limitations_for(classification),
    }
    preview_metadata_path = write_json(output_dir / "preview_metadata.json", preview_metadata)

    artifact_list = [
        str(manifest_path),
        *analysis["artifact_paths"],
        str(export_request_path),
        str(export_result_path),
        str(preview_metadata_path),
    ]
    artifact_list.extend(export_result.get("generated_files") or [])

    report = {
        "version": "1",
        "job_id": manifest["job_id"],
        "created_at": now_iso(),
        "status": _report_status(str(classification), export_result, require_real_cubism),
        "capability_classification": classification,
        "provider_mode": analysis["provider_mode"],
        "cubism_mode": export_result.get("cubism_mode"),
        "require_real_cubism": require_real_cubism,
        "adapter_command_configured": export_result.get("cubism_mode") == "real_command",
        "adapter_timeout_seconds": export_result.get("adapter_timeout_seconds", timeout_seconds),
        "artifact_list": artifact_list,
        "validation_status": export_result.get("validation"),
        "runtime_smoke": export_result.get("runtime_smoke"),
        "explicit_limitations": _limitations_for(classification),
    }
    report_path = write_json(output_dir / "final_report.json", report)
    write_text(output_dir / "final_report.md", _format_report(report, export_result))
    report["report_path"] = str(report_path)
    return report


def _limitations_for(classification: str) -> list[str]:
    if classification == CapabilityClassification.DEMO_FIXTURE.value:
        return [
            "Demo fixture only; no real segmentation, Cubism export, or runtime model quality is claimed.",
            "Set LIVE2D_CUBISM_EXPORT_COMMAND to attempt official Cubism automation.",
        ]
    if classification == CapabilityClassification.REAL_CUBISM_EXPORT_ATTEMPTED.value:
        return ["Official Cubism automation was attempted but real bundle validation failed."]
    if classification == CapabilityClassification.CONTRACT_BUNDLE_SHAPE_VALIDATED.value:
        return [
            "A bundle-shaped result was produced, but independent real Cubism/runtime verification did not pass.",
            "This is not accepted as a real image-to-Live2D export.",
        ]
    if classification == CapabilityClassification.REAL_CUBISM_EXPORT_VALIDATED.value:
        return ["Official Cubism provenance and bundle files validated; browser runtime smoke may still be required."]
    if classification == CapabilityClassification.REAL_RUNTIME_LOADED.value:
        return ["An existing bundle loaded through runtime smoke; this still does not prove image-to-Live2D generation."]
    return []


def _report_status(classification: str, export_result: dict[str, Any], require_real_cubism: bool) -> str:
    if export_result.get("status") == "failed":
        return "failed"
    if require_real_cubism and classification not in (
        CapabilityClassification.REAL_RUNTIME_LOADED.value,
    ):
        return "failed"
    return "completed"


def _format_report(report: dict[str, Any], export_result: dict[str, Any]) -> str:
    lines = [
        f"# image2live2d Run Report: {report['job_id']}",
        "",
        f"- Status: `{report['status']}`",
        f"- Capability: `{report['capability_classification']}`",
        f"- Provider mode: `{report['provider_mode']}`",
        f"- Cubism mode: `{report['cubism_mode']}`",
        "",
        "## Validation",
        "",
        f"```json\n{export_result.get('validation')}\n```",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in report["explicit_limitations"])
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.extend(f"- `{item}`" for item in report["artifact_list"])
    lines.append("")
    return "\n".join(lines)


def load_final_report(path: Path) -> dict[str, Any]:
    return read_json(path)
