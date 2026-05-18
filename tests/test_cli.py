from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
)


class CliTests(unittest.TestCase):
    def test_cli_missing_input_exits_two(self) -> None:
        completed = self._run_cli("demo-thin-e2e", "--input-image", "missing.png", "--output-dir", "output/missing")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("input image not found", completed.stderr)

    def test_cli_require_real_cubism_rejects_demo_fixture(self) -> None:
        old = os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                completed = self._run_cli(
                    "demo-thin-e2e",
                    "--input-image",
                    "examples/thin-e2e/input/curated-anime-placeholder.svg",
                    "--output-dir",
                    tmp,
                    "--require-real-cubism",
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("capability: demo_fixture", completed.stdout)
        finally:
            if old is not None:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_cli_fake_real_command_exits_two(self) -> None:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        script = ROOT / "tests/fixtures/fake_commands/valid_bundle.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                completed = self._run_cli(
                    "demo-thin-e2e",
                    "--input-image",
                    "examples/thin-e2e/input/curated-anime-placeholder.svg",
                    "--output-dir",
                    tmp,
                    "--require-real-cubism",
                )
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn("capability: real_cubism_export_attempted", completed.stdout)
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_cli_simulated_official_contract_still_exits_two(self) -> None:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        script = ROOT / "tests/fixtures/fake_commands/simulated_official_provenance.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                completed = self._run_cli(
                    "demo-thin-e2e",
                    "--input-image",
                    "examples/thin-e2e/input/curated-anime-placeholder.svg",
                    "--output-dir",
                    tmp,
                    "--require-real-cubism",
                )
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertIn("capability: contract_bundle_shape_validated", completed.stdout)
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_cli_probe_missing_command_exits_two(self) -> None:
        completed = self._run_cli("probe-cubism", "--command", "definitely-missing-image2live2d-command")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("available: False", completed.stdout)

    def test_cli_preflight_flat_image_reports_blockers(self) -> None:
        completed = self._run_cli("preflight-real-export", "--input", "examples/thin-e2e/input/curated-anime-placeholder.svg")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("blocker: flat_image_not_rigged_source", completed.stdout)
        self.assertIn("blocker: cubism_editor_not_found", completed.stdout)

    def test_cli_static_quad_generates_shape_valid_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            out = root / "static"
            completed = self._run_cli(
                "generate-static-quad-live2d",
                "--input-image",
                str(image),
                "--output-dir",
                str(out),
                "--model-name",
                "cli_static",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("capability: contract_bundle_shape_validated", completed.stdout)
            self.assertTrue((out / "cli_static.model3.json").exists())

    def test_cli_auto_rig_generates_shape_valid_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            out = root / "autorig"
            completed = self._run_cli(
                "generate-auto-rig-live2d",
                "--input-image",
                str(image),
                "--output-dir",
                str(out),
                "--model-name",
                "cli_autorig",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("capability: contract_bundle_shape_validated", completed.stdout)
            self.assertTrue((out / "cli_autorig.model3.json").exists())
            self.assertTrue((out / "auto_rig_plan.json").exists())

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "image2live2d.cli", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
