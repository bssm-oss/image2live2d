# image2live2d

`image2live2d`는 이미지에서 Live2D 런타임 모델을 만들기 위한 R&D 프로젝트입니다. 장기 목표는 임의 이미지 입력 -> AI 보정/분해 -> Cubism 호환 리깅/내보내기 -> 런타임 Live2D 모델 생성입니다.

현재 저장소가 실제로 보장하는 범위는 더 좁습니다. 이 프로젝트는 데모 파이프라인, 검증 게이트, Cubism 어댑터 계약, 런타임 smoke test, 그리고 PNG를 단일 ArtMesh 평면으로 변환하는 실험적 `.moc3` 생성기를 제공합니다.

## 현재 가능한 것

- 데모용 thin end-to-end 파이프라인 실행
- 모델 서비스 stub으로 레이어 계획/리포트 생성
- Cubism export adapter 계약 검증
- 가짜 `.moc3`/fixture를 real export로 오인하지 않도록 차단
- 기존 Live2D `.model3.json`/`.moc3` 번들을 Cubism Core로 runtime smoke 검증
- PNG 한 장을 단일 정적 quad ArtMesh로 감싼 **실제 runtime-loadable `.moc3` 번들** 생성
- 웹 preview에서 demo, invalid, attempted, runtime-loaded 상태 분류

## 아직 안 되는 것

- 임의 이미지에서 얼굴/머리/몸/의상 파츠를 자동 분해하는 것
- 디포머, 표정 파라미터, 물리, 모션을 자동 생성하는 것
- 상용 품질의 full-rig Live2D 캐릭터를 무조건 생성하는 것
- Live2D Cubism Editor 없이 공식 Cubism export workflow를 완전히 대체하는 것

즉, 현재의 정직한 상태는 다음과 같습니다.

```text
PNG -> static one-quad Live2D runtime bundle: 가능
임의 이미지 -> full-rig Live2D 캐릭터: 아직 R&D 대상
```

## 구성

- `skills/image2live2d/`: 에이전트용 작업 흐름, 체크리스트, 템플릿
- `services/model-service/`: 이미지 분석/레이어 계획 API 표면과 deterministic stub provider
- `services/cubism-adapter/`: Cubism export command 계약과 demo fixture 방어 로직
- `apps/web-preview/`: 결과 bundle 상태를 분류하는 브라우저 preview
- `src/image2live2d/`: CLI, 계약 검증, 어댑터, runtime smoke, static quad generator
- `scripts/`: Cubism adapter probe, runtime smoke, smoke matrix, static `.moc3` writer
- `tests/`: contract, service, adapter, runtime, CLI, preview, smoke tests

## 빠른 시작

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

`make dev-preview` 실행 후 `http://127.0.0.1:8766`을 열고, 생성된 `output/thin-e2e/preview_metadata.json` 내용을 preview 페이지에 붙여 넣으면 상태 분류를 확인할 수 있습니다.

## 검증 명령

전체 기본 검증:

```bash
make lint
make test
make smoke
```

정적 Live2D 번들 생성 + Cubism Core runtime 검증:

```bash
make static-quad-mao-texture
```

로컬 기준 기대 결과:

```text
status: completed
capability: real_runtime_loaded
warning: experimental static quad only; not an inferred rigged Live2D character
```

## Capability Classification

모든 실행 결과는 capability classification을 포함합니다.

- `demo_fixture`: 로컬 배선 검증용 demo fixture입니다. 실제 Cubism export가 아닙니다.
- `contract_bundle_shape_validated`: `.model3.json`, `.moc3`, texture 참조와 binary signature는 통과했지만 독립적인 Cubism/runtime 검증은 아직 없습니다.
- `real_cubism_export_attempted`: 공식/실제 export hook을 시도했지만 검증을 완전히 통과하지 못했습니다.
- `real_cubism_export_validated`: 향후 독립 검증기가 공식 Cubism/runtime 경로를 증명할 때를 위해 예약된 상태입니다.
- `real_runtime_loaded`: bundle이 Live2D Cubism Core runtime smoke를 통과했습니다. runtime loadability를 증명하지만 full rig 자동 생성을 의미하지는 않습니다.

