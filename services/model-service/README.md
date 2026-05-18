# Model Service

The model service owns image-adjacent computation and artifact lifecycle.

Run locally:

```bash
PYTHONPATH=src python -m image2live2d.cli serve-model --host 127.0.0.1 --port 8765 --output-dir output/service
```

Endpoints:

- `GET /health`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/analyze`
- `GET /jobs/{job_id}/artifacts`

The only built-in provider is `stub`, which is deterministic and suitable for contract tests only.

## Security Boundary

The service is unauthenticated and intended for local R&D use. Keep the default `127.0.0.1` binding unless you are on a trusted network and have added your own access controls.
