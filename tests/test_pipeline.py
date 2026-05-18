from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.orchestrator import run_thin_e2e  # noqa: E402
from image2live2d.storage import read_json  # noqa: E402


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


class PipelineTests(unittest.TestCase):
    def test_thin_e2e_demo_is_classified_as_demo_fixture(self) -> None:
        old = os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_thin_e2e(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg", Path(tmp))
                self.assertEqual(report["capability_classification"], "demo_fixture")
                final_report = read_json(Path(report["report_path"]))
                self.assertEqual(final_report["capability_classification"], "demo_fixture")
                self.assertFalse(final_report["validation_status"]["passed"])
        finally:
            if old is not None:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_thin_e2e_fake_real_command_is_not_accepted(self) -> None:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        script = ROOT / "tests/fixtures/fake_commands/valid_bundle.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_thin_e2e(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg", Path(tmp))
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["capability_classification"], "real_cubism_export_attempted")
                self.assertEqual(report["cubism_mode"], "real_command")
                self.assertFalse(report["validation_status"]["passed"])
                preview = read_json(Path(tmp) / "preview_metadata.json")
                self.assertEqual(preview["classification"], "real_cubism_export_attempted")
                self.assertTrue(preview["model3_path"].endswith("model.model3.json"))
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_thin_e2e_simulated_official_contract_is_not_real_success(self) -> None:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        script = ROOT / "tests/fixtures/fake_commands/simulated_official_provenance.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_thin_e2e(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg", Path(tmp))
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["capability_classification"], "contract_bundle_shape_validated")
                self.assertEqual(report["cubism_mode"], "real_command")
                self.assertFalse(report["validation_status"]["passed"])
                preview = read_json(Path(tmp) / "preview_metadata.json")
                self.assertEqual(preview["classification"], "contract_bundle_shape_validated")
                self.assertTrue(preview["model3_path"].endswith("model.model3.json"))
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    @unittest.skipUnless(
        Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json").exists()
        and Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js").exists(),
        "local Live2D sample/core assets are unavailable",
    )
    def test_thin_e2e_existing_external_sample_is_rejected_for_strict_pipeline(self) -> None:
        old_command = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        old_model3 = os.environ.get("IMAGE2LIVE2D_REAL_MODEL3_FIXTURE")
        old_core = os.environ.get("LIVE2D_CUBISM_CORE_JS")
        script = ROOT / "tests/fixtures/fake_commands/existing_real_sample_bundle.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        os.environ["IMAGE2LIVE2D_REAL_MODEL3_FIXTURE"] = "/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json"
        os.environ["LIVE2D_CUBISM_CORE_JS"] = "/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_thin_e2e(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg", Path(tmp), require_real_cubism=True)
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["capability_classification"], "real_cubism_export_attempted")
                self.assertTrue(any("Official Cubism automation" in item for item in report["explicit_limitations"]))
        finally:
            _restore_env("LIVE2D_CUBISM_EXPORT_COMMAND", old_command)
            _restore_env("IMAGE2LIVE2D_REAL_MODEL3_FIXTURE", old_model3)
            _restore_env("LIVE2D_CUBISM_CORE_JS", old_core)

    def test_thin_e2e_real_command_validation_failure_is_blocking(self) -> None:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        script = ROOT / "tests/fixtures/fake_commands/invalid_bundle.py"
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {script}"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = run_thin_e2e(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg", Path(tmp))
                self.assertEqual(report["status"], "failed")
                self.assertEqual(report["capability_classification"], "real_cubism_export_attempted")
                self.assertTrue(any("Official Cubism automation" in item for item in report["explicit_limitations"]))
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_skill_script_runs_demo(self) -> None:
        old = os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "skills/image2live2d/scripts/run_skill_job.py"),
                        "--input-image",
                        str(ROOT / "examples/thin-e2e/input/curated-anime-placeholder.svg"),
                        "--output-dir",
                        tmp,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=ROOT,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("final_report.json", completed.stdout)
        finally:
            if old is not None:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old


if __name__ == "__main__":
    unittest.main()
