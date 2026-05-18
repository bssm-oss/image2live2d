#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { generateMoc3 } from "./stretchy_moc3writer.mjs";

function usage() {
  console.error("usage: auto_rig_live2d.mjs --input-image input.png --output-dir out --model-name model");
}

function parseArgs(argv) {
  const args = { modelName: "auto_rig" };
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--input-image") {
      args.inputImage = value;
      index += 1;
    } else if (key === "--output-dir") {
      args.outputDir = value;
      index += 1;
    } else if (key === "--model-name") {
      args.modelName = value;
      index += 1;
    } else {
      throw new Error(`unknown argument: ${key}`);
    }
  }
  return args;
}

function pngDimensions(filePath) {
  const header = fs.readFileSync(filePath).subarray(0, 24);
  const pngSignature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (header.length < 24 || !header.subarray(0, 8).equals(pngSignature)) {
    throw new Error("auto-rig generation currently requires a PNG input image");
  }
  return { width: header.readUInt32BE(16), height: header.readUInt32BE(20) };
}

function safeModelName(name) {
  const cleaned = String(name || "auto_rig").replace(/[^A-Za-z0-9_.-]/g, "_");
  if (!/^[A-Za-z0-9]/.test(cleaned)) return `model_${cleaned}`;
  return cleaned.slice(0, 128) || "auto_rig";
}

function region(id, name, group, parameterId, drawOrder, x, y, width, height, ampX, ampY = 0) {
  return { id, name, group, parameterId, drawOrder, x, y, width, height, ampX, ampY };
}

function layoutRegions() {
  return [
    region("BackHair", "Back Hair", "Hair", "ParamHairSwing", 10, 0.24, 0.02, 0.52, 0.33, 0.055, 0.015),
    region("Head", "Head", "Head", "ParamAngleX", 60, 0.27, 0.06, 0.46, 0.34, 0.045, 0.01),
    region("Face", "Face", "Face", "ParamSmile", 85, 0.34, 0.15, 0.32, 0.23, 0.018, 0.02),
    region("LeftEye", "Left Eye", "Face", "ParamEyeLOpen", 120, 0.36, 0.20, 0.10, 0.06, 0.004, -0.04),
    region("RightEye", "Right Eye", "Face", "ParamEyeROpen", 120, 0.54, 0.20, 0.10, 0.06, 0.004, -0.04),
    region("LeftBrow", "Left Brow", "Face", "ParamBrowY", 125, 0.35, 0.15, 0.12, 0.05, 0.008, 0.04),
    region("RightBrow", "Right Brow", "Face", "ParamBrowY", 125, 0.53, 0.15, 0.12, 0.05, 0.008, 0.04),
    region("Mouth", "Mouth", "Face", "ParamMouthOpenY", 130, 0.43, 0.30, 0.14, 0.07, 0.006, 0.08),
    region("FrontHair", "Front Hair", "Hair", "ParamHairSwing", 110, 0.22, 0.00, 0.56, 0.24, 0.07, 0.02),
    region("Neck", "Neck", "Body", "ParamBodyAngleX", 45, 0.43, 0.38, 0.14, 0.12, 0.025, 0.005),
    region("Torso", "Torso", "Body", "ParamBodyAngleX", 35, 0.30, 0.45, 0.40, 0.37, 0.035, 0.018),
    region("Clothing", "Clothing", "Clothing", "ParamClothSwing", 70, 0.25, 0.48, 0.50, 0.38, 0.05, 0.025),
    region("LeftArm", "Left Arm", "Body", "ParamBodyAngleX", 50, 0.12, 0.43, 0.25, 0.42, 0.045, 0.012),
    region("RightArm", "Right Arm", "Body", "ParamBodyAngleX", 50, 0.63, 0.43, 0.25, 0.42, 0.045, 0.012),
    region("LeftLeg", "Left Leg", "Body", "ParamClothSwing", 25, 0.32, 0.78, 0.18, 0.22, 0.028, 0.012),
    region("RightLeg", "Right Leg", "Body", "ParamClothSwing", 25, 0.50, 0.78, 0.18, 0.22, 0.028, 0.012),
  ];
}

function pixelRegion(part, width, height) {
  return {
    x: part.x * width,
    y: part.y * height,
    width: part.width * width,
    height: part.height * height,
  };
}

