from __future__ import annotations

import json
import os
import sys
from pathlib import Path


request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
model3 = Path(os.environ["IMAGE2LIVE2D_REAL_MODEL3_FIXTURE"]).resolve()
result_path.write_text(
    json.dumps(
        {
            "version": "1",
            "job_id": request.get("job_id"),
            "status": "ok",
            "bundle_dir": str(model3.parent),
            "model3_path": str(model3),
            "generated_files": [str(model3)],
            "adapter_provenance": {
                "exporter": "official_cubism_editor",
                "editor_version": "pre-existing-local-sample",
                "workflow": "operator_assisted_cubism_editor",
                "operator_confirmed_export": True,
                "source_project_path": "fixtures/pre-existing-local-sample.cmo3",
            },
            "logs": ["using pre-existing local sample bundle for runtime smoke"],
            "errors": [],
        }
    ),
    encoding="utf-8",
)
