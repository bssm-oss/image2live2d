# image2live2d

R&D scaffold for an image-to-Live2D moonshot: arbitrary image input, AI-assisted correction, official Cubism export automation, and runtime preview.

The first milestone is deliberately narrower: one curated anime-style sample runs through a thin end-to-end path with an agent skill, model-service stub, Cubism adapter contract, and web preview metadata. Demo mode proves wiring only. It does not claim to generate a production `.moc3`.

## What This Builds

- `skills/image2live2d/` - Claude/Codex-style workflow package for orchestration, validation, and reports.
- `services/model-service/` - model-service surface and API contract for image analysis/layer planning.
- `services/cubism-adapter/` - official Cubism automation command contract plus demo-fixture safeguards.
- `apps/web-preview/` - browser preview shell that reports demo, invalid, and real runtime states.
- `src/image2live2d/` - shared contracts, stub provider, Cubism adapter, and thin e2e orchestrator.

## Quick Start

```bash
make test
make demo-thin-e2e
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input examples/thin-e2e/input/curated-anime-placeholder.svg
make runtime-smoke-mao
make static-quad-mao-texture
PYTHONPATH=src python3 -m image2live2d.cli probe-cubism
make dev-service
make dev-preview
```

Open `http://127.0.0.1:8766` after `make dev-preview` and paste the generated `output/thin-e2e/preview_metadata.json` contents into the preview page.

## Capability Classifications

Every run reports one capability classification:

- `demo_fixture` - local wiring only; never a real Cubism export.
- `contract_bundle_shape_validated` - `.model3.json` references, binary signatures, and adapter provenance pass local contract checks, but independent real Cubism/runtime verification is unavailable; not a real export claim.
- `real_cubism_export_attempted` - official automation was attempted but validation did not fully pass.
- `real_cubism_export_validated` - reserved for a future independent verifier that proves the official Cubism/runtime path; this scaffold does not emit it from adapter self-attestation alone.
- `real_runtime_loaded` - an existing validated bundle also loaded through Live2D Cubism Core runtime smoke. This proves runtime loadability, not image generation.

## Real Cubism Automation Hook

Set `LIVE2D_CUBISM_EXPORT_COMMAND` to an executable command that accepts two arguments:

```text
<export_request_json> <export_result_json>
```

The command must write the result JSON. See `docs/cubism-automation.md` for the contract. Without this environment variable, the pipeline uses a clearly labeled non-production demo fixture.

Important: official Live2D documentation and forum guidance indicate there is no supported headless `cmo3 -> moc3` command-line export. The included adapter script is a probe/template. A real setup should bridge to a licensed Cubism Editor workflow and then validate the exported runtime bundle.

To check whether this machine can produce a real `.moc3` now:

```bash
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input examples/thin-e2e/input/curated-anime-placeholder.svg
```

On a machine without Cubism Editor, without an adapter, or with only a flat image, this command exits non-zero and lists the blockers. Existing `.moc3` sample files in other projects are runtime references only; they are not proof that this repo converted an input image.

## Runtime Smoke

This repo can verify that an existing real `.model3.json`/`.moc3` bundle loads through Live2D Cubism Core when a Core JS runtime is available:

```bash
PYTHONPATH=src python3 -m image2live2d.cli runtime-smoke-bundle \
  --model3 /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json \
  --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js \
  --output output/runtime-smoke-mao.json
```

Expected local result: `status: loaded`. This is an actual runtime-load check for a pre-existing sample model, not image-to-Live2D generation.

## Experimental Static Quad Generator

The repo now includes one narrow OSS `.moc3` generation path: `generate-static-quad-live2d`. It creates a genuine Live2D runtime bundle from a PNG by mapping the whole image onto one ArtMesh quad, then optionally runs the same Cubism Core runtime smoke gate.

```bash
PYTHONPATH=src python3 -m image2live2d.cli generate-static-quad-live2d \
  --input-image /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.2048/texture_00.png \
  --output-dir output/static-quad-mao-texture \
  --model-name mao_texture_static \
  --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js
```

Expected local result: `capability: real_runtime_loaded`. This proves the generated `.moc3` is accepted by Live2D Cubism Core. It is still **not** automatic Live2D rigging: no semantic part decomposition, deformers, physics, facial parameters, or motions are inferred from the source image.

To require a real export instead of accepting demo mode:

```bash
PYTHONPATH=src python3 -m image2live2d.cli demo-thin-e2e \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/real-attempt \
  --require-real-cubism
```

That command exits non-zero in this environment. It will not accept demo fixtures, text files named `.moc3`, or adapter self-attestation as real image-to-Live2D output.

## Project Boundary

This repository does not promise arbitrary-image commercial-quality Live2D generation today. It creates the first honest, testable pipeline slice and the gates needed to grow toward that research target.

The experimental static-quad command is the current maximum working generation path: it emits a runtime-loadable `.moc3` for a flat PNG, but only as a static textured plane. The remaining research gap is turning an arbitrary character image into layered/rigged Cubism structure.
