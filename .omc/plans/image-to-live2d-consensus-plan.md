# Consensus Plan: Image-to-Live2D R&D Moonshot

## Source Spec
- `.omc/specs/deep-interview-image-to-live2d-rd-moonshot.md`
- Planning mode: `--consensus --direct`
- Status: APPROVED by Oracle architecture/critic review

## Requirements Summary
Build the first thin end-to-end milestone for an image-to-Live2D R&D moonshot. The system must include both an agent skill and a model/service surface. The first milestone should take one curated anime character image through a complete pipeline: skill orchestration, service-side image analysis/layer planning, Cubism export adapter integration, hard real-export preflight, and web preview classification. In environments without a real Cubism Editor/export adapter, strict mode must fail honestly rather than claiming a generated runtime bundle.

This is not a production guarantee for arbitrary images. It is the first measurable slice toward the long-term target of arbitrary image -> automatic AI correction -> official Cubism export -> commercial-quality full rigging.

## RALPLAN-DR Summary

### Principles
- Preserve honesty about feasibility: arbitrary-image commercial-grade full rigging is a research goal, not a v1 guarantee.
- Separate orchestration from computation: skills coordinate workflows; services own image/model processing and artifact lifecycle.
- Use official Cubism export as the primary `.moc3` path; do not build the plan around reverse-engineering proprietary binary output.
- Make every pipeline step observable through manifests, artifacts, confidence values, logs, and reports.
- Keep the first milestone thin but real: one curated end-to-end demo is better than many disconnected stubs.
- Never let demo fixtures satisfy real Cubism/export claims.

### Decision Drivers
- The repo is empty, so architecture must establish conventions from scratch.
- Image decomposition/model inference tooling is Python-centered, while Live2D web preview is browser/TypeScript-centered.
- Cubism Editor automation may be unavailable in CI/local dev, so the adapter contract must support deterministic validation without pretending to export real `.moc3` when the official tool is absent.
- The plan must distinguish orchestration validation from real Cubism export validation.

### Viable Options
| Option | Pros | Cons |
|--------|------|------|
| Python-first service + skill + TypeScript preview | Best fit for image ML, clear API boundary, browser preview remains native to web tooling | Multi-language repo, more setup scripts |
| TypeScript full-stack with Python worker subprocesses | Unified app/developer UX, easier web/API integration | ML dependency management becomes awkward; subprocess boundary can hide model failures |
| Research notebook first | Fastest model experimentation | Fails the “both skill and service” requirement and does not prove end-to-end automation |

### Favored Option
Use a hybrid architecture: Python model service and pipeline contracts, Markdown/script-based agent skill, TypeScript web preview, and an explicit Cubism automation adapter contract.

Rejected alternatives:
- TypeScript-only is rejected because segmentation/inpainting/model experimentation is materially easier in Python.
- Notebook-first is rejected because it would not produce a reusable service or skill surface.
- Unofficial `.moc3` exporter-first is rejected because the spec resolved to official Cubism automation.

## Architecture Decision Record

### Decision
Create a greenfield monorepo with four first-class surfaces:

1. `skills/image2live2d/` - agent skill instructions, templates, checklists, and scripts.
2. `services/model-service/` - Python API for image jobs, layer planning, critique, artifacts, and provider adapters.
3. `services/cubism-adapter/` - command/API contract for official Cubism export automation, plus a validation-only demo adapter for environments without Cubism.
4. `apps/web-preview/` - browser preview that loads a generated `.model3.json` bundle when one is available.

Every pipeline run must write a final report with a capability classification:

- `demo_fixture` - local wiring/demo path only; never counts as real Cubism export.
- `contract_bundle_shape_validated` - runtime-bundle-shaped files and adapter provenance passed local contract checks, but independent real Cubism/runtime verification is unavailable; not a real export claim.
- `real_cubism_export_attempted` - official automation hook was invoked but validation did not fully pass.
- `real_cubism_export_validated` - reserved for a future independent verifier that proves the official Cubism/runtime path beyond adapter self-attestation.
- `real_runtime_loaded` - validated bundle was loaded by the web runtime smoke path without fatal errors.

### Drivers
- The user explicitly wants both skill form and model/service form.
- Official Cubism export is required for the real `.moc3` path.
- The first milestone must be end-to-end, but the environment may not have Cubism installed.

### Alternatives Considered
- Single CLI only: simpler, but does not satisfy service/skill split.
- Fully hosted SaaS first: too much product/platform scope before the R&D pipeline is proven.
- Direct `.moc3` writer: conflicts with official Cubism automation constraint and has legal/compatibility risk.

### Why Chosen
This split lets each component do what it is good at: the skill handles workflow judgment, the service handles image computation, the adapter isolates Cubism-specific automation risk, and the preview validates runtime behavior through the user-facing surface.

### Consequences
- The first implementation must maintain schemas shared across components.
- CI can fully validate schemas, API behavior, skill dry-run, and demo adapter behavior.
- Real Cubism export remains an optional integration test gated by environment variables and a licensed local installation.