function gridMesh(rect, cols = 2, rows = 2) {
  const vertices = [];
  const uvs = [];
  for (let row = 0; row <= rows; row += 1) {
    for (let col = 0; col <= cols; col += 1) {
      const nx = col / cols;
      const ny = row / rows;
      vertices.push({ x: rect.x + rect.width * nx, y: rect.y + rect.height * ny });
      uvs.push((rect.x + rect.width * nx) / rect.canvasWidth, (rect.y + rect.height * ny) / rect.canvasHeight);
    }
  }
  const triangles = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const a = row * (cols + 1) + col;
      const b = a + 1;
      const c = a + cols + 1;
      const d = c + 1;
      triangles.push([a, b, d], [a, d, c]);
    }
  }
  return { vertices, triangles, uvs };
}

function warpGrid(rect, part, pose, cols = 2, rows = 2) {
  const points = [];
  for (let row = 0; row <= rows; row += 1) {
    for (let col = 0; col <= cols; col += 1) {
      const nx = col / cols;
      const ny = row / rows;
      const falloff = 0.25 + ny * 0.75;
      const centerPull = (nx - 0.5) * 2;
      points.push({
        x: rect.x + rect.width * nx + pose * rect.width * part.ampX * falloff,
        y: rect.y + rect.height * ny + Math.abs(pose) * rect.height * part.ampY * (1 - Math.abs(centerPull) * 0.35),
      });
    }
  }
  return points;
}

function buildProject(width, height) {
  const parts = layoutRegions();
  const nodes = [
    { id: "Root", name: "Root", type: "group", visible: true },
    { id: "HeadGroup", name: "Head", type: "group", parent: "Root", visible: true },
    { id: "HairGroup", name: "Hair", type: "group", parent: "HeadGroup", visible: true },
    { id: "FaceGroup", name: "Face", type: "group", parent: "HeadGroup", visible: true },
    { id: "BodyGroup", name: "Body", type: "group", parent: "Root", visible: true },
    { id: "ClothingGroup", name: "Clothing", type: "group", parent: "BodyGroup", visible: true },
  ];
  const groupIds = new Map([
    ["Head", "HeadGroup"],
    ["Hair", "HairGroup"],
    ["Face", "FaceGroup"],
    ["Body", "BodyGroup"],
    ["Clothing", "ClothingGroup"],
  ]);
  const animations = [{ name: "Idle", duration: 2400, fps: 30, tracks: [] }];
  const regions = new Map();

  for (const part of parts) {
    const rect = { ...pixelRegion(part, width, height), canvasWidth: width, canvasHeight: height };
    const warpId = `${part.id}Warp`;
    nodes.push({
      id: warpId,
      name: `${part.name} Warp`,
      type: "warpDeformer",
      parent: groupIds.get(part.group),
      visible: true,
      col: 2,
      row: 2,
      gridX: rect.x,
      gridY: rect.y,
      gridW: rect.width,
      gridH: rect.height,
      parameterId: part.parameterId,
    });
    nodes.push({
      id: part.id,
      name: part.name,
      type: "part",
      parent: warpId,
      visible: true,
      opacity: 1,
      draw_order: part.drawOrder,
      mesh: gridMesh(rect),
    });
    regions.set(part.id, {
      atlasIndex: 0,
      x: part.x,
      y: part.y,
      width: part.width,
      height: part.height,
      srcX: rect.x,
      srcY: rect.y,
      srcWidth: width,
      srcHeight: height,
      cropW: rect.width,
      cropH: rect.height,
    });
    animations[0].tracks.push({
      nodeId: warpId,
      property: "mesh_verts",
      keyframes: [
        { time: 0, value: warpGrid(rect, part, -1) },
        { time: 1200, value: warpGrid(rect, part, 0) },
        { time: 2400, value: warpGrid(rect, part, 1) },
      ],
    });
  }

  return {
    project: {
      canvas: { width, height },
      parameters: [
        { id: "ParamAngleX", name: "Face Angle X", min: -1, max: 1, default: 0 },
        { id: "ParamBodyAngleX", name: "Body Angle X", min: -1, max: 1, default: 0 },
        { id: "ParamBreath", name: "Breath", min: 0, max: 1, default: 0.5 },
        { id: "ParamMouthOpenY", name: "Mouth Open", min: -1, max: 1, default: 0 },
        { id: "ParamSmile", name: "Smile", min: -1, max: 1, default: 0 },
        { id: "ParamBrowY", name: "Brow Y", min: -1, max: 1, default: 0 },
        { id: "ParamHairSwing", name: "Hair Swing", min: -1, max: 1, default: 0 },
        { id: "ParamClothSwing", name: "Cloth Swing", min: -1, max: 1, default: 0 },
        { id: "ParamEyeLOpen", name: "Left Eye Open", min: 0, max: 1, default: 1 },
        { id: "ParamEyeROpen", name: "Right Eye Open", min: 0, max: 1, default: 1 },
      ],
      animations,
      nodes,
    },
    regions,
    partPlan: parts.map(part => ({
      id: part.id,
      name: part.name,
      group: part.group,
      parameter_id: part.parameterId,
      normalized_bounds: { x: part.x, y: part.y, width: part.width, height: part.height },
    })),
  };
}

