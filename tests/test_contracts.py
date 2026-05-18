from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from image2live2d.contracts import validate_export_request, validate_job_manifest, validate_layer_plan, validate_model3_bundle  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_example_manifest_is_valid(self) -> None:
        manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_job_manifest(manifest), [])

    def test_manifest_rejects_path_traversal_job_id(self) -> None:
        manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
        for bad_id in ("../../escape", "x/y", "", 42):
            with self.subTest(bad_id=bad_id):
                manifest["job_id"] = bad_id
                errors = validate_job_manifest(manifest)
                self.assertTrue(any("manifest.job_id" in error for error in errors))

    def test_manifest_rejects_non_string_image_path_and_output_dir(self) -> None:
        manifest = json.loads((ROOT / "examples/manifests/thin-e2e.json").read_text(encoding="utf-8"))
        manifest["input"]["image_path"] = 123
        manifest["output_dir"] = []
        errors = validate_job_manifest(manifest)
        self.assertTrue(any("manifest.input.image_path" in error for error in errors))
        self.assertTrue(any("manifest.output_dir" in error for error in errors))

    def test_layer_plan_requires_parts(self) -> None:
        errors = validate_layer_plan({"version": "1", "job_id": "x", "source_image": "x.png", "provider_mode": "stub", "parts": []})
        self.assertIn("layer_plan.parts must be a non-empty list", errors)

    def test_export_request_rejects_non_string_expected_outputs(self) -> None:
        errors = validate_export_request(
            {
                "version": "1",
                "job_id": "job",
                "source_image": "input.png",
                "layer_plan_path": "layer.json",
                "intermediate_asset_path": "asset.psd",
                "output_bundle_dir": "output",
                "expected_outputs": [{}],
            }
        )
        self.assertTrue(any("unsupported value" in error for error in errors))

    def test_demo_fixture_cannot_pass_real_bundle_validation(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            model3 = bundle / "fixture.model3.json"
            model3.write_text(
                json.dumps(
                    {
                        "Version": 3,
                        "FileReferences": {"Moc": "fixture-non-production.moc3.txt", "Textures": ["textures/texture_00.txt"]},
                        "Meta": {"NonProductionFixture": True},
                    }
                ),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("demo fixture" in error for error in errors))

    def test_bundle_validation_rejects_parent_traversal_reference(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            bundle.mkdir()
            outside = Path(tmp) / "outside.moc3"
            outside.write_text("outside", encoding="utf-8")
            model3 = bundle / "model.model3.json"
            model3.write_text(
                json.dumps({"Version": 3, "FileReferences": {"Moc": "../outside.moc3", "Textures": ["textures/texture_00.png"]}}),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("inside bundle" in error for error in errors))

    def test_bundle_validation_rejects_absolute_reference(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            bundle.mkdir()
            absolute = Path(tmp) / "absolute.moc3"
            absolute.write_text("absolute", encoding="utf-8")
            model3 = bundle / "model.model3.json"
            model3.write_text(
                json.dumps({"Version": 3, "FileReferences": {"Moc": str(absolute), "Textures": ["textures/texture_00.png"]}}),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("inside bundle" in error for error in errors))

    def test_bundle_validation_requires_existing_moc_and_texture_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            model3 = bundle / "model.model3.json"
            model3.write_text(
                json.dumps({"Version": 3, "FileReferences": {"Moc": "missing.moc3", "Textures": ["textures/missing.png"]}}),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("missing.moc3" in error for error in errors))
            self.assertTrue(any("textures/missing.png" in error for error in errors))

    def test_bundle_validation_checks_physics_pose_and_motion_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "textures").mkdir()
            (bundle / "model.moc3").write_text("fake", encoding="utf-8")
            (bundle / "textures" / "texture_00.png").write_text("fake", encoding="utf-8")
            model3 = bundle / "model.model3.json"
            model3.write_text(
                json.dumps(
                    {
                        "Version": 3,
                        "FileReferences": {
                            "Moc": "model.moc3",
                            "Textures": ["textures/texture_00.png"],
                            "Physics": "missing.physics3.json",
                            "Pose": "missing.pose3.json",
                            "Motions": {"Idle": [{"File": "motions/missing.motion3.json"}]},
                        },
                    }
                ),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("missing.physics3.json" in error for error in errors))
            self.assertTrue(any("missing.pose3.json" in error for error in errors))
            self.assertTrue(any("motions/missing.motion3.json" in error for error in errors))

    def test_bundle_validation_rejects_non_string_texture_entries(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "model.moc3").write_bytes(b"MOC3\x03\x00\x00\x00" + b"\x00" * 128)
            model3 = bundle / "model.model3.json"
            model3.write_text(
                json.dumps({"Version": 3, "FileReferences": {"Moc": "model.moc3", "Textures": [123, ""]}}),
                encoding="utf-8",
            )
            passed, errors = validate_model3_bundle(model3)
            self.assertFalse(passed)
            self.assertTrue(any("Textures entries" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
