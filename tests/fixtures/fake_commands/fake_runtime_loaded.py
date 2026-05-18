from __future__ import annotations

import json
import sys
from pathlib import Path


model3_path = Path(sys.argv[1]).resolve()
result_path = Path(sys.argv[2])
result_path.write_text(
    json.dumps(
        {
            "version": "1",
            "status": "loaded",
            "runtime": "fake-runtime",
            "model3_path": str(model3_path),
            "consistency_passed": False,
            "errors": [],
            "logs": ["fake loaded result"],
        }
    ),
    encoding="utf-8",
)
