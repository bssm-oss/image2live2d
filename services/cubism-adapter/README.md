# Cubism Adapter

This adapter surface defines the boundary to official Cubism automation.

If `LIVE2D_CUBISM_EXPORT_COMMAND` is not set, the Python pipeline uses a non-production demo fixture. Demo fixtures are labeled `demo_fixture` and fail real export validation.

## Template Adapter

Start from:

```bash
python3 scripts/live2d_cubism_adapter.py --probe output/probe.json
```

The script is intentionally a probe/template. It does not generate `.moc3`. Replace its `export()` implementation with your licensed Cubism workflow, then set:

```bash
export LIVE2D_CUBISM_EXPORT_COMMAND="python3 scripts/live2d_cubism_adapter.py"
```

Run the hard preflight before claiming real export readiness:

```bash
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input path/to/rigged-project.cmo3
```

Flat `.png`/`.jpg`/`.svg` inputs are rejected by preflight because Cubism exports require a rigged `.cmo3` or layered source that has gone through the official Editor workflow.

## Strict Run

```bash
PYTHONPATH=src python3 -m image2live2d.cli demo-thin-e2e \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/real-attempt \
  --require-real-cubism
```

Strict mode exits non-zero unless a real Cubism bundle passes validation. A bundle-shaped fake with files named `.moc3` is rejected unless it has basic binary signatures and official Cubism Editor provenance.

See `docs/cubism-automation.md` for the full command contract and tutorial.
