from __future__ import annotations

import json
import sys
from pathlib import Path


request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
bundle = Path(request["output_bundle_dir"]) / "declared_bundle"
outside = Path(request["output_bundle_dir"]).parent / "outside_bundle"
outside.mkdir(parents=True, exist_ok=True)
model3 = outside / "model.model3.json"
model3.write_text(json.dumps({"Version": 3, "FileReferences": {"Moc": "model.moc3", "Textures": ["textures/texture_00.png"]}}), encoding="utf-8")
result_path.write_text(
    json.dumps({"version": "1", "status": "ok", "bundle_dir": str(bundle), "model3_path": str(model3), "generated_files": [], "logs": [], "errors": []}),
    encoding="utf-8",
)
