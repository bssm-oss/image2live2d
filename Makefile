PYTHON ?= python3
PYTHONPATH := src
export PYTHONPATH

.PHONY: install lint test dev-service dev-preview demo-thin-e2e probe-cubism preflight-real-export runtime-smoke-mao static-quad-mao-texture validate-demo-bundle smoke

install:
	$(PYTHON) -m pip install -e .

lint:
	$(PYTHON) -m compileall src tests

test:
	$(PYTHON) -m unittest discover -s tests

dev-service:
	$(PYTHON) -m image2live2d.cli serve-model --host 127.0.0.1 --port 8765 --output-dir output/service

dev-preview:
	$(PYTHON) -m http.server 8766 --directory apps/web-preview

demo-thin-e2e:
	$(PYTHON) -m image2live2d.cli demo-thin-e2e --input-image examples/thin-e2e/input/curated-anime-placeholder.svg --output-dir output/thin-e2e

probe-cubism:
	$(PYTHON) -m image2live2d.cli probe-cubism

preflight-real-export:
	$(PYTHON) -m image2live2d.cli preflight-real-export --input examples/thin-e2e/input/curated-anime-placeholder.svg

runtime-smoke-mao:
	$(PYTHON) -m image2live2d.cli runtime-smoke-bundle --model3 /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js --output output/runtime-smoke-mao.json

static-quad-mao-texture:
	$(PYTHON) -m image2live2d.cli generate-static-quad-live2d --input-image /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.2048/texture_00.png --output-dir output/static-quad-mao-texture --model-name mao_texture_static --core-js /Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js

validate-demo-bundle:
	$(PYTHON) -m image2live2d.cli validate-bundle --model3 output/thin-e2e/cubism/demo_fixture_bundle/fixture.model3.json

smoke:
	$(PYTHON) scripts/smoke_matrix.py
