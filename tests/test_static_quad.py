from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.contracts import validate_model3_bundle  # noqa: E402
from image2live2d.autorig import generate_auto_rig_live2d  # noqa: E402
from image2live2d.static_quad import generate_static_quad_live2d  # noqa: E402


PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
)


class StaticQuadTests(unittest.TestCase):
    def test_generates_shape_valid_static_quad_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            result = generate_static_quad_live2d(image, root / "bundle", model_name="unit_static")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["capability_classification"], "contract_bundle_shape_validated")
            model3 = Path(result["model3_path"])
            passed, errors = validate_model3_bundle(model3, forbid_fixture=True, require_binary_signatures=True)
            self.assertTrue(passed, errors)

    def test_rejects_non_png_input_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.jpg"
            image.write_bytes(b"not really a jpeg")
            result = generate_static_quad_live2d(image, root / "bundle", model_name="unit_static")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "png_required")

    def test_generates_shape_valid_auto_rig_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            result = generate_auto_rig_live2d(image, root / "bundle", model_name="unit_autorig")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["capability_classification"], "contract_bundle_shape_validated")
            self.assertIn("warp-deformers", result["generated_features"])
            self.assertIn("expression-parameters", result["generated_features"])
            model3 = Path(result["model3_path"])
            passed, errors = validate_model3_bundle(model3, forbid_fixture=True, require_binary_signatures=True)
            self.assertTrue(passed, errors)
            self.assertTrue((model3.parent / "auto_rig_plan.json").exists())
            self.assertTrue((model3.parent / "motions" / "idle.motion3.json").exists())
            self.assertTrue((model3.parent / "unit_autorig.physics3.json").exists())

    def test_auto_rig_rejects_non_png_input_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.webp"
            image.write_bytes(b"not really a webp")
            result = generate_auto_rig_live2d(image, root / "bundle", model_name="unit_autorig")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "png_required")

    def test_auto_rig_rejects_invalid_model_name_before_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            result = generate_auto_rig_live2d(image, root / "bundle", model_name="../bad")

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "invalid_model_name")

    def test_auto_rig_reports_generation_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            with patch("image2live2d.autorig.shutil.which", return_value="node"):
                with patch("image2live2d.autorig.subprocess.run", side_effect=TimeoutExpired(cmd="node", timeout=1)):
                    result = generate_auto_rig_live2d(image, root / "bundle", model_name="unit_autorig", timeout_seconds=1)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "auto_rig_generation_timeout")

    def test_auto_rig_passes_timeout_to_runtime_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            image.write_bytes(PNG_1X1)
            with patch("image2live2d.autorig.run_runtime_smoke") as runtime_smoke:
                runtime_smoke.return_value = {"status": "loaded", "runtime_load_status": "loaded", "errors": []}
                result = generate_auto_rig_live2d(image, root / "bundle", model_name="unit_autorig", core_js_path=root / "core.js", timeout_seconds=7)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["capability_classification"], "real_runtime_loaded")
            self.assertEqual(runtime_smoke.call_args.kwargs["timeout_seconds"], 7)


if __name__ == "__main__":
    unittest.main()
