from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import validate_layer_plan
from .storage import ensure_dir, now_iso, write_json, write_text


STUB_PARTS = [
    ("back_hair", "hair", None, 10, 0.72),
    ("torso", "body", None, 20, 0.76),
    ("neck", "body", "torso", 25, 0.70),
    ("head", "head", "neck", 30, 0.78),
    ("face", "face", "head", 40, 0.74),
    ("left_eye", "face", "face", 50, 0.68),
    ("right_eye", "face", "face", 51, 0.68),
    ("mouth", "face", "face", 60, 0.64),
    ("front_hair", "hair", "head", 70, 0.66),
]


def run_stub_analysis(manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    job_id = manifest["job_id"]
    source_image = manifest["input"]["image_path"]
    artifacts_dir = ensure_dir(output_dir / "artifacts")
    masks_dir = ensure_dir(artifacts_dir / "masks")

    parts: list[dict[str, Any]] = []
    for name, group, parent, draw_order, confidence in STUB_PARTS:
        mask_path = masks_dir / f"{name}.mask.json"
        write_json(
            mask_path,
            {
                "version": "1",
                "job_id": job_id,
                "part": name,
                "provider_mode": "stub",
                "shape": "placeholder-polygon",
                "points": [[0, 0], [1, 0], [1, 1], [0, 1]],
            },
        )
        parts.append(
            {
                "name": name,
                "group": group,
                "parent": parent,
                "draw_order": draw_order,
                "mask_path": str(mask_path),
                "confidence": confidence,
                "manual_correction_notes": [
                    "Stub provider does not inspect pixels.",
                    "Replace with segmentation/inpainting provider before claiming visual quality.",
                ],
            }
        )

    layer_plan = {
        "version": "1",
        "job_id": job_id,
        "source_image": source_image,
        "provider_mode": "stub",
        "created_at": now_iso(),
        "parts": parts,
        "known_limitations": [
            "Deterministic scaffold only; no real segmentation.",
            "Draw order and hierarchy are plausible placeholders for pipeline validation.",
        ],
    }
    errors = validate_layer_plan(layer_plan)
    if errors:
        raise ValueError("Invalid stub layer plan: " + "; ".join(errors))

    layer_plan_path = write_json(artifacts_dir / "layer_plan.json", layer_plan)
    critique = {
        "version": "1",
        "job_id": job_id,
        "provider_mode": "stub",
        "created_at": now_iso(),
        "overall_confidence": 0.66,
        "issues": [
            {
                "severity": "info",
                "code": "stub_provider",
                "message": "No pixel-level model was run; this is suitable only for contract tests.",
            }
        ],
    }
    critique_path = write_json(artifacts_dir / "critique.json", critique)
    intermediate_path = write_text(
        artifacts_dir / "cubism_handoff_placeholder.txt",
        "Placeholder for layered PSD or Cubism-ready intermediate. Stub mode only.\n",
    )

    return {
        "layer_plan_path": str(layer_plan_path),
        "critique_path": str(critique_path),
        "intermediate_asset_path": str(intermediate_path),
        "artifact_paths": [str(layer_plan_path), str(critique_path), str(intermediate_path)],
        "provider_mode": "stub",
    }
