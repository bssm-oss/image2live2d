#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function usage() {
  console.error("usage: live2d_runtime_smoke.js <model3_json> <result_json> --core-js <live2dcubismcore.min.js>");
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function fail(resultPath, code, messages, extra = {}) {
  const result = {
    version: "1",
    status: "failed",
    runtime: "live2d-cubism-core-js",
    errors: [{ code, messages }],
    logs: [],
    created_at: nowIso(),
    ...extra,
  };
  writeJson(resultPath, result);
  return 2;
}

function parseArgs(argv) {
  const args = { model3: argv[2], result: argv[3], coreJs: process.env.LIVE2D_CUBISM_CORE_JS || null };
  for (let index = 4; index < argv.length; index += 1) {
    if (argv[index] === "--core-js") {
      args.coreJs = argv[index + 1];
      index += 1;
    }
  }
  return args;
}

function toArrayBuffer(buffer) {
  return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
}

async function loadCubismCore(coreJsPath) {
  const source = fs.readFileSync(coreJsPath, "utf8");
  const context = {
    console,
    setTimeout,
    clearTimeout,
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
  };
  context.globalThis = context;
  context.window = context;
  context.self = context;
  context.location = { href: `file://${path.resolve(coreJsPath)}` };
  context.navigator = { userAgent: "node" };
  context.document = {
    currentScript: { src: `file://${path.resolve(coreJsPath)}` },
    getElementsByTagName() {
      return [];
    },
    createElement() {
      return {
        setAttribute() {},
        addEventListener() {},
        parentNode: { insertBefore() {} },
      };
    },
    head: { appendChild() {} },
  };
  vm.createContext(context);
  vm.runInContext(source, context, { filename: coreJsPath });
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    if (context.Live2DCubismCore?.Moc?.fromArrayBuffer) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      return context.Live2DCubismCore;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("Live2DCubismCore did not initialize Moc.fromArrayBuffer");
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.model3 || !args.result || !args.coreJs) {
    usage();
    return args.result ? fail(args.result, "missing_arguments", ["model3, result, and --core-js are required"]) : 2;
  }

  const model3Path = path.resolve(args.model3);
  const resultPath = path.resolve(args.result);
  const coreJsPath = path.resolve(args.coreJs);
  if (!fs.existsSync(model3Path)) return fail(resultPath, "model3_not_found", [`model3 not found: ${model3Path}`]);
  if (!fs.existsSync(coreJsPath)) return fail(resultPath, "cubism_core_not_found", [`core js not found: ${coreJsPath}`]);

  let model3;
  try {
    model3 = JSON.parse(fs.readFileSync(model3Path, "utf8"));
  } catch (error) {
    return fail(resultPath, "invalid_model3_json", [String(error)], { model3_path: model3Path });
  }

  const mocReference = model3?.FileReferences?.Moc;
  if (typeof mocReference !== "string" || !mocReference.endsWith(".moc3")) {
    return fail(resultPath, "missing_moc_reference", ["FileReferences.Moc must point to a .moc3 file"], { model3_path: model3Path });
  }

  const mocPath = path.resolve(path.dirname(model3Path), mocReference);
  if (!mocPath.startsWith(path.resolve(path.dirname(model3Path)) + path.sep)) {
    return fail(resultPath, "moc_reference_outside_bundle", ["Moc reference must stay inside model bundle"], { model3_path: model3Path });
  }
  if (!fs.existsSync(mocPath)) return fail(resultPath, "moc_not_found", [`moc not found: ${mocReference}`], { model3_path: model3Path });

  let core;
  try {
    core = await loadCubismCore(coreJsPath);
  } catch (error) {
    return fail(resultPath, "cubism_core_load_failed", [String(error)], { model3_path: model3Path, core_js_path: coreJsPath });
  }

  try {
    const mocBytes = fs.readFileSync(mocPath);
    const mocBuffer = toArrayBuffer(mocBytes);
    const moc = core.Moc.fromArrayBuffer(mocBuffer);
    const consistent = Boolean(moc && typeof moc.hasMocConsistency === "function" && moc.hasMocConsistency(mocBuffer));
    if (!moc || !consistent) {
      return fail(resultPath, "moc_runtime_consistency_failed", ["Cubism Core did not accept this .moc3 as a consistent runtime model"], {
        model3_path: model3Path,
        moc_path: mocPath,
        core_js_path: coreJsPath,
      });
    }
    writeJson(resultPath, {
      version: "1",
      status: "loaded",
      runtime: "live2d-cubism-core-js",
      cubism_core_version: core.Version?.csmGetVersion?.() ?? null,
      model3_path: model3Path,
      moc_path: mocPath,
      core_js_path: coreJsPath,
      consistency_passed: true,
      errors: [],
      logs: ["Cubism Core loaded the referenced MOC3 and reported consistency."],
      created_at: nowIso(),
    });
    return 0;
  } catch (error) {
    return fail(resultPath, "moc_runtime_load_failed", [String(error)], { model3_path: model3Path, moc_path: mocPath, core_js_path: coreJsPath });
  }
}

main().then((code) => process.exit(code));
