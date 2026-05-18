from __future__ import annotations

import json
import sys
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
bundle = Path(request["output_bundle_dir"]) / "invalid_bundle"
bundle.mkdir(parents=True, exist_ok=True)
model3 = bundle / "model.model3.json"
model3.write_text(
    json.dumps(
        {
            "Version": 3,
            "FileReferences": {
                "Moc": "missing.moc3",
                "Textures": ["textures/missing.png"],
            },
        }
    ),
    encoding="utf-8",
)
result_path.write_text(
    json.dumps(
        {
            "version": "1",
            "status": "ok",
            "bundle_dir": str(bundle),
            "model3_path": str(model3),
            "generated_files": [str(model3)],
            "logs": ["invalid bundle generated"],
            "errors": [],
        }
    ),
    encoding="utf-8",
)
