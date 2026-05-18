#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output" / "smoke-matrix"
SAMPLES = [
    ROOT / "examples/smoke-inputs/front-bust.svg",
    ROOT / "examples/smoke-inputs/side-profile.svg",
    ROOT / "examples/smoke-inputs/mascot-prop.svg",
]
ALLOWED_SUFFIXES = [".png", ".jpg", ".jpeg", ".webp"]


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    details: dict[str, Any]


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[ScenarioResult] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    for sample in SAMPLES:
        results.append(run_demo_sample(sample, env))
    for sample in make_suffix_samples():
        results.append(run_demo_sample(sample, env))

    results.extend(
        [
            run_unsupported_suffix(env),
            run_strict_demo_rejection(env),
            run_strict_fake_real_rejection(env),
            run_strict_simulated_official_contract_rejection(env),
            run_invalid_fake_real(env),
            run_template_probe(env),
            run_validate_fake_bundle_rejection(env),
            run_validate_shape_only_bundle(env),
            run_preflight_real_export_blockers(env),
            run_static_quad_shape_generation(env),
            run_auto_rig_generation(env),
            run_runtime_smoke_real_sample(env),
            run_service_lifecycle(env),
            run_preview_classifier(),
        ]
    )

    summary = {
        "passed": all(item.passed for item in results),
        "scenario_count": len(results),
        "results": [item.__dict__ for item in results],
    }
    summary_path = OUTPUT_ROOT / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.name}")
        if not item.passed:
            print(json.dumps(item.details, indent=2, ensure_ascii=False))
    print(f"summary: {summary_path}")
    return 0 if summary["passed"] else 2


def make_suffix_samples() -> list[Path]:
    fixture_dir = OUTPUT_ROOT / "generated-inputs"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    samples: list[Path] = []
    for suffix in ALLOWED_SUFFIXES:
        sample = fixture_dir / f"smoke{suffix}"
        sample.write_bytes(b"stub provider ignores image bytes; suffix contract smoke only\n")
        samples.append(sample)
    return samples


