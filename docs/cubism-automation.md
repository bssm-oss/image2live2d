# Cubism Automation Contract

Real `.moc3` generation must go through a user-provided official Cubism workflow. This project does not ship a headless Cubism exporter.

Official constraints to keep in mind:

- Cubism Editor normally exports MOC3 through the Editor GUI: `File -> Export Embedded File -> Export as MOC3 file`.
- Live2D staff have stated that `cmo3 -> moc3` export via command line is not supported.
- Cubism External Application Integration is a WebSocket API for inspection/control and notifications. It can observe export events such as MOC file export notifications, but it is not a supported headless MOC3 export trigger.

## Mode Map

| Mode | Command | Purpose |
|------|---------|---------|
| Demo fixture | `make demo-thin-e2e` | Validate local wiring without real Cubism output. |
| Real preflight | `python3 -m image2live2d.cli preflight-real-export --input path/to/source` | Explain whether this machine/input can produce a real `.moc3` now. |
| Probe | `python3 -m image2live2d.cli probe-cubism` | Check whether an adapter command is configured and discoverable. |
| Real attempt | `demo-thin-e2e --require-real-cubism` | Fail unless the configured adapter produces a validated runtime bundle. |
| Bundle validation | `python3 -m image2live2d.cli validate-bundle --model3 path/to/model.model3.json` | Validate `.model3.json` references, `.moc3` signature, and texture signatures inside the bundle. |
| Runtime smoke | `python3 -m image2live2d.cli runtime-smoke-bundle --model3 path/to/model.model3.json --core-js path/to/live2dcubismcore.min.js --output output/runtime.json` | Ask Live2D Cubism Core to load and consistency-check an existing `.moc3`. |

## Environment Variables

```bash
export LIVE2D_CUBISM_EXPORT_COMMAND="python3 scripts/live2d_cubism_adapter.py"
export LIVE2D_CUBISM_EDITOR_PATH="/Applications/Live2D Cubism 5 Editor.app"
```

`LIVE2D_CUBISM_EXPORT_COMMAND` is invoked as:

```text
$LIVE2D_CUBISM_EXPORT_COMMAND <export_request_json> <export_result_json>
```

Commands may optionally support a probe convention:

```text
$LIVE2D_CUBISM_EXPORT_COMMAND --probe <probe_result_json>
```

## Adapter Lifecycle

1. The image2live2d pipeline writes `export_request.json`.
2. The Cubism adapter command reads that request.
3. The adapter locates the licensed Cubism Editor setup or reports why it is unavailable.
4. If the adapter uses External Application Integration, the user must enable it in Cubism Editor and approve the plugin/client.
5. Because official headless export is not supported, the adapter should guide or wait for the operator/manual Cubism export workflow.
6. The adapter writes `export_result.json` with either failure details or paths to the exported runtime bundle.
7. image2live2d validates `.model3.json`, referenced `.moc3`, textures, and optional physics/pose/motion files.
8. Demo fixtures are rejected from real-export validation.

## Export Request

The request JSON contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Contract version. |
| `job_id` | string | Yes | Safe job ID: letters, digits, `_`, `.`, `-`. |
| `source_image` | string | Yes | Original source image path. |
| `layer_plan_path` | string | Yes | JSON layer plan from the model service. |
| `intermediate_asset_path` | string | Yes | PSD or placeholder/intermediate path. |
| `output_bundle_dir` | string | Yes | Directory where runtime bundle should be written. |
| `expected_outputs` | string[] | Yes | Allowed values: `model3.json`, `moc3`, `textures`, `physics`, `pose`, `motions`. |

Example:

```json
{
  "version": "1",
  "job_id": "thin-e2e-demo",
  "source_image": "examples/thin-e2e/input/curated-anime-placeholder.svg",
  "layer_plan_path": "output/thin-e2e/artifacts/layer_plan.json",
  "intermediate_asset_path": "output/thin-e2e/artifacts/cubism_handoff_placeholder.txt",
  "output_bundle_dir": "output/thin-e2e/cubism",
  "expected_outputs": ["model3.json", "moc3", "textures"]
}
```

## Export Result

