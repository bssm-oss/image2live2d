from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.cubism import probe_export_command, run_export  # noqa: E402
from image2live2d.storage import write_json  # noqa: E402


class CubismAdapterTests(unittest.TestCase):
    def test_missing_real_command_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            result = self._with_command("definitely-missing-image2live2d-command", request_path, result_path)
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["status"], "failed")

    def test_failing_fake_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/failing.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")

    def test_malformed_result_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/malformed.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")

    def test_text_fake_command_does_not_validate_as_real_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/valid_bundle.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertFalse(result["validation"]["passed"])
            self.assertTrue(any("not a Cubism MOC3 binary" in error for error in result["validation"]["errors"]))

    def test_bundle_shape_without_provenance_is_attempted_not_real_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/bundle_shape_only.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertTrue(result["validation"]["bundle_shape_passed"])
            self.assertFalse(result["validation"]["provenance_passed"])

    def test_simulated_official_provenance_exercises_real_validation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/simulated_official_provenance.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "contract_bundle_shape_validated")
            self.assertFalse(result["validation"]["passed"])
            self.assertTrue(any("independent real Cubism" in error for error in result["validation"]["errors"]))

    def test_missing_status_result_cannot_be_normalized_to_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/missing_status_shape.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["errors"][0]["code"], "adapter_reported_failure")

    def test_model3_path_must_stay_inside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/escaped_model3_path.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["errors"][0]["code"], "model3_path_outside_bundle")

    def test_real_command_missing_result_fails_with_specific_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/no_result.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["errors"][0]["code"], "missing_export_result")
            self.assertIn("simulated command wrote no result", result["logs"][0])

    def test_real_command_validation_failure_downgrades_to_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/invalid_bundle.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["cubism_mode"], "real_command")
            self.assertFalse(result["non_production_fixture"])
            self.assertTrue(any("missing" in error for error in result["validation"]["errors"]))

    def test_nonzero_adapter_preserves_structured_failure_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/structured_failure.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertEqual(result["errors"][0]["code"], "cubism_editor_not_found")
            self.assertTrue(any("Cubism Editor" in error for error in result["validation"]["errors"]))

    def test_relative_model3_with_null_bundle_dir_falls_back_to_request_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/null_bundle_dir.py"
            result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["classification"], "real_cubism_export_attempted")
            self.assertTrue(Path(result["model3_path"]).is_absolute())

    def test_real_command_relative_model3_path_resolves_against_bundle_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path("model.model3.json")
            stale.write_text("not json", encoding="utf-8")
            request_path, result_path = self._request(Path(tmp))
            script = ROOT / "tests/fixtures/fake_commands/valid_relative_bundle.py"
            try:
                result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["classification"], "real_cubism_export_attempted")
                self.assertTrue(Path(result["model3_path"]).is_absolute())
                self.assertTrue(str(result["model3_path"]).startswith(str(Path(tmp).resolve())))
            finally:
                stale.unlink(missing_ok=True)

    def test_real_command_relative_output_dir_does_not_double_prefix_model3_path(self) -> None:
        relative_output = Path("output/unit-relative-model3-resolution")
        shutil.rmtree(ROOT / relative_output, ignore_errors=True)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                request = {
                    "version": "1",
                    "job_id": "test-job",
                    "source_image": "input.svg",
                    "layer_plan_path": "layer_plan.json",
                    "intermediate_asset_path": "intermediate.psd",
                    "output_bundle_dir": str(relative_output / "cubism"),
                    "expected_outputs": ["model3.json", "moc3", "textures"],
                }
                request_path = write_json(Path(tmp) / "export_request.json", request)
                result_path = Path(tmp) / "export_result.json"
                script = ROOT / "tests/fixtures/fake_commands/valid_bundle.py"
                result = self._with_command(f"{sys.executable} {script}", request_path, result_path)
                self.assertEqual(result["status"], "failed")
                self.assertTrue(str(result["model3_path"]).endswith("model.model3.json"))
                self.assertFalse(any("model3.json not found" in error for error in result["validation"]["errors"]))
        finally:
            shutil.rmtree(ROOT / relative_output, ignore_errors=True)

    def test_invalid_export_request_writes_failure_before_demo_fallback(self) -> None:
        old = os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                request_path = write_json(Path(tmp) / "bad_request.json", {"version": "1"})
                result_path = Path(tmp) / "result.json"
                result = run_export(request_path, result_path)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["errors"][0]["code"], "invalid_export_request")
                self.assertNotEqual(result["classification"], "demo_fixture")
                self.assertTrue(result_path.exists())
        finally:
            if old is not None:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_probe_missing_env_reports_unavailable(self) -> None:
        old = os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
        try:
            result = probe_export_command()
            self.assertFalse(result["available"])
            self.assertEqual(result["status"], "missing_env")
        finally:
            if old is not None:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old

    def test_probe_command_with_probe_support_reports_ready(self) -> None:
        script = ROOT / "tests/fixtures/fake_commands/probeable.py"
        result = probe_export_command(f"{sys.executable} {script}")
        self.assertTrue(result["available"])
        self.assertTrue(result["supports_probe"])
        self.assertEqual(result["status"], "ready")

    def test_probe_directory_command_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = probe_export_command(tmp)
            self.assertFalse(result["available"])
            self.assertEqual(result["status"], "non_executable_command")

    def test_export_directory_command_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path, result_path = self._request(Path(tmp))
            result = self._with_command(tmp, request_path, result_path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "non_executable_export_command")

    def _request(self, tmp: Path) -> tuple[Path, Path]:
        request = {
            "version": "1",
            "job_id": "test-job",
            "source_image": "input.svg",
            "layer_plan_path": "layer_plan.json",
            "intermediate_asset_path": "intermediate.psd",
            "output_bundle_dir": str(tmp / "bundle-output"),
            "expected_outputs": ["model3.json", "moc3", "textures"],
        }
        request_path = write_json(tmp / "export_request.json", request)
        return request_path, tmp / "export_result.json"

    def _with_command(self, command: str, request_path: Path, result_path: Path) -> dict[str, object]:
        old = os.environ.get("LIVE2D_CUBISM_EXPORT_COMMAND")
        os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = command
        try:
            return run_export(request_path, result_path)
        finally:
            if old is None:
                os.environ.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
            else:
                os.environ["LIVE2D_CUBISM_EXPORT_COMMAND"] = old


if __name__ == "__main__":
    unittest.main()
