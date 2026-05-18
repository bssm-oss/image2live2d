from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import re
from typing import Any


class CapabilityClassification(StrEnum):
    DEMO_FIXTURE = "demo_fixture"
    CONTRACT_BUNDLE_SHAPE_VALIDATED = "contract_bundle_shape_validated"
    REAL_CUBISM_EXPORT_ATTEMPTED = "real_cubism_export_attempted"
    REAL_CUBISM_EXPORT_VALIDATED = "real_cubism_export_validated"
    REAL_RUNTIME_LOADED = "real_runtime_loaded"


ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MOC3_MAGIC = b"MOC3"
MIN_REASONABLE_MOC3_BYTES = 64
TEXTURE_SIGNATURES = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".webp": b"RIFF",
}


def require_fields(data: dict[str, Any], fields: list[str], label: str) -> list[str]:
    return [f"{label}.{field} is required" for field in fields if field not in data]


def validate_job_manifest(data: dict[str, Any]) -> list[str]:
    errors = require_fields(data, ["version", "job_id", "input", "output_dir"], "manifest")
    job_id = data.get("job_id")
    if not isinstance(job_id, str) or SAFE_ID_PATTERN.fullmatch(job_id) is None:
        errors.append("manifest.job_id must be 1-128 safe characters: letters, digits, _, ., -")
    input_data = data.get("input")
    if not isinstance(input_data, dict):
        errors.append("manifest.input must be an object")
        return errors

    errors.extend(require_fields(input_data, ["image_path"], "manifest.input"))
    image_path = input_data.get("image_path")
    if not isinstance(image_path, str) or not image_path:
        errors.append("manifest.input.image_path must be a non-empty string")
    else:
        suffix = Path(image_path).suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            errors.append(f"manifest.input.image_path has unsupported suffix: {suffix}")

    output_dir = data.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        errors.append("manifest.output_dir must be a non-empty string")
    return errors


def validate_layer_plan(data: dict[str, Any]) -> list[str]:
    errors = require_fields(data, ["version", "job_id", "source_image", "provider_mode", "parts"], "layer_plan")
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        errors.append("layer_plan.parts must be a non-empty list")
        return errors

    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            errors.append(f"layer_plan.parts[{index}] must be an object")
            continue
        errors.extend(
            require_fields(
                part,
                ["name", "group", "draw_order", "confidence", "manual_correction_notes"],
                f"layer_plan.parts[{index}]",
            )
        )
    return errors


def validate_export_request(data: dict[str, Any]) -> list[str]:
    errors = require_fields(
        data,
        [
            "version",
            "job_id",
            "source_image",
            "layer_plan_path",
            "intermediate_asset_path",
            "output_bundle_dir",
            "expected_outputs",
        ],
        "export_request",
    )

    job_id = data.get("job_id")
    if not isinstance(job_id, str) or SAFE_ID_PATTERN.fullmatch(job_id) is None:
        errors.append("export_request.job_id must be 1-128 safe characters: letters, digits, _, ., -")

    for field in ("source_image", "layer_plan_path", "intermediate_asset_path", "output_bundle_dir"):
        value = data.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"export_request.{field} must be a non-empty string")

    expected_outputs = data.get("expected_outputs")
    allowed_outputs = {"model3.json", "moc3", "textures", "physics", "pose", "motions"}
    if not isinstance(expected_outputs, list) or not expected_outputs:
        errors.append("export_request.expected_outputs must be a non-empty list")
    else:
        for output in expected_outputs:
            if not isinstance(output, str) or output not in allowed_outputs:
                errors.append(f"export_request.expected_outputs contains unsupported value: {output}")

    return errors


def referenced_runtime_files(model3: dict[str, Any]) -> list[str]:
    refs = model3.get("FileReferences", {})
    files: list[str] = []

    moc = refs.get("Moc")
    if isinstance(moc, str):
        files.append(moc)

    textures = refs.get("Textures", [])
    if isinstance(textures, list):
        files.extend(path for path in textures if isinstance(path, str))

    for key in ("Physics", "Pose", "DisplayInfo"):
        value = refs.get(key)
        if isinstance(value, str):
            files.append(value)

    motions = refs.get("Motions", {})
    if isinstance(motions, dict):
        for motion_list in motions.values():
            if not isinstance(motion_list, list):
                continue
            for motion in motion_list:
                if isinstance(motion, dict) and isinstance(motion.get("File"), str):
                    files.append(motion["File"])

    return files


