# Tutorial: Local Model Service Mode

The service is unauthenticated and intended for local R&D. Keep it bound to `127.0.0.1` unless you add your own access controls.

## Start Service

```bash
PYTHONPATH=src python3 -m image2live2d.cli serve-model \
  --host 127.0.0.1 \
  --port 8765 \
  --output-dir output/service
```

## Verify Health

```bash
curl http://127.0.0.1:8765/health
```

Expected:

```json
{"status":"ok","provider_modes":["stub"]}
```

## Create and Analyze a Job

```bash
curl -X POST http://127.0.0.1:8765/jobs \
  -H 'Content-Type: application/json' \
  --data-binary @examples/manifests/thin-e2e.json

curl -X POST http://127.0.0.1:8765/jobs/thin-e2e-example/analyze

curl http://127.0.0.1:8765/jobs/thin-e2e-example/artifacts
```

The built-in provider is `stub`; it creates predictable artifacts for testing only.
