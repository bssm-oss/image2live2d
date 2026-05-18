#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { generateMoc3 } from "./stretchy_moc3writer.mjs";

function usage() {
  console.error("usage: static_quad_live2d.mjs --input-image input.png --output-dir out --model-name model");
}

function parseArgs(argv) {
  const args = { modelName: "static_quad" };
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
    throw new Error("static quad generation currently requires a PNG input image");
  }
  return { width: header.readUInt32BE(16), height: header.readUInt32BE(20) };
}

function safeModelName(name) {
  const cleaned = String(name || "static_quad").replace(/[^A-Za-z0-9_.-]/g, "_");
  if (!/^[A-Za-z0-9]/.test(cleaned)) return `model_${cleaned}`;
  return cleaned.slice(0, 128) || "static_quad";
}

function buildProject(width, height) {
  return {
    canvas: { width, height },
    parameters: [{ id: "ParamOpacity", name: "Opacity", min: 0, max: 1, default: 1 }],
    animations: [],
    nodes: [
      { id: "PartRoot", name: "Root", type: "group", visible: true },
      {
        id: "ImageQuad",
        name: "ImageQuad",
        type: "part",
        parent: "PartRoot",
        visible: true,
        opacity: 1,
        draw_order: 0,
        mesh: {
          vertices: [
            { x: 0, y: 0 },
            { x: width, y: 0 },
            { x: width, y: height },
            { x: 0, y: height },
          ],
          triangles: [
            [0, 1, 2],
            [0, 2, 3],
          ],
          uvs: [0, 0, 1, 0, 1, 1, 0, 1],
        },
      },
    ],
  };
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
  const textureDirName = `${modelName}.static`;
  const textureReference = `${textureDirName}/texture_00.png`;

  fs.mkdirSync(path.join(outputDir, textureDirName), { recursive: true });
  fs.copyFileSync(inputPath, path.join(outputDir, textureReference));

  const project = buildProject(width, height);
  const regions = new Map([
    [
      "ImageQuad",
      {
        atlasIndex: 0,
        x: 0,
        y: 0,
        width: 1,
        height: 1,
        srcX: 0,
        srcY: 0,
        srcWidth: width,
        srcHeight: height,
        cropW: width,
        cropH: height,
      },
    ],
  ]);
  const moc3 = generateMoc3({ project, regions, atlasSize: 1, numAtlases: 1 });
  fs.writeFileSync(path.join(outputDir, `${modelName}.moc3`), Buffer.from(moc3));
  fs.writeFileSync(
    path.join(outputDir, `${modelName}.model3.json`),
    JSON.stringify(
      {
        Version: 3,
        FileReferences: {
          Moc: `${modelName}.moc3`,
          Textures: [textureReference],
        },
        Groups: [],
        HitAreas: [],
        Meta: {
          GeneratedBy: "image2live2d experimental static quad generator",
          ExperimentalStaticQuad: true,
          SourceImage: path.basename(inputPath),
        },
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );
  console.log(path.join(outputDir, `${modelName}.model3.json`));
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 2;
}
