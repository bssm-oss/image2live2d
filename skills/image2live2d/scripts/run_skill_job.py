from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from image2live2d.orchestrator import run_thin_e2e  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run image2live2d skill workflow")
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = run_thin_e2e(args.input_image, args.output_dir)
    print(report["report_path"])
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
