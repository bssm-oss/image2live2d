---
name: image2live2d
description: Orchestrate image-to-Live2D R&D jobs through manifest creation, model-service analysis, Cubism adapter validation, and final reporting.
---

# image2live2d Skill

Use this skill to run the image-to-Live2D thin end-to-end workflow.

## Hard Rules

- Never claim demo fixtures are real Cubism exports.
- Always include capability classification in the final answer.
- Treat `demo_fixture` as wiring success only.
- Treat `contract_bundle_shape_validated` as non-real contract evidence; never claim it is actual image-to-Live2D output.
- Treat `real_cubism_export_attempted` with failed validation as a blocker for real-export claims.
- Use the model service for image/layer artifacts; do not ask the language model to invent masks.
- If the user requests real Cubism output, run `preflight-real-export` and `probe-cubism` first.
- Stop on failed strict real export; do not silently downgrade to demo success.

## Workflow

1. Create or read a job manifest.
2. Call the model service or local stub provider.
3. Inspect layer plan confidence and manual-correction notes.
4. Create a Cubism export request.
5. If real export is required, verify source/editor/adapter readiness with `preflight-real-export`, then verify `LIVE2D_CUBISM_EXPORT_COMMAND` with `probe-cubism`.
6. Invoke the Cubism adapter.
7. Validate capability classification.
8. If classification is `demo_fixture`, say clearly that no real `.moc3` was produced.
9. If classification is `real_cubism_export_attempted`, report validation errors and stop.
10. If classification is `contract_bundle_shape_validated`, say the bundle shape is not proof of a real `.moc3` export.
11. Write a final report using `templates/final-report.md`.

## Local Command

```bash
PYTHONPATH=src python skills/image2live2d/scripts/run_skill_job.py \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/skill-demo
```

## Real Export Checklist

- [ ] Cubism Editor is installed and licensed.
- [ ] The operator has a rigged `.cmo3` project ready; this scaffold does not create production rigging from a single image yet.
- [ ] `LIVE2D_CUBISM_EXPORT_COMMAND` points to an adapter command.
- [ ] `probe-cubism` reports the command is available.
- [ ] `preflight-real-export` reports no blockers for the source/editor/adapter.
- [ ] Adapter result includes official Cubism provenance.
- [ ] Strict mode is used: `--require-real-cubism`.
- [ ] `runtime-smoke-bundle` reports `status: loaded` through Live2D Cubism Core before claiming runtime load success.
- [ ] `final_report.json` reports `real_runtime_loaded` from independent runtime smoke before claiming runtime success; still do not claim image generation unless export provenance ties the bundle to the source job.