def run_demo_sample(sample: Path, env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / f"demo-{sample.stem}"
    completed = run_cli(
        ["demo-thin-e2e", "--input-image", str(sample), "--output-dir", str(out)],
        env=without_adapter(env),
    )
    report = read_json(out / "final_report.json") if (out / "final_report.json").exists() else {}
    passed = completed.returncode == 0 and report.get("capability_classification") == "demo_fixture"
    return ScenarioResult(
        f"demo sample {sample.name}",
        passed,
        {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "report": report},
    )


def run_strict_demo_rejection(env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / "strict-demo-rejection"
    completed = run_cli(
        [
            "demo-thin-e2e",
            "--input-image",
            str(SAMPLES[0]),
            "--output-dir",
            str(out),
            "--require-real-cubism",
        ],
        env=without_adapter(env),
    )
    passed = completed.returncode == 2 and "capability: demo_fixture" in completed.stdout
    return ScenarioResult("strict mode rejects demo fixture", passed, command_details(completed))


def run_unsupported_suffix(env: dict[str, str]) -> ScenarioResult:
    sample = OUTPUT_ROOT / "generated-inputs" / "bad.txt"
    sample.write_text("unsupported", encoding="utf-8")
    out = OUTPUT_ROOT / "unsupported-suffix"
    completed = run_cli(["demo-thin-e2e", "--input-image", str(sample), "--output-dir", str(out)], env=without_adapter(env))
    passed = completed.returncode == 2 and "unsupported suffix" in completed.stderr
    return ScenarioResult("unsupported suffix fails", passed, command_details(completed))


def run_strict_fake_real_rejection(env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / "strict-fake-real"
    scenario_env = env.copy()
    scenario_env["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {ROOT / 'tests/fixtures/fake_commands/valid_bundle.py'}"
    completed = run_cli(
        [
            "demo-thin-e2e",
            "--input-image",
            str(SAMPLES[1]),
            "--output-dir",
            str(out),
            "--require-real-cubism",
        ],
        env=scenario_env,
    )
    report = read_json(out / "final_report.json") if (out / "final_report.json").exists() else {}
    passed = completed.returncode == 2 and report.get("capability_classification") == "real_cubism_export_attempted"
    return ScenarioResult("strict fake real bundle is rejected", passed, {**command_details(completed), "report": report})


def run_strict_simulated_official_contract_rejection(env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / "strict-simulated-official"
    scenario_env = env.copy()
    scenario_env["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {ROOT / 'tests/fixtures/fake_commands/simulated_official_provenance.py'}"
    completed = run_cli(
        [
            "demo-thin-e2e",
            "--input-image",
            str(SAMPLES[1]),
            "--output-dir",
            str(out),
            "--require-real-cubism",
        ],
        env=scenario_env,
    )
    report = read_json(out / "final_report.json") if (out / "final_report.json").exists() else {}
    passed = completed.returncode == 2 and report.get("capability_classification") == "contract_bundle_shape_validated"
    return ScenarioResult("strict simulated official contract is not real success", passed, {**command_details(completed), "report": report})


def run_invalid_fake_real(env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / "invalid-fake-real"
    scenario_env = env.copy()
    scenario_env["LIVE2D_CUBISM_EXPORT_COMMAND"] = f"{sys.executable} {ROOT / 'tests/fixtures/fake_commands/invalid_bundle.py'}"
    completed = run_cli(
        [
            "demo-thin-e2e",
            "--input-image",
            str(SAMPLES[2]),
            "--output-dir",
            str(out),
            "--require-real-cubism",
        ],
        env=scenario_env,
    )
    report = read_json(out / "final_report.json") if (out / "final_report.json").exists() else {}
    passed = completed.returncode == 2 and report.get("capability_classification") == "real_cubism_export_attempted"
    return ScenarioResult("strict invalid fake real fails", passed, {**command_details(completed), "report": report})


def run_template_probe(env: dict[str, str]) -> ScenarioResult:
    out = OUTPUT_ROOT / "template-probe.json"
    completed = run_cli(
        ["probe-cubism", "--command", f"{sys.executable} {ROOT / 'scripts/live2d_cubism_adapter.py'}", "--output", str(out)],
        env=env,
    )
    probe = read_json(out) if out.exists() else {}
    passed = completed.returncode in (0, 2) and probe.get("supports_probe") is True and probe.get("status") in {
        "ready_for_operator_adapter",
        "cubism_editor_not_found",
    }
    return ScenarioResult("template adapter probe is structured", passed, {**command_details(completed), "probe": probe})


def run_validate_fake_bundle_rejection(env: dict[str, str]) -> ScenarioResult:
    model3 = OUTPUT_ROOT / "strict-fake-real/cubism/real_bundle/model.model3.json"
    completed = run_cli(["validate-bundle", "--model3", str(model3)], env=env)
    passed = completed.returncode == 2 and "not a Cubism MOC3 binary" in completed.stdout
    return ScenarioResult("validate-bundle rejects fake text bundle", passed, command_details(completed))


def run_validate_shape_only_bundle(env: dict[str, str]) -> ScenarioResult:
    model3 = OUTPUT_ROOT / "strict-fake-real/cubism/real_bundle/model.model3.json"
    completed = run_cli(["validate-bundle", "--model3", str(model3), "--shape-only"], env=env)
    passed = completed.returncode == 0 and "valid: true" in completed.stdout
    return ScenarioResult("shape-only validation accepts contract references", passed, command_details(completed))


def run_preflight_real_export_blockers(env: dict[str, str]) -> ScenarioResult:
    completed = run_cli(["preflight-real-export", "--input", str(SAMPLES[0])], env=without_adapter(env))
    passed = (
        completed.returncode == 2
        and "blocker: flat_image_not_rigged_source" in completed.stdout
        and "blocker: missing_export_command" in completed.stdout
        and "blocker: cubism_editor_not_found" in completed.stdout
    )
    return ScenarioResult("preflight reports real export blockers", passed, command_details(completed))


def run_runtime_smoke_real_sample(env: dict[str, str]) -> ScenarioResult:
    model3 = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.model3.json")
    core_js = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js")
    if not model3.exists() or not core_js.exists():
        return ScenarioResult("runtime smoke real local sample skipped", True, {"skipped": "local Live2D sample/core assets unavailable"})
    out = OUTPUT_ROOT / "runtime-smoke-mao.json"
    completed = run_cli(["runtime-smoke-bundle", "--model3", str(model3), "--core-js", str(core_js), "--output", str(out)], env=env)
    result = read_json(out) if out.exists() else {}
    passed = completed.returncode == 0 and result.get("status") == "loaded" and result.get("consistency_passed") is True
    return ScenarioResult("runtime smoke loads real local Mao sample", passed, {**command_details(completed), "result": result})


def run_static_quad_shape_generation(env: dict[str, str]) -> ScenarioResult:
    source = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.2048/texture_00.png")
    if not source.exists():
        source = OUTPUT_ROOT / "generated-inputs" / "static-quad.png"
        source.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
            )
        )
    out = OUTPUT_ROOT / "static-quad"
    args = [
        "generate-static-quad-live2d",
        "--input-image",
        str(source),
        "--output-dir",
        str(out),
        "--model-name",
        "smoke_static_quad",
    ]
    core_js = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js")
    uses_real_runtime = core_js.exists() and source.name == "texture_00.png"
    if uses_real_runtime:
        args.extend(["--core-js", str(core_js)])
    completed = run_cli(args, env=env)
    report = read_json(out / "static_quad_report.json") if (out / "static_quad_report.json").exists() else {}
    expected = "real_runtime_loaded" if uses_real_runtime else "contract_bundle_shape_validated"
    passed = completed.returncode == 0 and report.get("capability_classification") == expected
    return ScenarioResult("static quad generated bundle is honest and valid", passed, {**command_details(completed), "report": report})


def run_auto_rig_generation(env: dict[str, str]) -> ScenarioResult:
    source = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Avatars/Mao/Mao.2048/texture_00.png")
    if not source.exists():
        source = OUTPUT_ROOT / "generated-inputs" / "auto-rig.png"
        source.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000a49444154789c63600000020001e221bc330000000049454e44ae426082"
            )
        )
    out = OUTPUT_ROOT / "auto-rig"
    args = [
        "generate-auto-rig-live2d",
        "--input-image",
        str(source),
        "--output-dir",
        str(out),
        "--model-name",
        "smoke_auto_rig",
    ]
    core_js = Path("/Users/Projects/bssm-oss/AIvtuber/Sources/AIvtuber/Resources/Live2DViewer/vendor/live2dcubismcore.min.js")
    uses_real_runtime = core_js.exists() and source.name == "texture_00.png"
    if uses_real_runtime:
        args.extend(["--core-js", str(core_js)])
    completed = run_cli(args, env=env)
    report = read_json(out / "auto_rig_report.json") if (out / "auto_rig_report.json").exists() else {}
    expected = "real_runtime_loaded" if uses_real_runtime else "contract_bundle_shape_validated"
    passed = (
        completed.returncode == 0
        and report.get("capability_classification") == expected
        and "warp-deformers" in report.get("generated_features", [])
        and "expression-parameters" in report.get("generated_features", [])
    )
    label = "auto-rig generated bundle is runtime-loadable" if uses_real_runtime else "auto-rig generated bundle is shape-valid"
    return ScenarioResult(label, passed, {**command_details(completed), "report": report})


def run_service_lifecycle(env: dict[str, str]) -> ScenarioResult:
    port = free_port()
    out = OUTPUT_ROOT / "service"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "image2live2d.cli",
            "serve-model",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--output-dir",
            str(out),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_health(port)
        base = f"http://127.0.0.1:{port}"
        manifest = read_json(ROOT / "examples/manifests/thin-e2e.json")
        created = request_json(base + "/jobs", method="POST", body=manifest)
        analysis = request_json(base + "/jobs/thin-e2e-example/analyze", method="POST")
        artifacts = request_json(base + "/jobs/thin-e2e-example/artifacts")
        passed = created.get("job_id") == "thin-e2e-example" and analysis.get("provider_mode") == "stub" and len(artifacts.get("artifacts", [])) == 3
        return ScenarioResult("model service lifecycle", passed, {"created": created, "analysis": analysis, "artifacts": artifacts})
    except Exception as exc:
        return ScenarioResult("model service lifecycle", False, {"error": str(exc)})
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_preview_classifier() -> ScenarioResult:
    script = """
const { classifyPreviewState } = require('./apps/web-preview/preview.js');
const cases = [
  ['demo_fixture', 'demo'],
  ['contract_bundle_shape_validated', 'invalid'],
  ['real_cubism_export_validated', 'invalid'],
  ['real_cubism_export_attempted', 'invalid'],
  ['real_runtime_loaded', 'loaded'],
];
for (const [classification, expected] of cases) {
  const result = classifyPreviewState({ classification });
  if (result.state !== expected) {
    console.error(`${classification} => ${result.state}, expected ${expected}`);
    process.exit(1);
  }
}
"""
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=False)
    return ScenarioResult("preview classifier matrix", completed.returncode == 0, command_details(completed))


def run_cli(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "image2live2d.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def without_adapter(env: dict[str, str]) -> dict[str, str]:
    clean = env.copy()
    clean.pop("LIVE2D_CUBISM_EXPORT_COMMAND", None)
    return clean


def command_details(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def request_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(port: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            health = request_json(f"http://127.0.0.1:{port}/health")
            if health.get("status") == "ok":
                return
        except Exception:
            time.sleep(0.1)
    raise TimeoutError("service did not become healthy")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    raise SystemExit(main())
