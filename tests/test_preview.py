from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreviewTests(unittest.TestCase):
    def test_preview_classifier_states(self) -> None:
        script = """
const { classifyPreviewState } = require('./apps/web-preview/preview.js');
const demo = classifyPreviewState({ classification: 'demo_fixture' });
const shape = classifyPreviewState({ classification: 'contract_bundle_shape_validated' });
const valid = classifyPreviewState({ classification: 'real_cubism_export_validated' });
const bad = classifyPreviewState({ classification: 'real_cubism_export_attempted' });
const loaded = classifyPreviewState({ classification: 'real_runtime_loaded' });
const missing = classifyPreviewState(null);
const unknown = classifyPreviewState({ classification: 'wat' });
if (demo.state !== 'demo') process.exit(1);
if (shape.state !== 'invalid') process.exit(2);
if (!shape.message.includes('not a real export')) process.exit(3);
if (valid.state !== 'invalid') process.exit(4);
if (!valid.message.includes('real_runtime_loaded')) process.exit(10);
if (bad.state !== 'invalid') process.exit(5);
if (loaded.state !== 'loaded') process.exit(6);
if (missing.state !== 'missing') process.exit(7);
if (unknown.state !== 'invalid') process.exit(8);
if (!demo.message.includes('not a real Cubism export')) process.exit(9);
"""
        completed = subprocess.run(["node", "-e", script], cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
