from __future__ import annotations

import json
import sys
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
bundle = Path(request["output_bundle_dir"])
(bundle / "textures").mkdir(parents=True, exist_ok=True)
(bundle / "model.moc3").write_text("fake binary for contract validation only", encoding="utf-8")
(bundle / "textures" / "texture_00.png").write_text("fake texture", encoding="utf-8")
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
            "bundle_dir": None,
            "model3_path": "model.model3.json",
            "generated_files": ["model.model3.json", "model.moc3", "textures/texture_00.png"],
            "logs": ["null bundle dir result generated"],
            "errors": [],
        }
    ),
    encoding="utf-8",
)