The result JSON must contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Contract version. |
| `status` | string | Yes | `ok` or `failed`. |
| `bundle_dir` | string/null | Yes | Runtime bundle directory. |
| `model3_path` | string/null | Yes | Path to `.model3.json`; relative paths resolve against `bundle_dir`. |
| `generated_files` | string[] | Yes | Files written by the adapter. |
| `adapter_provenance` | object | Yes for real validation | Official Cubism provenance. See below. |
| `logs` | string[] | Yes | Short diagnostic logs. Avoid secrets. |
| `errors` | array | Yes | Structured errors on failure. |

For a run to claim `real_cubism_export_validated`, `adapter_provenance` must include:

```json
{
  "exporter": "official_cubism_editor",
  "editor_version": "5.x",
  "workflow": "operator_assisted_cubism_editor",
  "operator_confirmed_export": true,
  "source_project_path": "path/to/rigged-project.cmo3"
}
```

`source_project_path` may also point to a layered `.psd` source if your adapter documents the Cubism rigging workflow that produced the export.

Current scaffold boundary: adapter provenance is recorded and validated, but self-attestation alone is classified only as `contract_bundle_shape_validated`. This prevents fake commands from claiming real image-to-Live2D output. `runtime-smoke-bundle` can promote an existing model to `real_runtime_loaded` only when Live2D Cubism Core accepts the referenced `.moc3`; that still does not prove the project generated the model from the input image.

Failure example:

```json
{
  "version": "1",
  "status": "failed",
  "bundle_dir": "output/thin-e2e/cubism",
  "model3_path": null,
  "generated_files": [],
  "logs": ["Cubism Editor not found"],
  "errors": [
    {
      "code": "cubism_editor_not_found",
      "messages": ["Set LIVE2D_CUBISM_EDITOR_PATH or install Cubism Editor."]
    }
  ]
}
```

## Validation Gate

Real export validation fails unless:

- `.model3.json` exists and parses;
- `FileReferences.Moc` points to an existing `.moc3` file;
- the `.moc3` file starts with the `MOC3` binary signature and is not a tiny text stub;
- every texture referenced by `FileReferences.Textures` exists;
- referenced textures have valid PNG/JPEG/WebP signatures;
- referenced physics, pose, and motion files exist;
- referenced files stay inside the bundle directory;
- the bundle is not marked `NonProductionFixture`;
- the adapter result includes official Cubism Editor provenance.

This is still not proof of commercial rigging quality. It is a hard gate against demo/text fixtures. A later runtime smoke stage is required before claiming `real_runtime_loaded`.

## Tutorial: Connect a Real Adapter

1. Install and activate Live2D Cubism Editor.
2. Open a rigged `.cmo3` project in Cubism Editor.
3. Enable `File -> External Application Integration Settings` if your adapter uses WebSocket integration.
4. Copy `scripts/live2d_cubism_adapter.py` and replace its `export()` body with your licensed workflow.
5. Make the adapter write the result JSON described above.
6. Probe it:

```bash
PYTHONPATH=src python3 -m image2live2d.cli probe-cubism \
  --command "python3 scripts/live2d_cubism_adapter.py"
```

7. Run the pipeline in strict mode:

```bash
export LIVE2D_CUBISM_EXPORT_COMMAND="python3 scripts/live2d_cubism_adapter.py"
PYTHONPATH=src python3 -m image2live2d.cli demo-thin-e2e \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/real-attempt \
  --require-real-cubism
```

8. Inspect `output/real-attempt/export_request.json`, `export_result.json`, `final_report.json`, and `preview_metadata.json`.

## Troubleshooting

| Symptom | Meaning | Fix |
|---------|---------|-----|
| `flat_image_not_rigged_source` | The input is a flat image, not a Cubism-ready project/source. | Create a layered PSD and rig it in Cubism, or provide a `.cmo3`. |
| `status: missing_env` | No adapter command configured. | Set `LIVE2D_CUBISM_EXPORT_COMMAND`. |
| `command_available_probe_unsupported` | Command exists but does not implement `--probe`. | This is acceptable; run strict e2e to test export. |
| `cubism_editor_not_found` | Template adapter cannot locate Cubism Editor. | Set `LIVE2D_CUBISM_EDITOR_PATH`. |
| `contract_bundle_shape_validated` | Files look like a runtime bundle, but independent real-export verification is unavailable. | Treat as contract evidence only; do not claim real image-to-Live2D output. |
| `real_cubism_export_attempted` | Adapter ran or was requested but bundle validation failed. | Inspect validation errors in `export_result.json`. |
| `demo_fixture` | Demo path ran. | Use `--require-real-cubism` to fail instead. |