### Follow-ups
- Select exact segmentation/inpainting providers after the scaffolding is in place.
- Build a curated sample dataset and benchmark harness before expanding beyond the first anime image.
- Add real Cubism GUI/CLI automation only after the adapter contract is validated.

## Implementation Steps

### Phase 1: Repository Foundation
- Add root `README.md` explaining the R&D moonshot, thin end-to-end milestone, and feasibility boundaries.
- Add root `docs/architecture.md`, `docs/roadmap.md`, and `docs/cubism-automation.md`.
- Add root `Makefile` or task runner with `install`, `test`, `lint`, `dev-service`, `dev-preview`, and `demo-thin-e2e` targets.
- Add `.gitignore` for Python, Node, generated artifacts, model caches, and Cubism output bundles.

### Phase 2: Shared Job Contract
- Define a versioned job manifest schema containing input image path, output directory, requested parts, provider settings, Cubism adapter settings, quality thresholds, and report paths.
- Define artifact schemas for layer plans, masks, critique results, export requests, export results, preview metadata, and failure reports.
- Define the minimum Cubism handoff contract:
  - source image metadata;
  - generated layered/intermediate asset path;
  - part names and hierarchy/grouping;
  - draw order;
  - mask/alpha expectations;
  - confidence values;
  - known manual-correction notes;
  - export request JSON;
  - expected runtime output files;
  - validation rules.
- Define the capability classification enum used by all reports.
- Add schema examples under `examples/manifests/` and `examples/results/`.
- Add tests that validate example manifests and results against the schemas.

### Phase 3: Model Service
- Create `services/model-service/` as a Python service with typed request/response models.
- Implement endpoints:
  - `POST /jobs` to create an image conversion job.
  - `GET /jobs/{id}` to inspect status.
  - `POST /jobs/{id}/analyze` to generate a layer plan and critique metadata.
  - `GET /jobs/{id}/artifacts` to list produced artifacts.
- Implement a deterministic `stub` provider that works without GPU/model downloads and returns predictable masks/layer plans for the curated sample.
- Add provider interfaces for future `sam2`, `mediapipe`, `ollama-gemma`, and inpainting providers without making them mandatory for the first milestone.
- Store artifacts under a repo-local generated output directory, never mixed with source files.

### Phase 4: Agent Skill
- Create `skills/image2live2d/SKILL.md` with workflow rules for image intake, manifest generation, service calls, quality review, retry planning, Cubism export request, and final report.
- Add skill templates:
  - job manifest template;
  - layer quality checklist;
  - Cubism export checklist;
  - final report template.
- Add scripts that can run a skill dry-run against the model service stub and write the final report.
- Add tests or smoke checks that validate the skill templates and dry-run script.

### Phase 5: Cubism Automation Adapter Contract
- Create `services/cubism-adapter/` with an explicit command contract:
  - input: export request JSON with PSD/intermediate paths and output bundle directory;
  - output: export result JSON with status, generated files, logs, and errors.
- Support `LIVE2D_CUBISM_EXPORT_COMMAND` as the real official automation hook.
- Provide a validation-only demo adapter that does not claim to create a real `.moc3`; it should produce a clearly marked fixture bundle for tests and local UI wiring.
- Add a Cubism capability probe before invoking a real export command:
  - command exists and is executable;
  - input paths exist;
  - output directory is writable;
  - command can return version/capability metadata when supported;
  - license/tooling assumptions are written into the report.
- Add real bundle validation:
  - `.model3.json` exists and parses;
  - referenced `.moc3` exists;
  - referenced textures exist;
  - any referenced physics/pose/motion files exist;
  - demo fixture metadata fails real-export validation.
- Make demo fixtures impossible to confuse with production by setting `non_production_fixture: true` and using fixture-specific filenames/metadata.
- Add docs explaining how to connect a real licensed Cubism automation command when available.

### Phase 6: Web Preview
- Create `apps/web-preview/` as a minimal browser app that can load a model bundle path or URL.
- Use a Live2D web runtime-compatible approach for real bundles.
- Provide a clear unavailable state when only demo fixtures exist or `.moc3` is missing.
- Add a preview report panel showing model path, source job, artifact confidence, and known limitations.
- Add smoke coverage for three preview states:
  - demo fixture;
  - missing/invalid bundle;
  - valid real bundle when available.

### Phase 7: Thin End-to-End Demo
- Add one curated sample job under `examples/thin-e2e/`.
- Add sample provenance metadata under `examples/thin-e2e/SAMPLE_PROVENANCE.md` before committing any real image.
- If image licensing is unclear, use a generated/local placeholder and mark it as non-production sample data.
- Implement a command that runs:
  1. skill dry-run or orchestrator script;
  2. model service stub analysis;
  3. Cubism adapter export request;
  4. preview metadata generation;
  5. final report creation.
- If a real `LIVE2D_CUBISM_EXPORT_COMMAND` is configured, run the real export path.
- If no real Cubism command is configured, run only the demo adapter path and explicitly mark the output as non-production.
- The final report must include capability classification, provider mode, Cubism mode, artifact list, validation status, and explicit limitations.