function linearSegments(keyframes) {
  const segments = [keyframes[0].time, keyframes[0].value];
  for (let index = 1; index < keyframes.length; index += 1) {
    segments.push(0, keyframes[index].time, keyframes[index].value);
  }
  return segments;
}

function motionCurve(id, values) {
  return { Target: "Parameter", Id: id, Segments: linearSegments(values) };
}

function generateIdleMotion() {
  const curves = [
    motionCurve("ParamAngleX", [{ time: 0, value: -1 }, { time: 1.2, value: 0 }, { time: 2.4, value: 1 }]),
    motionCurve("ParamBodyAngleX", [{ time: 0, value: 1 }, { time: 1.2, value: 0 }, { time: 2.4, value: -1 }]),
    motionCurve("ParamMouthOpenY", [{ time: 0, value: 0 }, { time: 1.2, value: 0.35 }, { time: 2.4, value: 0 }]),
    motionCurve("ParamSmile", [{ time: 0, value: -0.15 }, { time: 1.2, value: 0.75 }, { time: 2.4, value: -0.15 }]),
    motionCurve("ParamBrowY", [{ time: 0, value: 0 }, { time: 1.2, value: 0.4 }, { time: 2.4, value: 0 }]),
    motionCurve("ParamEyeLOpen", [{ time: 0, value: 1 }, { time: 1.2, value: 0.25 }, { time: 2.4, value: 1 }]),
    motionCurve("ParamEyeROpen", [{ time: 0, value: 1 }, { time: 1.2, value: 0.25 }, { time: 2.4, value: 1 }]),
    motionCurve("ParamHairSwing", [{ time: 0, value: -1 }, { time: 1.2, value: 0.2 }, { time: 2.4, value: 1 }]),
    motionCurve("ParamClothSwing", [{ time: 0, value: 1 }, { time: 1.2, value: -0.2 }, { time: 2.4, value: -1 }]),
    motionCurve("ParamBreath", [{ time: 0, value: 0.15 }, { time: 1.2, value: 1 }, { time: 2.4, value: 0.15 }]),
  ];
  return {
    Version: 3,
    Meta: {
      Duration: 2.4,
      Fps: 30,
      Loop: true,
      AreBeziersRestricted: false,
      CurveCount: curves.length,
      TotalSegmentCount: curves.length * 2,
      TotalPointCount: curves.length * 3,
      UserDataCount: 0,
      TotalUserDataSize: 0,
    },
    Curves: curves,
  };
}

function generatePhysics() {
  return {
    Version: 3,
    Meta: {
      PhysicsSettingCount: 2,
      TotalInputCount: 2,
      TotalOutputCount: 2,
      VertexCount: 4,
      Fps: 30,
      EffectiveForces: { Gravity: { X: 0, Y: -1 }, Wind: { X: 0, Y: 0 } },
      PhysicsDictionary: [
        { Id: "PhysicsHair", Name: "Auto Hair Swing" },
        { Id: "PhysicsCloth", Name: "Auto Cloth Swing" },
      ],
    },
    PhysicsSettings: [
      physicsSetting("PhysicsHair", "ParamAngleX", "ParamHairSwing"),
      physicsSetting("PhysicsCloth", "ParamBodyAngleX", "ParamClothSwing"),
    ],
  };
}