## Cubism Export Hook

실제 Cubism export adapter를 연결하려면 `LIVE2D_CUBISM_EXPORT_COMMAND`를 설정합니다. 명령은 두 인자를 받아야 합니다.

```text
<export_request_json> <export_result_json>
```

명령은 반드시 result JSON을 써야 합니다. 계약 세부사항은 `docs/cubism-automation.md`에 있습니다. 이 환경 변수가 없으면 파이프라인은 명확히 표시된 non-production demo fixture를 사용합니다.

주의: Live2D 공식 문서/포럼 기준으로 headless `cmo3 -> moc3` command-line export는 지원되지 않습니다. 이 저장소의 `scripts/live2d_cubism_adapter.py`는 실제 exporter가 아니라 probe/template입니다. 실제 운영에서는 라이선스가 있는 Cubism Editor workflow를 연결하고, 생성된 runtime bundle을 별도로 검증해야 합니다.

현재 머신이 진짜 `.moc3` export를 만들 수 있는지 확인하려면:

```bash
PYTHONPATH=src python3 -m image2live2d.cli preflight-real-export \
  --input examples/thin-e2e/input/curated-anime-placeholder.svg
```

Cubism Editor, export adapter, rigged `.cmo3` 또는 layered PSD가 없으면 이 명령은 non-zero로 종료하고 blocker를 출력합니다. 다른 프로젝트에 존재하는 기존 `.moc3` sample은 runtime reference일 뿐, 이 저장소가 입력 이미지를 변환했다는 증거가 아닙니다.

## Runtime Smoke

기존 real Live2D bundle이 Cubism Core에서 로드되는지 확인할 수 있습니다.

```bash
PYTHONPATH=src python3 -m image2live2d.cli runtime-smoke-bundle \
  --model3 /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json \
  --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js \
  --output output/runtime-smoke-mao.json
```

로컬 기대 결과는 `status: loaded`입니다. 이것은 기존 sample model의 runtime-load 검증이며, 이미지 변환 성공 증명이 아닙니다.

## 실험적 Static Quad Generator

`generate-static-quad-live2d`는 현재 이 저장소에서 실제로 `.moc3`를 새로 생성하는 가장 좁은 경로입니다. PNG 전체를 하나의 ArtMesh quad에 매핑하고, 선택적으로 Cubism Core runtime smoke를 실행합니다.

```bash
PYTHONPATH=src python3 -m image2live2d.cli generate-static-quad-live2d \
  --input-image /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.2048/texture_00.png \
  --output-dir output/static-quad-mao-texture \
  --model-name mao_texture_static \
  --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js
```

로컬 기대 결과는 `capability: real_runtime_loaded`입니다. 이 상태는 생성된 `.moc3`가 Live2D Cubism Core에 의해 일관된 runtime model로 받아들여졌다는 뜻입니다.

단, 이 기능은 자동 리깅이 아닙니다. source image에서 의미 있는 파츠, face rig, physics, motion, expression parameter를 추론하지 않습니다.

## Strict Mode

demo fixture를 허용하지 않고 real export만 요구하려면:

```bash
PYTHONPATH=src python3 -m image2live2d.cli demo-thin-e2e \
  --input-image examples/thin-e2e/input/curated-anime-placeholder.svg \
  --output-dir output/real-attempt \
  --require-real-cubism
```

현재 환경에서는 이 명령이 non-zero로 종료됩니다. demo fixture, text file을 `.moc3`로 위장한 파일, adapter self-attestation만으로는 real image-to-Live2D output으로 인정하지 않습니다.

## 프로젝트 경계

이 저장소는 오늘 기준으로 임의 이미지의 상용 품질 Live2D 자동 생성을 약속하지 않습니다. 대신 다음을 제공합니다.

1. 거짓 성공을 막는 검증 게이트
2. Cubism adapter 계약
3. runtime smoke 검증
4. thin end-to-end demo
5. 실제 Cubism Core가 받아들이는 static `.moc3` 생성 proof

남은 핵심 연구 과제는 임의 캐릭터 이미지를 layered/rigged Cubism 구조로 바꾸는 것입니다.
