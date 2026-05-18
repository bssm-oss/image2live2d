#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


COMMON_MACOS_EDITOR_PATHS = [
    "/Applications/Live2D Cubism 5 Editor.app",
    "/Applications/Live2D Cubism 4 Editor.app",
]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def detect_editor() -> dict[str, Any]:
    configured = os.environ.get("LIVE2D_CUBISM_EDITOR_PATH")
    candidates = [configured] if configured else []
    if platform.system() == "Darwin":
        candidates.extend(COMMON_MACOS_EDITOR_PATHS)

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return {"found": True, "path": candidate}
    return {"found": False, "path": configured, "searched": [path for path in candidates if path]}


def probe(output_path: Path) -> int:
    editor = detect_editor()
    write_json(
        output_path,
        {
            "version": "1",
            "status": "ready_for_operator_adapter" if editor["found"] else "cubism_editor_not_found",
            "available": editor["found"],
            "adapter": "scripts/live2d_cubism_adapter.py",
            "editor": editor,
            "capabilities": {
                "requires_official_editor": True,
                "headless_export_implemented": False,
                "writes_moc3": False,
                "purpose": "template/probe adapter; replace export implementation with a licensed official Cubism workflow",
            },
            "warnings": [
                "This template does not generate .moc3 by itself.",
                "Use it to verify environment wiring, then implement the official Cubism export step for your licensed setup.",
            ],
            "created_at": now_iso(),
        },
    )
    return 0 if editor["found"] else 2


def export(request_path: Path, result_path: Path) -> int:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    editor = detect_editor()
    status = "failed"
    errors: list[dict[str, Any]] = []

    if not editor["found"]:
        errors.append(
            {
                "code": "cubism_editor_not_found",
                "messages": [
                    "Set LIVE2D_CUBISM_EDITOR_PATH to your Live2D Cubism Editor installation, then replace this template with a real official export implementation.",
                ],
            }
        )
    else:
        errors.append(
            {
                "code": "headless_export_not_implemented",
                "messages": [
                    "Editor installation was detected, but this template intentionally does not automate Cubism export.",
                    "Implement the licensed GUI/API/automation bridge here and write a result JSON that points to the exported .model3.json.",
                ],
            }
        )

    write_json(
        result_path,
        {
            "version": "1",
            "job_id": request.get("job_id"),
            "status": status,
            "bundle_dir": request.get("output_bundle_dir"),
            "model3_path": None,
            "generated_files": [],
            "logs": [
                "live2d_cubism_adapter.py is a template/probe, not a production exporter.",
                f"editor_detected={editor['found']}",
            ],
            "errors": errors,
            "created_at": now_iso(),
        },
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Template adapter for LIVE2D_CUBISM_EXPORT_COMMAND")
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("result", nargs="?", type=Path)
    parser.add_argument("--probe", type=Path, help="Write probe JSON and exit")
    args = parser.parse_args()

    if args.probe:
        return probe(args.probe)
    if not args.request or not args.result:
        parser.error("expected <export_request_json> <export_result_json> or --probe <probe_result_json>")
    return export(args.request, args.result)


if __name__ == "__main__":
    raise SystemExit(main())
