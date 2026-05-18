from __future__ import annotations

import json
import sys
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
result_path.write_text(
    json.dumps(
        {
            "version": "1",
            "job_id": request.get("job_id"),
            "status": "failed",
            "bundle_dir": request.get("output_bundle_dir"),
            "model3_path": None,
            "generated_files": [],
            "logs": ["structured adapter failure"],
            "errors": [
                {
                    "code": "cubism_editor_not_found",
                    "messages": ["Cubism Editor was not found by the adapter."],
                }
            ],
        }
    ),
    encoding="utf-8",
)
raise SystemExit(2)
