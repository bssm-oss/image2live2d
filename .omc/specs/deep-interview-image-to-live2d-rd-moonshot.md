# Deep Interview Spec: Image-to-Live2D R&D Moonshot

## Metadata
- Interview ID: `6D255516-BF39-40F6-871E-B49BDF6E9A6E`
- Rounds: 8
- Final Ambiguity Score: 15.4%
- Type: greenfield
- Generated: 2026-05-17T01:15:00+09:00
- Threshold: 20%
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.96 | 0.40 | 0.384 |
| Constraint Clarity | 0.78 | 0.30 | 0.234 |
| Success Criteria Clarity | 0.76 | 0.30 | 0.228 |
| **Total Clarity** | | | **0.846** |
| **Ambiguity** | | | **0.154** |

## Goal
Build an R&D moonshot system for automatic image-to-Live2D conversion that contains both:

- an agent skill/workflow layer for Claude/Codex-style orchestration, validation, retry planning, and reporting;
- a model/service layer for image analysis, segmentation, layer planning, AI critique, artifact generation, and Cubism automation integration.

The long-term goal is: arbitrary image input -> AI correction pipeline -> official Cubism export automation -> runtime Live2D model with commercial-quality full rigging.

The first milestone is a thin end-to-end slice: one carefully selected anime character image passes through skill + service + Cubism adapter contract + web preview metadata. If a licensed Cubism Editor workflow is unavailable, the milestone must fail honestly instead of pretending to produce a loadable Live2D runtime bundle.

## Constraints
- The repository is currently empty except for Git metadata, so this is greenfield.
- The first implementation must include both the agent skill track and the model/service track.
- The project is classified as an R&D moonshot, not a guaranteed production v1 for arbitrary images.
- Long-term target remains arbitrary images and full rig quality, but early milestones may use curated inputs to establish the pipeline.
- `.moc3` generation should use official Cubism automation, assuming the user has a valid Live2D Cubism Editor installation/license.
- The project must not depend on bypassing Live2D licensing or reverse-engineering proprietary binary export as the primary path.
- The first milestone should prefer explicit manifests, artifacts, confidence scores, and failure reports over silent best-effort behavior.

## Non-Goals
- Guaranteeing commercial-quality full rigging for every possible image in the first milestone.
- Treating a small VLM such as Gemma as a complete replacement for segmentation, inpainting, rigging, and Cubism export.
- Shipping a direct unofficial `.moc3` writer as the main v1 path.
- Hiding failures; failed segmentation, poor rigging, or Cubism automation errors must be surfaced.
- Building only a prompt/skill without a real service surface.
- Building only a model API without the agent workflow layer.

## Acceptance Criteria
- [ ] A Claude/Codex-style skill package can accept an image job, create a job manifest, call the model service, evaluate returned artifacts, and produce a correction/report plan.
- [ ] A model service API can accept a source image and return segmentation/layer-plan artifacts, critique/confidence metadata, and a machine-readable job result.
- [ ] The system can run a thin end-to-end demo on one curated anime character image.
- [ ] The end-to-end demo produces Cubism-ready intermediate assets such as layered PSD or equivalent export inputs.
- [ ] Official Cubism automation is invoked only when a real adapter/editor setup is available; otherwise strict mode reports blockers and exits non-zero.
- [ ] A web preview can classify demo, attempted, contract-only, and independently verified runtime states without overclaiming fake bundles.
- [ ] The demo report includes model/service decisions, confidence scores, failure points, retry attempts, and known quality limitations.
- [ ] The repository documents the long-term R&D roadmap from curated anime sample -> broader anime inputs -> complex poses/backgrounds -> arbitrary images.
- [ ] The repository documents why full arbitrary-image commercial-quality rigging is a research target, not an immediate guarantee.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| A skill alone can convert images to Live2D. | Skills package workflows and scripts, but do not replace image inference, segmentation, or GPU service lifecycle. | Build a skill for orchestration and a service for computation. |
| A small model such as Gemma can do the whole image correction pipeline. | VLMs are useful for critique/analysis, but segmentation, inpainting, layer decomposition, and rigging need specialized models/algorithms. | Use Gemma/Ollama-like VLMs as critique/planning components, not the whole pipeline. |
| `.model3.json` is enough to be Live2D. | `.model3.json` is a manifest; actual runtime data depends on `.moc3`, textures, physics, motions, etc. | First milestone must produce a real runtime bundle through official Cubism automation. |
| Fully automatic `.moc3` can be generated directly. | `.moc3` is proprietary/compiled runtime data; official workflows center on Cubism Editor export. | Primary path uses official Cubism automation with a valid user installation/license. |
| The product should guarantee every image succeeds. | Arbitrary images + commercial-quality full rigging + no user intervention is not a buildable v1. | Reclassify as R&D moonshot and make the first milestone a thin end-to-end curated demo. |

## Technical Context
The workspace at `/Users/Projects/bssm-oss/image2live2d` has no source tree, package metadata, build scripts, tests, UI, API, or existing image/Live2D/AI code. Architecture and tooling can be chosen from scratch.

External findings gathered during the interview:

