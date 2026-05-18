from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.runtime import run_runtime_smoke  # noqa: E402


REAL_MODEL3 = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json")
CORE_JS = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js")
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
)


class RuntimeSmokeTests(unittest.TestCase):
    def test_runtime_smoke_requires_core_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_runtime_smoke(ROOT / "examples/results/real-cubism-validated-shape.json", Path(tmp) / "runtime.json")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "bundle_validation_failed")

    @unittest.skipUnless(REAL_MODEL3.exists() and CORE_JS.exists(), "local Cubism sample/core assets are unavailable")
    def test_runtime_smoke_loads_real_local_live2d_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_runtime_smoke(REAL_MODEL3, Path(tmp) / "runtime.json", core_js_path=CORE_JS)
            self.assertEqual(result["status"], "loaded")
            self.assertEqual(result["runtime_load_status"], "loaded")
            self.assertTrue(result["consistency_passed"])

    @unittest.skipUnless(REAL_MODEL3.exists(), "local Cubism sample asset is unavailable")
    def test_runtime_smoke_rejects_custom_command_without_consistency_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = ROOT / "tests/fixtures/fake_commands/fake_runtime_loaded.py"
            result = run_runtime_smoke(REAL_MODEL3, Path(tmp) / "runtime.json", command=f"{sys.executable} {script}")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "runtime_consistency_not_proven")

    @unittest.skipUnless(CORE_JS.exists(), "local Cubism Core JS is unavailable")
    def test_runtime_smoke_rejects_moc3_magic_without_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            (bundle / "textures").mkdir(parents=True)
            (bundle / "model.moc3").write_bytes(b"MOC3\x03\x00\x00\x00" + b"\x00" * 128)
            (bundle / "textures" / "texture_00.png").write_bytes(PNG_1X1)
            model3 = bundle / "model.model3.json"
            model3.write_text(json.dumps({"Version": 3, "FileReferences": {"Moc": "model.moc3", "Textures": ["textures/texture_00.png"]}}), encoding="utf-8")
            result = run_runtime_smoke(model3, Path(tmp) / "runtime.json", core_js_path=CORE_JS)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["errors"][0]["code"], "moc_runtime_consistency_failed")


if __name__ == "__main__":
    unittest.main()