### Phase 8: Verification and Documentation
- Add unit tests for schema validation, service request/response models, provider interfaces, artifact storage, and adapter contract parsing.
- Add integration tests for model-service stub + skill dry-run + demo adapter.
- Add optional integration test instructions for real Cubism automation.
- Add fake-command tests for Cubism adapter failures:
  - missing command;
  - nonzero exit;
  - malformed JSON;
  - missing output files;
  - demo fixture incorrectly submitted to real validation.
- Document expansion milestones: curated anime -> broader anime -> difficult poses/backgrounds -> arbitrary images -> commercial-grade full rig benchmark.

## Acceptance Criteria
- [ ] `README.md` clearly says this is an R&D moonshot and that arbitrary-image commercial full rigging is not guaranteed in the first milestone.
- [ ] The repo contains `skills/image2live2d/`, `services/model-service/`, `services/cubism-adapter/`, and `apps/web-preview/`.
- [ ] A job manifest schema and at least one valid example manifest exist.
- [ ] The model service can run with the deterministic stub provider and produce layer-plan/critique artifacts.
- [ ] The agent skill dry-run can call or simulate the service workflow and write a final report.
- [ ] The Cubism adapter contract supports both a real command hook and a clearly labeled demo adapter.
- [ ] The thin e2e command runs locally without GPU/Cubism using the demo adapter and labels outputs as non-production.
- [ ] When `LIVE2D_CUBISM_EXPORT_COMMAND` is configured, the pipeline can invoke it and validate the returned runtime bundle contract without promoting self-attested fake data to real export success.
- [ ] The web preview handles both real bundle loading and missing/unavailable `.moc3` states without crashing.
- [ ] Tests pass for schemas, service stub, skill dry-run, adapter contract, and demo e2e path.
- [ ] Every pipeline run writes a final report with capability classification, provider mode, Cubism mode, artifact list, validation status, and explicit limitations.
- [ ] Demo mode passes locally without GPU/Cubism but is labeled `demo_fixture` and cannot satisfy real export criteria.
- [ ] Real Cubism mode fails fast if `LIVE2D_CUBISM_EXPORT_COMMAND` is missing, exits nonzero, returns malformed JSON, or omits required runtime files.
- [ ] Real bundle validation checks that `.model3.json` references resolve to existing files, including `.moc3` and textures, and rejects fake text/bad-signature runtime files.
- [ ] Web preview has an automated smoke test for demo fixture, missing/invalid bundle, and valid real bundle when available.
- [ ] Curated sample includes provenance/license metadata and is not committed if licensing is unclear.
- [ ] The layer-plan artifact includes part names, hierarchy/grouping, draw order, confidence values, and known manual-correction notes.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Real Cubism automation is unavailable in the dev environment. | Cannot prove real `.moc3` export locally. | Gate real export behind `LIVE2D_CUBISM_EXPORT_COMMAND`; validate contract with demo adapter and document optional real test. |
| Demo adapter is mistaken for production `.moc3` export. | Misleading product claims. | Mark demo artifacts as `non_production_fixture: true` and fail production validation if real `.moc3` is absent. |
| Scope drifts toward arbitrary images too early. | Project stalls before first proof. | Keep first milestone tied to one curated sample and document expansion roadmap. |
| Small VLM is overused for pixel tasks. | Poor masks/layers. | Treat VLM as critique/planning only; keep provider interfaces open for segmentation/inpainting models. |
| Multi-language repo increases setup burden. | Developer friction. | Provide root task commands and keep first stubs lightweight. |
| Curated sample has unclear rights. | Legal/product risk. | Require provenance metadata and block committing unclear assets. |
| Real export command validates only process exit, not bundle integrity. | False positive runtime claims. | Validate manifest references and runtime load state separately. |

## Verification Steps
- Run schema validation for all examples.
- Run model-service unit tests and service smoke tests.
- Run skill dry-run against the stub service.
- Run Cubism adapter contract tests with the demo adapter.
- Run thin e2e demo without real Cubism and inspect the non-production report.
- Run `demo-thin-e2e` with no Cubism env var and assert the final report says `demo_fixture`, not real export.
- Run with `LIVE2D_CUBISM_EXPORT_COMMAND` set to a failing fake command and assert the pipeline fails clearly.
- Run with a fake command that returns malformed JSON or missing files and assert bundle validation fails.
- Run with a valid fixture bundle and assert the web preview loads or reports unavailable deterministically.
- If Cubism is installed and `LIVE2D_CUBISM_EXPORT_COMMAND` is configured, run the real export integration test and load the bundle in web preview.
- Run the web preview and confirm it renders the correct state for available, unavailable, and invalid bundle inputs.

## Plan Changelog
- Initial draft created from deep-interview spec.
- Oracle review applied: added capability classification, Cubism capability probe, real bundle validation, demo fixture safeguards, sample provenance, fake-command tests, and preview smoke requirements.
- Oracle re-review approved the revised plan for autopilot execution.
