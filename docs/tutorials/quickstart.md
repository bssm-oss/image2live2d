# Tutorial: Thin End-to-End Quickstart

This tutorial proves the local pipeline wiring. It does not produce a real `.moc3`.

## 1. Run Tests

```bash
make test
```

Expected: all tests pass.

## 2. Run Demo Mode

```bash
make demo-thin-e2e
```

Expected output includes:

```text
capability: demo_fixture
```

That means the pipeline ran, but no real Cubism export happened.

## 3. Inspect Artifacts

```bash
open output/thin-e2e/final_report.json
open output/thin-e2e/preview_metadata.json
```

The report should explicitly say `demo_fixture` and list limitations.

## 4. Run the Web Preview Gate

```bash
make dev-preview
```

Open `http://127.0.0.1:8766`, paste `preview_metadata.json`, and click **Classify Preview State**.

Expected: the page says **Demo fixture** and warns that this is not a real Cubism export.

## 5. Prove Real Export Is Blocked Locally

```bash
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input examples/thin-e2e/input/curated-anime-placeholder.svg
```

Expected on a normal dev machine without Cubism: non-zero exit with blockers for a flat, non-rigged source image, missing export adapter, and missing Cubism Editor.

## 6. Load a Real Existing Live2D Sample

If the sibling `AIvtuber` sample assets are present on this machine:

```bash
make runtime-smoke-mao
```

Expected: `status: loaded`. This proves the runtime smoke can load a real pre-existing `.moc3`; it does not prove this repo generated that model.
