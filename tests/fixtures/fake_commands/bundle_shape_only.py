from __future__ import annotations

import json
import sys
from pathlib import Path


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
)

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
bundle = Path(request["output_bundle_dir"]) / "shape_only_bundle"
(bundle / "textures").mkdir(parents=True, exist_ok=True)
(bundle / "model.moc3").write_bytes(b"MOC3\x03\x00\x00\x00" + b"\x00" * 128)
(bundle / "textures" / "texture_00.png").write_bytes(PNG_1X1)
model3 = bundle / "model.model3.json"
model3.write_text(
    json.dumps({"Version": 3, "FileReferences": {"Moc": "model.moc3", "Textures": ["textures/texture_00.png"]}}),
    encoding="utf-8",
)
result_path.write_text(
    json.dumps(
        {
            "version": "1",
            "status": "ok",
            "bundle_dir": str(bundle),
            "model3_path": str(model3),
            "generated_files": [str(model3), str(bundle / "model.moc3"), str(bundle / "textures" / "texture_00.png")],
            "logs": ["bundle shape generated without official provenance"],
            "errors": [],
        }
    ),
    encoding="utf-8",
)