function physicsSetting(id, inputId, outputId) {
  return {
    Id: id,
    Input: [{ Source: { Target: "Parameter", Id: inputId }, Weight: 60, Type: "X", Reflect: false }],
    Output: [{ Destination: { Target: "Parameter", Id: outputId }, VertexIndex: 1, Scale: 1, Weight: 100, Type: "Angle", Reflect: false }],
    Vertices: [
      { Position: { X: 0, Y: 0 }, Mobility: 1, Delay: 1, Acceleration: 1, Radius: 0 },
      { Position: { X: 0, Y: 20 }, Mobility: 0.95, Delay: 0.75, Acceleration: 1.1, Radius: 20 },
    ],
    Normalization: {
      Position: { Minimum: -1, Default: 0, Maximum: 1 },
      Angle: { Minimum: -30, Default: 0, Maximum: 30 },
    },
  };
}

function generateCdi3(project) {
  return {
    Version: 3,
    Parameters: project.parameters.map(param => ({ Id: param.id, GroupId: "AutoRig", Name: param.name ?? param.id })),
    ParameterGroups: [{ Id: "AutoRig", GroupId: "", Name: "Auto Rig" }],
    Parts: project.nodes.filter(node => node.type === "group").map(node => ({ Id: node.id, Name: node.name ?? node.id })),
  };
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.inputImage || !args.outputDir) {
    usage();
    return 2;
  }

  const inputPath = path.resolve(args.inputImage);
  const outputDir = path.resolve(args.outputDir);
  const modelName = safeModelName(args.modelName);
  const { width, height } = pngDimensions(inputPath);
  const textureDirName = `${modelName}.textures`;
  const textureReference = `${textureDirName}/texture_00.png`;
  const motionFile = "motions/idle.motion3.json";
  const physicsFile = `${modelName}.physics3.json`;
  const cdi3File = `${modelName}.cdi3.json`;

  fs.mkdirSync(path.join(outputDir, textureDirName), { recursive: true });
  fs.mkdirSync(path.join(outputDir, "motions"), { recursive: true });
  fs.copyFileSync(inputPath, path.join(outputDir, textureReference));

  const { project, regions, partPlan } = buildProject(width, height);
  const moc3 = generateMoc3({ project, regions, atlasSize: 1, numAtlases: 1 });
  fs.writeFileSync(path.join(outputDir, `${modelName}.moc3`), Buffer.from(moc3));
  writeJson(path.join(outputDir, motionFile), generateIdleMotion());
  writeJson(path.join(outputDir, physicsFile), generatePhysics());
  writeJson(path.join(outputDir, cdi3File), generateCdi3(project));
  writeJson(path.join(outputDir, "auto_rig_plan.json"), {
    version: "1",
    source_image: path.basename(inputPath),
    method: "heuristic-layout-autorig",
    parts: partPlan,
    parameters: project.parameters.map(param => param.id),
    generated_features: ["heuristic-region-artmeshes", "warp-deformers", "expression-parameters", "standard-parameters", "idle-motion", "physics-settings"],
  });
  writeJson(path.join(outputDir, `${modelName}.model3.json`), {
    Version: 3,
    FileReferences: {
      Moc: `${modelName}.moc3`,
      Textures: [textureReference],
      Physics: physicsFile,
      DisplayInfo: cdi3File,
      Motions: { Idle: [{ File: motionFile }] },
    },
    Groups: [
      { Target: "Parameter", Name: "LipSync", Ids: ["ParamMouthOpenY"] },
      { Target: "Parameter", Name: "EyeBlink", Ids: ["ParamEyeLOpen", "ParamEyeROpen"] },
    ],
    HitAreas: [
      { Id: "Head", Name: "Head" },
      { Id: "Torso", Name: "Body" },
    ],
    Meta: {
      GeneratedBy: "image2live2d heuristic auto-rig generator",
      HeuristicAutoRig: true,
      SourceImage: path.basename(inputPath),
      Limitations: "Heuristic region layout; not commercial-quality semantic segmentation.",
    },
  });
  console.log(path.join(outputDir, `${modelName}.model3.json`));
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 2;
}
