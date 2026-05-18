from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.contracts import validate_model3_bundle  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
