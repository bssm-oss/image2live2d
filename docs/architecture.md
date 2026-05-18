# Architecture

The system is split into four surfaces.

## Agent Skill

The skill owns workflow judgment: image intake, manifest generation, quality checklist execution, retry planning, Cubism export request creation, and final reporting. It must not pretend to perform GPU inference itself.

## Model Service

The service owns image-adjacent computation and artifact lifecycle. The first provider is deterministic `stub`, which creates predictable layer-plan and critique artifacts for tests and the thin demo. Future providers can add SAM2, MediaPipe, Ollama/Gemma critique, inpainting, or depth/layer decomposition.

## Cubism Adapter

The adapter isolates official Cubism automation risk. Real export requires `LIVE2D_CUBISM_EXPORT_COMMAND`. Demo mode creates a fixture with `non_production_fixture: true` and cannot pass real export validation.

## Web Preview

The preview distinguishes demo fixtures, invalid bundles, validated real bundles, and runtime-loaded bundles. It surfaces classification and limitations instead of hiding unavailable runtime state.
