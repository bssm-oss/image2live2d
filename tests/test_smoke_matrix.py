from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SmokeMatrixTests(unittest.TestCase):
    def test_smoke_matrix_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/smoke_matrix.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        summary = json.loads((ROOT / "output/smoke-matrix/summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["passed"])
        self.assertGreaterEqual(summary["scenario_count"], 10)


if __name__ == "__main__":
    unittest.main()
