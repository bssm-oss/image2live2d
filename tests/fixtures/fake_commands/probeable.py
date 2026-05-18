from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

if len(sys.argv) == 3 and sys.argv[1] == "--probe":
    Path(sys.argv[2]).write_text(
        json.dumps(
            {
                "version": "1",
                "status": "ready",
                "available": True,
                "adapter": "probeable-test-adapter",
                "capabilities": {"headless_export_implemented": True},
                "created_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    raise SystemExit(0)

raise SystemExit(2)