- Live2D runtime bundles are not just JSON. Official outputs include `.moc3`, `.model3.json`, texture PNGs, and optional physics/motion/user data files.
- `.model3.json` is a manifest referencing model, textures, physics, pose, expressions, motions, and hit areas.
- Cubism authoring normally starts from PSD/layers; ArtMeshes, deformers, parameters, physics, and motion curves remain the hard part.
- See-through-style research can decompose anime images into semantic, inpainted PSD layers, but it explicitly does not solve full Image-to-Live2D rigging.
- Claude/Codex skills are best treated as workflow packages: instructions, scripts, references, validation, and tool calls.
- A local/hosted model service is the right home for segmentation, image critique, artifact storage, caching, batching, and GPU lifecycle.

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Universal Image Input | core domain | source path, media type, character/image class, complexity, confidence | enters AI Correction Pipeline |
| Runtime Live2D Model | core domain | `.model3.json`, `.moc3`, textures, physics, motions, preview URL | produced by Cubism Export Automation |
| AI Correction Pipeline | core domain | segmentation, layer decomposition, inpainting, critique, retry strategy | consumes Universal Image Input and feeds Model Service outputs to Cubism Export Automation |
| Agent Skill | workflow | instructions, manifest template, validation checklist, retry policy, report format | orchestrates Model Service and Cubism Export Automation |
| Model Service | service | image API, segmentation masks, layer plan, confidence scores, artifact storage | performs computation requested by Agent Skill |
| Cubism Export Automation | external integration | Cubism Editor path, automation adapter, export manifest, runtime bundle | generates Runtime Live2D Model through official tooling |
| Full Rig Quality Standard | quality target | full body, face, hair, clothes, physics, motion naturalness | long-term pass criterion for Runtime Live2D Model |
| Failure/Risk Policy | governance | known limitations, retry logs, failure taxonomy, unsupported cases | prevents silent failures and supports R&D iteration |
| R&D Moonshot Roadmap | planning | milestones, datasets, metrics, expansion stages | turns impossible v1 guarantee into staged research program |
| Thin End-to-End Milestone | first deliverable | one curated image, complete pipeline traversal, web preview | validates architecture before broadening scope |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|--------------|-----|---------|--------|-----------------|
| 1 | 5 | 5 | - | - | - |
| 2 | 6 | 1 | 0 | 5 | 83% |
| 3 | 6 | 0 | 1 | 5 | 100% |
| 4 | 7 | 1 | 0 | 6 | 86% |
| 5 | 7 | 0 | 0 | 7 | 100% |
| 6 | 8 | 1 | 0 | 7 | 88% |
| 7 | 9 | 1 | 0 | 8 | 89% |
| 8 | 10 | 1 | 0 | 9 | 90% |

## Interview Transcript
<details>
<summary>Full Q&A (8 rounds)</summary>

### Round 1
**Q:** 단일 이미지를 넣었을 때 최종 산출물이 어떤 수준이면 “이미지→Live2D 변환 툴이 작동한다”고 판단하시겠습니까?

**A:** 런타임 모델.

**Ambiguity:** 61.5% (Goal: 0.55, Constraints: 0.25, Criteria: 0.30)

### Round 2
**Q:** 이 프로젝트에서 `.moc3` 생성은 어떤 방식까지 허용할까요?

**A:** 완전 자동 필수.

**Ambiguity:** 48.0% (Goal: 0.70, Constraints: 0.45, Criteria: 0.35)

### Round 3
**Q:** 완전 자동 요구를 유지할 때, v1에서 반드시 성공으로 인정할 산출물은 어느 쪽입니까?

**A:** 공식 Cubism 자동화.

**Ambiguity:** 35.8% (Goal: 0.78, Constraints: 0.65, Criteria: 0.45)

### Round 4
**Q:** v1 웹 preview에서 무엇이 반드시 움직이면 “자동 변환 성공”으로 pass입니까?

**A:** 풀 리깅 품질.

**Ambiguity:** 28.0% (Goal: 0.90, Constraints: 0.55, Criteria: 0.65)

### Round 5
**Q:** v1에서 허용할 원본 이미지는 어디까지입니까?

**A:** 이미지 전부.

**Ambiguity:** 36.2% (Goal: 0.92, Constraints: 0.35, Criteria: 0.55)

### Round 6
**Q:** 모든 이미지를 받되, 자동 full rigging이 실패하거나 품질 기준 미달일 때 v1은 어떻게 처리해야 성공입니까?

**A:** 무조건 성공.

**Ambiguity:** 45.5% (Goal: 0.95, Constraints: 0.15, Criteria: 0.40)

### Round 7
**Q:** 현재 요구사항을 어떤 성격의 프로젝트로 확정할까요?

**A:** R&D moonshot.

**Ambiguity:** 26.0% (Goal: 0.95, Constraints: 0.65, Criteria: 0.55)

### Round 8
**Q:** 첫 번째 성공 마일스톤은 무엇으로 잡을까요?

**A:** Thin end-to-end.

**Ambiguity:** 15.4% (Goal: 0.96, Constraints: 0.78, Criteria: 0.76)

</details>