def validate_model3_bundle(
    model3_path: Path,
    *,
    forbid_fixture: bool = True,
    require_binary_signatures: bool = True,
) -> tuple[bool, list[str]]:
    import json

    errors: list[str] = []
    if not model3_path.exists():
        return False, [f"model3.json not found: {model3_path}"]

    try:
        model3 = json.loads(model3_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"model3.json is invalid JSON: {exc}"]

    if forbid_fixture and model3.get("Meta", {}).get("NonProductionFixture") is True:
        errors.append("demo fixture cannot satisfy real export validation")

    refs = model3.get("FileReferences")
    if not isinstance(refs, dict):
        errors.append("model3.json missing FileReferences object")
        return False, errors

    moc = refs.get("Moc")
    if not isinstance(moc, str) or not moc.endswith(".moc3"):
        errors.append("FileReferences.Moc must point to a .moc3 file")

    textures = refs.get("Textures")
    if not isinstance(textures, list) or not textures:
        errors.append("FileReferences.Textures must contain at least one texture")
    elif any(not isinstance(texture, str) or not texture for texture in textures):
        errors.append("FileReferences.Textures entries must be non-empty strings")

    bundle_dir = model3_path.parent.resolve()
    for relative in referenced_runtime_files(model3):
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"referenced runtime file must stay inside bundle: {relative}")
            continue
        candidate = (bundle_dir / relative_path).resolve()
        try:
            candidate.relative_to(bundle_dir)
        except ValueError:
            errors.append(f"referenced runtime file escapes bundle: {relative}")
            continue
        if not candidate.exists():
            errors.append(f"referenced runtime file missing: {relative}")

    if require_binary_signatures and isinstance(moc, str) and moc.endswith(".moc3"):
        moc_path = _safe_bundle_path(bundle_dir, moc)
        if moc_path is not None and moc_path.exists():
            errors.extend(_validate_moc3_signature(moc_path, moc))

    if require_binary_signatures and isinstance(textures, list):
        for texture in textures:
            if not isinstance(texture, str):
                continue
            texture_path = _safe_bundle_path(bundle_dir, texture)
            if texture_path is not None and texture_path.exists():
                errors.extend(_validate_texture_signature(texture_path, texture))

    return not errors, errors


def validate_real_export_provenance(result: dict[str, Any]) -> list[str]:
    provenance = result.get("adapter_provenance")
    if not isinstance(provenance, dict):
        return ["adapter_provenance is required before claiming a real Cubism export"]

    errors: list[str] = []
    if provenance.get("exporter") != "official_cubism_editor":
        errors.append("adapter_provenance.exporter must be official_cubism_editor")
    if not isinstance(provenance.get("editor_version"), str) or not provenance["editor_version"]:
        errors.append("adapter_provenance.editor_version must be a non-empty string")
    if provenance.get("operator_confirmed_export") is not True:
        errors.append("adapter_provenance.operator_confirmed_export must be true")

    workflow = provenance.get("workflow")
    allowed_workflows = {"operator_assisted_cubism_editor", "external_application_integration"}
    if workflow not in allowed_workflows:
        errors.append("adapter_provenance.workflow must identify an official Cubism Editor workflow")

    source_project = provenance.get("source_project_path")
    if source_project is not None:
        if not isinstance(source_project, str) or Path(source_project).suffix.lower() not in {".cmo3", ".psd"}:
            errors.append("adapter_provenance.source_project_path must point to a .cmo3 project or layered .psd source")
    return errors


def _safe_bundle_path(bundle_dir: Path, relative: str) -> Path | None:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    candidate = (bundle_dir / relative_path).resolve()
    try:
        candidate.relative_to(bundle_dir)
    except ValueError:
        return None
    return candidate


def _validate_moc3_signature(path: Path, label: str) -> list[str]:
    errors: list[str] = []
    size = path.stat().st_size
    with path.open("rb") as handle:
        data = handle.read(8)
    if not data.startswith(MOC3_MAGIC):
        errors.append(f"referenced moc3 file is not a Cubism MOC3 binary: {label}")
    if size < MIN_REASONABLE_MOC3_BYTES:
        errors.append(f"referenced moc3 file is too small to be a real export: {label}")
    return errors


def _validate_texture_signature(path: Path, label: str) -> list[str]:
    suffix = path.suffix.lower()
    signature = TEXTURE_SIGNATURES.get(suffix)
    if signature is None:
        return [f"referenced texture has unsupported image suffix: {label}"]
    with path.open("rb") as handle:
        data = handle.read(12)
    if suffix == ".webp":
        if not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
            return [f"referenced texture is not a valid WebP file: {label}"]
        return []
    if not data.startswith(signature):
        return [f"referenced texture is not a valid {suffix.lstrip('.').upper()} file: {label}"]
    return []
