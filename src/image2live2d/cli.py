from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .contracts import validate_model3_bundle
from .cubism import preflight_real_export, probe_export_command
from .model_service import serve
from .orchestrator import run_thin_e2e
from .runtime import run_runtime_smoke
from .static_quad import generate_static_quad_live2d
from .storage import write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="image2live2d")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo-thin-e2e", help="Run the thin end-to-end demo")
    demo.add_argument("--input-image", required=True, type=Path)
    demo.add_argument("--output-dir", required=True, type=Path)
    demo.add_argument(
        "--require-real-cubism",
        action="store_true",
        help="Exit non-zero unless the run validates a real Cubism export bundle",
    )
    demo.add_argument("--adapter-timeout", default=None, type=int, help="Cubism adapter timeout in seconds")

    service = subparsers.add_parser(
        "serve-model",
        help="Run the local unauthenticated model service; bind only to trusted interfaces",
    )
    service.add_argument("--host", default="127.0.0.1")
    service.add_argument("--port", default=8765, type=int)
    service.add_argument("--output-dir", required=True, type=Path)

    probe = subparsers.add_parser("probe-cubism", help="Probe LIVE2D_CUBISM_EXPORT_COMMAND readiness")
    probe.add_argument("--command", dest="adapter_command", default=None, help="Override LIVE2D_CUBISM_EXPORT_COMMAND")
    probe.add_argument("--output", default=None, type=Path, help="Optional path to write probe JSON")

    preflight = subparsers.add_parser("preflight-real-export", help="Explain whether this machine can produce a real .moc3 now")
    preflight.add_argument("--input", dest="input_path", default=None, type=Path, help="Optional source image, PSD, or .cmo3 to evaluate")
    preflight.add_argument("--command", dest="adapter_command", default=None, help="Override LIVE2D_CUBISM_EXPORT_COMMAND")
    preflight.add_argument("--output", default=None, type=Path, help="Optional path to write preflight JSON")

    validate = subparsers.add_parser("validate-bundle", help="Validate a generated Live2D model3 bundle")
    validate.add_argument("--model3", required=True, type=Path)
    validate.add_argument("--allow-fixture", action="store_true", help="Allow demo fixtures during validation")
    validate.add_argument("--shape-only", action="store_true", help="Only validate model3 references; do not require binary signatures")

    runtime = subparsers.add_parser("runtime-smoke-bundle", help="Load a model3 bundle through a Live2D runtime smoke command")
    runtime.add_argument("--model3", required=True, type=Path)
    runtime.add_argument("--core-js", default=None, type=Path, help="Path to official live2dcubismcore.min.js for built-in Node smoke")
    runtime.add_argument("--command", dest="runtime_command", default=None, help="Override runtime smoke command")
    runtime.add_argument("--output", required=True, type=Path, help="Path to write runtime smoke JSON")
    runtime.add_argument("--timeout", default=30, type=int)

    static_quad = subparsers.add_parser(
        "generate-static-quad-live2d",
        help="Generate an experimental static one-quad Live2D bundle from a PNG and optionally runtime-smoke it",
    )
    static_quad.add_argument("--input-image", required=True, type=Path)
    static_quad.add_argument("--output-dir", required=True, type=Path)
    static_quad.add_argument("--model-name", default="static_quad")
    static_quad.add_argument("--core-js", default=None, type=Path, help="Path to official live2dcubismcore.min.js for runtime proof")
    static_quad.add_argument("--timeout", default=30, type=int)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo-thin-e2e":
        if not args.input_image.exists():
            print(f"error: input image not found: {args.input_image}", file=sys.stderr)
            return 2
        try:
            report = run_thin_e2e(
                args.input_image,
                args.output_dir,
                require_real_cubism=args.require_real_cubism,
                export_timeout_seconds=args.adapter_timeout,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"report: {report['report_path']}")
        print(f"capability: {report['capability_classification']}")
        if report["capability_classification"] == "demo_fixture":
            print("warning: demo fixture only; no real Cubism export was produced")
        return 0 if report["status"] == "completed" else 2
    if args.command == "serve-model":
        serve(args.host, args.port, args.output_dir)
        return 0
    if args.command == "probe-cubism":
        result = probe_export_command(args.adapter_command)
        if args.output:
            write_json(args.output, result)
        print(f"status: {result['status']}")
        print(f"available: {result['available']}")
        print(f"supports_probe: {result['supports_probe']}")
        return 0 if result["available"] else 2
    if args.command == "preflight-real-export":
        result = preflight_real_export(args.input_path, args.adapter_command)
        if args.output:
            write_json(args.output, result)
        print(f"status: {result['status']}")
        print(f"ready: {result['ready']}")
        for blocker in result["blockers"]:
            print(f"blocker: {blocker['code']} - {blocker['message']}")
        for action in result["next_actions"]:
            print(f"next: {action}")
        return 0 if result["ready"] else 2
    if args.command == "validate-bundle":
        passed, errors = validate_model3_bundle(
            args.model3,
            forbid_fixture=not args.allow_fixture,
            require_binary_signatures=not args.shape_only,
        )
        print(f"valid: {str(passed).lower()}")
        for error in errors:
            print(f"error: {error}")
        return 0 if passed else 2
    if args.command == "runtime-smoke-bundle":
        result = run_runtime_smoke(
            args.model3,
            args.output,
            core_js_path=args.core_js,
            command=args.runtime_command,
            timeout_seconds=args.timeout,
        )
        print(f"status: {result['status']}")
        print(f"runtime_load_status: {result['runtime_load_status']}")
        for error in result.get("errors", []):
            if isinstance(error, dict):
                print(f"error: {error.get('code')} - {'; '.join(str(message) for message in error.get('messages', []))}")
            else:
                print(f"error: {error}")
        return 0 if result["status"] == "loaded" else 2
    if args.command == "generate-static-quad-live2d":
        result = generate_static_quad_live2d(
            args.input_image,
            args.output_dir,
            model_name=args.model_name,
            core_js_path=args.core_js,
            timeout_seconds=args.timeout,
        )
        print(f"status: {result['status']}")
        print(f"capability: {result['capability_classification']}")
        if result.get("model3_path"):
            print(f"model3: {result['model3_path']}")
        print("warning: experimental static quad only; not an inferred rigged Live2D character")
        for error in result.get("errors", []):
            print(f"error: {error.get('code')} - {'; '.join(str(message) for message in error.get('messages', []))}")
        return 0 if result["status"] == "completed" else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
