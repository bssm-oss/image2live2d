# Tutorial: Real Cubism Adapter Bridge

This tutorial explains how to connect a licensed Cubism workflow without pretending the scaffold can perform unsupported headless export.

## Reality Check

Live2D Cubism Editor does not provide a supported command-line `cmo3 -> moc3` export path. External Application Integration can observe/control some Editor state and export notifications, but it does not officially trigger MOC3 export.

The adapter should therefore be treated as a bridge around an official Editor workflow:

1. verify Cubism is installed;
2. guide or wait for the operator/Editor export;
3. collect exported `.model3.json`, `.moc3`, textures, and related files;
4. write `export_result.json`;
5. let image2live2d validate the runtime bundle.

## 1. Probe the Template

Before probing an adapter, run the hard preflight. With only the sample SVG and no Cubism installation, this must fail:

```bash
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input examples/thin-e2e/input/curated-anime-placeholder.svg
```

Expected blockers include `flat_image_not_rigged_source`, `missing_export_command`, and `cubism_editor_not_found` on a machine without Cubism configured.

```bash
PYTHONPATH=src python3 -m image2live2d.cli probe-cubism \
  --command "python3 scripts/live2d_cubism_adapter.py" \
  --output output/cubism-probe.json
```

If Cubism Editor is not found, the probe reports `available: False`. This is expected on machines without Cubism.

## 2. Configure Editor Path

macOS example:

```bash
export LIVE2D_CUBISM_EDITOR_PATH="/Applications/Live2D Cubism 5 Editor.app"
```

Windows users should set the path appropriate for their installation in the shell that invokes the adapter.

## 3. Implement the Adapter

Copy `scripts/live2d_cubism_adapter.py` and replace its `export()` function. Your implementation must:

- read `<export_request_json>`;
- perform or coordinate the official Cubism export workflow;
- write `<export_result_json>`;
- include `adapter_provenance` with `exporter: official_cubism_editor`, `editor_version`, `workflow`, and `operator_confirmed_export: true`;
- return `0` only when it produced a result JSON for validation;
- return non-zero for setup/export failures.

## 4. Run Strict Mode

```bash
export LIVE2D_CUBISM_EXPORT_COMMAND="python3 scripts/live2d_cubism_adapter.py"
PYTHONPATH=src python3 -m image2live2d.cli demo-thin-e2e \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/real-attempt \
  --require-real-cubism
```

Expected while using the unmodified template: non-zero exit and `real_cubism_export_attempted`, not success.

Expected after implementing a real adapter in this scaffold: `contract_bundle_shape_validated` when official Cubism provenance, `.model3.json`, `.moc3` signature, textures, and referenced files validate. This is still not accepted as real success until an independent runtime/export verifier promotes it.

If you have Live2D Cubism Core JS, run runtime smoke next:

```bash
PYTHONPATH=src python3 -m image2live2d.cli runtime-smoke-bundle \
  --model3 path/to/exported.model3.json \
  --core-js path/to/live2dcubismcore.min.js \
  --output output/runtime-smoke.json
```

`status: loaded` proves the existing exported `.moc3` is accepted by Cubism Core. It still does not prove automatic image-to-Live2D generation unless the adapter/export provenance ties it to the current source job.

## 5. Validate an Existing Bundle

```bash
PYTHONPATH=src python3 -m image2live2d.cli validate-bundle \
  --model3 path/to/model.model3.json
```

This validates references plus basic `.moc3`/texture binary signatures. It does not grade rig quality or prove the model was generated from the input image unless the adapter provenance is present in a strict pipeline run.
