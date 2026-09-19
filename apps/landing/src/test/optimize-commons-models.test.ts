/**
 * Tests for `scripts/dev/optimize-commons-models.mjs`.
 *
 * The optimizer writes `public/models/*.lod*.glb` + `manifest.json` (v2), which
 * is what the landing streams, so its guarantees are pinned here rather than
 * left to a manual run:
 *
 *   1. a dense mesh comes out under the triangle budget, meshopt-compressed,
 *      POSITION-only, and re-readable;
 *   2. two runs with the same `--generated` are byte-identical;
 *   3. a byte-budget breach is exit 1 under --strict, and the file is still written;
 *   4. the manifest is exactly the v2 contract the page's reader depends on;
 *   5. the legacy-input path removes the uncompressed file only with --clean.
 *
 * Everything runs against throwaway fixture repos in a temp dir with synthetic
 * geometry (a UV sphere built with @gltf-transform/core), so nothing here moves
 * when a real cartridge is added.
 */
import { describe, it, expect, beforeAll, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Document, NodeIO, Logger, Primitive } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { dequantize, getBounds } from "@gltf-transform/functions";
import { MeshoptDecoder } from "meshoptimizer";
import {
  EXIT_BUDGET,
  EXIT_DRIFT,
  EXIT_FAILED,
  EXIT_OK,
  EXIT_USAGE,
  GENERATOR,
  LOD0_ALL_MAX_INPUTS,
  MANIFEST_VERSION,
  buildManifest,
  loadDeps,
  makeContext,
  manifestBudgets,
  optimizeGlb,
  parseArgs,
  parseInputName,
  resolveLod0Selection,
  run,
  targetsFor,
  validateExceptions,
} from "../../../../scripts/dev/optimize-commons-models.mjs";

// ─── Synthetic geometry ─────────────────────────────────────────────────────

const silent = () => new Logger(Logger.Verbosity.SILENT);
const writerIO = new NodeIO().setLogger(silent());
const readerIO = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ "meshopt.decoder": MeshoptDecoder })
  .setLogger(silent());

/** A UV sphere: `rings * segments * 2` triangles, indexed, POSITION only. */
function sphereArrays(segments: number, rings: number, radius = 1) {
  const positions: number[] = [];
  for (let r = 0; r <= rings; r += 1) {
    const phi = (r / rings) * Math.PI;
    for (let s = 0; s <= segments; s += 1) {
      const theta = (s / segments) * Math.PI * 2;
      positions.push(
        radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta),
      );
    }
  }
  const indices: number[] = [];
  for (let r = 0; r < rings; r += 1) {
    for (let s = 0; s < segments; s += 1) {
      const a = r * (segments + 1) + s;
      const b = a + segments + 1;
      indices.push(a, b, a + 1, a + 1, b, b + 1);
    }
  }
  return {
    positions: new Float32Array(positions),
    indices: new Uint32Array(indices),
  };
}

function cubeArrays(size = 1) {
  const h = size / 2;
  const positions = new Float32Array([
    -h,
    -h,
    -h,
    h,
    -h,
    -h,
    h,
    h,
    -h,
    -h,
    h,
    -h,
    -h,
    -h,
    h,
    h,
    -h,
    h,
    h,
    h,
    h,
    -h,
    h,
    h,
  ]);
  const indices = new Uint32Array([
    0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 2, 3, 7, 2, 7, 6, 1,
    2, 6, 1, 6, 5, 0, 4, 7, 0, 7, 3,
  ]);
  return { positions, indices };
}

type MeshSpec = {
  positions: Float32Array;
  indices: Uint32Array;
  translation?: [number, number, number];
  scale?: [number, number, number];
  material?: boolean;
};

/** A GLB with one node per spec, each with its own mesh — and an unused material/normals to be dropped. */
async function buildGlb(specs: MeshSpec[]): Promise<Uint8Array> {
  const doc = new Document().setLogger(silent());
  const buffer = doc.createBuffer();
  const scene = doc.createScene();
  for (const spec of specs) {
    const position = doc
      .createAccessor()
      .setType("VEC3")
      .setArray(spec.positions)
      .setBuffer(buffer);
    const indices = doc
      .createAccessor()
      .setType("SCALAR")
      .setArray(spec.indices)
      .setBuffer(buffer);
    const prim = doc
      .createPrimitive()
      .setMode(Primitive.Mode.TRIANGLES)
      .setAttribute("POSITION", position)
      .setIndices(indices);
    if (spec.material) {
      const normals = doc
        .createAccessor()
        .setType("VEC3")
        .setArray(
          new Float32Array(spec.positions.length)
            .fill(0)
            .map((_, i) => (i % 3 === 1 ? 1 : 0)),
        )
        .setBuffer(buffer);
      prim.setAttribute("NORMAL", normals);
      prim.setMaterial(
        doc.createMaterial("paint").setBaseColorFactor([1, 0, 0, 1]),
      );
    }
    const node = doc.createNode().setMesh(doc.createMesh().addPrimitive(prim));
    if (spec.translation) node.setTranslation(spec.translation);
    if (spec.scale) node.setScale(spec.scale);
    scene.addChild(node);
  }
  return writerIO.writeBinary(doc);
}

const DENSE_SPHERE = () => ({ ...sphereArrays(80, 80), material: true }); // 12,800 triangles
const SMALL_SPHERE = () => sphereArrays(12, 8); // 192 triangles

// ─── Fixture repo builder ───────────────────────────────────────────────────

const BUDGETS = {
  _comment: "test budgets",
  lod1Bytes: 8192,
  lod0Bytes: 49152,
  lod1Triangles: 500,
  lod0Triangles: 4000,
  keyframeBytes: 49152,
};

type RepoSpec = {
  budgets?: Record<string, unknown>;
  /** Files written to apps/landing/public/models/raw/. */
  raw?: Record<string, Uint8Array>;
  /** Files written straight into apps/landing/public/models/ (the legacy layout). */
  legacy?: Record<string, Uint8Array>;
  /** Manifests written to projects/<slug>/project.json. */
  manifests?: Array<{ slug: string; animations?: boolean }>;
  /** apps/landing/models.hero.json contents. */
  hero?: string[];
};

let repos: string[] = [];

function makeRepo(spec: RepoSpec = {}): string {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "y4d-models-"));
  repos.push(repo);
  const landing = path.join(repo, "apps", "landing");
  const models = path.join(landing, "public", "models");
  fs.mkdirSync(models, { recursive: true });
  fs.writeFileSync(
    path.join(landing, "perf-budgets.json"),
    JSON.stringify({ version: 1, meshes: spec.budgets ?? BUDGETS }, null, 2),
  );
  if (spec.raw) {
    fs.mkdirSync(path.join(models, "raw"), { recursive: true });
    for (const [name, bytes] of Object.entries(spec.raw))
      fs.writeFileSync(path.join(models, "raw", name), bytes);
  }
  for (const [name, bytes] of Object.entries(spec.legacy ?? {}))
    fs.writeFileSync(path.join(models, name), bytes);
  for (const m of spec.manifests ?? []) {
    const dir = path.join(repo, "projects", m.slug);
    fs.mkdirSync(dir, { recursive: true });
    const manifest: Record<string, unknown> = {
      project: { slug: m.slug, name: m.slug },
    };
    if (m.animations) {
      manifest.animations = [
        {
          id: "sweep",
          label: "Sweep",
          from_state: { a: 1 },
          to_state: { a: 2 },
          frames: 2,
        },
      ];
    }
    fs.writeFileSync(path.join(dir, "project.json"), JSON.stringify(manifest));
  }
  if (spec.hero)
    fs.writeFileSync(
      path.join(landing, "models.hero.json"),
      JSON.stringify(spec.hero),
    );
  return repo;
}

const modelsDir = (repo: string) =>
  path.join(repo, "apps", "landing", "public", "models");
const readManifest = (repo: string) =>
  JSON.parse(
    fs.readFileSync(path.join(modelsDir(repo), "manifest.json"), "utf8"),
  );

/** Collect stdout/stderr from a `run()` call instead of printing it. */
function capture() {
  const out: string[] = [];
  const err: string[] = [];
  return {
    out,
    err,
    log: (m: unknown) => out.push(String(m)),
    logError: (m: unknown) => err.push(String(m)),
  };
}

/** Drive the CLI against a fixture repo with the manifest timestamp pinned. */
async function optimize(
  repo: string,
  argv: string[] = [],
  extra: Record<string, unknown> = {},
) {
  const io = capture();
  const code = await run({
    argv: [
      "--generated",
      "2026-09-19T00:00:00Z",
      "--commons-pin",
      "none",
      ...argv,
    ],
    repo,
    env: {},
    ...io,
    ...extra,
  });
  return { code, ...io };
}

/** The JSON chunk of a GLB, straight from the bytes. */
function glbJson(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const jsonLength = view.getUint32(12, true);
  return JSON.parse(
    new TextDecoder().decode(bytes.subarray(20, 20 + jsonLength)),
  );
}

async function triangleCountOf(bytes: Uint8Array) {
  const doc = await readerIO.readBinary(bytes);
  let count = 0;
  for (const mesh of doc.getRoot().listMeshes()) {
    for (const prim of mesh.listPrimitives())
      count += prim.getIndices()!.getCount() / 3;
  }
  return { doc, count };
}

let deps: Awaited<ReturnType<typeof loadDeps>>;
let dense: Uint8Array;
let small: Uint8Array;

beforeAll(async () => {
  deps = await loadDeps();
  dense = await buildGlb([DENSE_SPHERE()]);
  small = await buildGlb([SMALL_SPHERE()]);
});

afterEach(() => {
  for (const repo of repos) fs.rmSync(repo, { recursive: true, force: true });
  repos = [];
});

// ─── Input naming ───────────────────────────────────────────────────────────

describe("parseInputName", () => {
  it("recognises base renders and keyframes", () => {
    expect(parseInputName("gridfinity.glb")).toEqual({
      kind: "base",
      slug: "gridfinity",
    });
    expect(parseInputName("motor-mount.nema-sweep.0.glb")).toEqual({
      kind: "frame",
      slug: "motor-mount",
      animation: "nema-sweep",
      index: 0,
    });
    expect(parseInputName("motor-mount.nema-sweep.12.glb")!.index).toBe(12);
  });

  it("ignores outputs, the manifest and anything else", () => {
    // An output must never be picked up as an input by a second run over the same dir.
    expect(parseInputName("gridfinity.lod1.glb")).toBeNull();
    expect(parseInputName("gridfinity.lod0.glb")).toBeNull();
    expect(parseInputName("manifest.json")).toBeNull();
    expect(parseInputName(".hidden.glb")).toBeNull();
    expect(parseInputName("Gridfinity.glb")).toBeNull();
    expect(parseInputName("motor-mount.nema-sweep.x.glb")).toBeNull();
  });
});

describe("parseArgs", () => {
  it("accepts both flag spellings and rejects the rest", () => {
    expect(
      parseArgs([
        "--lod0",
        "hero",
        "--strict",
        "--generated=2026-01-01T00:00:00Z",
      ]),
    ).toEqual({
      lod0: "hero",
      strict: true,
      generated: "2026-01-01T00:00:00Z",
    });
    expect(() => parseArgs(["--bogus"])).toThrow(/Unknown flag/);
    expect(() => parseArgs(["--generated", "yesterday"])).toThrow(/ISO-8601/);
    expect(() => parseArgs(["--commons-pin", "abc"])).toThrow(/40-hex/);
  });
});

// ─── Geometry pipeline ──────────────────────────────────────────────────────

describe("optimizeGlb", () => {
  it("simplifies a dense mesh under the triangle budget, meshopt-compressed and POSITION-only", async () => {
    const targets = {
      lod1: { triangles: BUDGETS.lod1Triangles, bytes: BUDGETS.lod1Bytes },
      lod0: { triangles: BUDGETS.lod0Triangles, bytes: BUDGETS.lod0Bytes },
    };
    const { before, outputs } = await optimizeGlb(dense, targets, deps);
    expect(before.triangles).toBe(12_800);

    const lod1 = outputs.lod1!;
    expect(lod1.triangles).toBeLessThanOrEqual(BUDGETS.lod1Triangles);
    expect(lod1.triangles).toBeGreaterThan(100);
    expect(lod1.bytes.length).toBeLessThanOrEqual(BUDGETS.lod1Bytes);
    expect(lod1.withinBytes).toBe(true);

    const json = glbJson(lod1.bytes);
    expect(json.extensionsRequired).toContain("EXT_meshopt_compression");
    expect(json.extensionsUsed).toContain("EXT_meshopt_compression");
    expect(json.materials).toBeUndefined();
    expect(json.meshes).toHaveLength(1);
    expect(json.meshes[0].primitives).toHaveLength(1);
    expect(Object.keys(json.meshes[0].primitives[0].attributes)).toEqual([
      "POSITION",
    ]);
    expect(json.asset.generator).toBeDefined();
    expect(JSON.stringify(json)).not.toMatch(/20\d\d-\d\d-\d\dT/); // no timestamps inside the GLB

    // Re-reads with gltf-transform + the meshopt decoder, at the triangle count the manifest will claim.
    const { count } = await triangleCountOf(lod1.bytes);
    expect(count).toBe(lod1.triangles);

    const lod0 = outputs.lod0!;
    expect(lod0.triangles).toBeLessThanOrEqual(BUDGETS.lod0Triangles);
    expect(lod0.triangles).toBeGreaterThan(lod1.triangles);
    expect(lod0.bytes.length).toBeLessThanOrEqual(BUDGETS.lod0Bytes);
  });

  it("keeps a mesh that is already under budget intact and skips a pointless lod0", async () => {
    const targets = {
      lod1: { triangles: BUDGETS.lod1Triangles, bytes: BUDGETS.lod1Bytes },
      lod0: { triangles: BUDGETS.lod0Triangles, bytes: BUDGETS.lod0Bytes },
    };
    const { outputs } = await optimizeGlb(small, targets, deps);
    expect(outputs.lod1!.triangles).toBe(192);
    expect(outputs.lod0).toBeUndefined();
    expect(outputs.lod0Skipped).toMatch(/already complete/);
  });

  it("bakes every node into one world-space primitive, dropping materials and normals", async () => {
    const glb = await buildGlb([
      { ...cubeArrays(2), translation: [10, 0, 0], material: true },
      { ...cubeArrays(2), scale: [-1, 1, 1] },
    ]);
    const { before, outputs } = await optimizeGlb(
      glb,
      { lod1: { triangles: 1000, bytes: 100_000 } },
      deps,
    );
    expect(before.triangles).toBe(24);
    const lod1 = outputs.lod1!;
    expect(lod1.triangles).toBe(24);
    const json = glbJson(lod1.bytes);
    expect(json.meshes).toHaveLength(1);
    expect(json.materials).toBeUndefined();
    expect(Object.keys(json.meshes[0].primitives[0].attributes)).toEqual([
      "POSITION",
    ]);

    // The translated cube spans x ∈ [9, 11], the mirrored one x ∈ [-1, 1]: both
    // were baked into world space rather than left on node transforms.
    const { doc } = await triangleCountOf(lod1.bytes);
    await doc.transform(dequantize());
    const bounds = getBounds(doc.getRoot().listScenes()[0]);
    expect(bounds.min[0]).toBeCloseTo(-1, 1);
    expect(bounds.max[0]).toBeCloseTo(11, 1);
  });

  it("lowers the triangle target when the byte budget is the binding one", async () => {
    const { outputs } = await optimizeGlb(
      dense,
      { lod0: { triangles: 4000, bytes: 6000 } },
      deps,
    );
    const lod0 = outputs.lod0!;
    expect(lod0.byteCapped).toBe(true);
    expect(lod0.triangles).toBeLessThan(4000);
    expect(lod0.bytes.length).toBeLessThanOrEqual(6000);
  });
});

// ─── CLI: raw inputs ────────────────────────────────────────────────────────

describe("run — raw inputs", () => {
  it("writes lod files, keyframes and the v2 manifest", async () => {
    const repo = makeRepo({
      raw: {
        "gridfinity.glb": dense,
        "motor-mount.glb": small,
        "motor-mount.sweep.1.glb": dense,
        "motor-mount.sweep.0.glb": small,
      },
    });
    const { code, err } = await optimize(repo, [
      "--commons-pin",
      "f2c578f78037c37f0f29fe0571b946aeeb45bc0f",
    ]);
    expect(err).toEqual([]);
    expect(code).toBe(EXIT_OK);

    const files = fs.readdirSync(modelsDir(repo)).sort();
    expect(files).toEqual([
      "gridfinity.lod0.glb",
      "gridfinity.lod1.glb",
      "manifest.json",
      "motor-mount.lod1.glb",
      "motor-mount.sweep.0.glb",
      "motor-mount.sweep.1.glb",
      "raw",
    ]);

    const manifest = readManifest(repo);
    // Key order is part of the contract: the reader and the drift lane both diff it as text.
    expect(Object.keys(manifest)).toEqual([
      "version",
      "generated",
      "generator",
      "source",
      "budgets",
      "models",
    ]);
    expect(manifest.version).toBe(MANIFEST_VERSION);
    expect(manifest.generated).toBe("2026-09-19T00:00:00Z");
    expect(manifest.generator).toBe(GENERATOR);
    expect(manifest.source).toEqual({
      kind: "render-api",
      commons_pin: "f2c578f78037c37f0f29fe0571b946aeeb45bc0f",
    });
    expect(manifest.budgets).toEqual(manifestBudgets(BUDGETS));
    expect(manifest.budgets._comment).toBeUndefined();

    expect(manifest.models.map((m: { slug: string }) => m.slug)).toEqual([
      "gridfinity",
      "motor-mount",
    ]);
    const [gridfinity, motorMount] = manifest.models;
    expect(Object.keys(gridfinity)).toEqual(["slug", "size", "lod1", "lod0"]);
    expect(Object.keys(gridfinity.lod1)).toEqual([
      "file",
      "bytes",
      "triangles",
    ]);
    expect(gridfinity.lod1.file).toBe("gridfinity.lod1.glb");
    expect(gridfinity.lod1.bytes).toBe(
      fs.statSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")).size,
    );
    expect(gridfinity.lod1.triangles).toBeLessThanOrEqual(
      BUDGETS.lod1Triangles,
    );
    expect(gridfinity.lod0.triangles).toBeGreaterThan(
      gridfinity.lod1.triangles,
    );
    // v1 readers keep working on slug + size: size is the smallest file the entry offers.
    expect(gridfinity.size).toBe(
      Math.min(gridfinity.lod1.bytes, gridfinity.lod0.bytes),
    );

    expect(Object.keys(motorMount)).toEqual(["slug", "size", "lod1", "frames"]);
    expect(motorMount.lod0).toBeUndefined();
    expect(motorMount.frames.map((f: { index: number }) => f.index)).toEqual([
      0, 1,
    ]);
    expect(Object.keys(motorMount.frames[0])).toEqual([
      "animation",
      "index",
      "file",
      "bytes",
      "triangles",
    ]);
    expect(motorMount.frames[1]).toMatchObject({
      animation: "sweep",
      index: 1,
      file: "motor-mount.sweep.1.glb",
    });
    expect(motorMount.frames[1].triangles).toBeLessThanOrEqual(
      BUDGETS.lod0Triangles,
    );
    expect(motorMount.size).toBe(
      Math.min(
        motorMount.lod1.bytes,
        ...motorMount.frames.map((f: { bytes: number }) => f.bytes),
      ),
    );
  });

  it("is byte-identical across two runs with the same --generated", async () => {
    const a = makeRepo({
      raw: { "gridfinity.glb": dense, "motor-mount.sweep.0.glb": small },
    });
    const b = makeRepo({
      raw: { "gridfinity.glb": dense, "motor-mount.sweep.0.glb": small },
    });
    expect((await optimize(a)).code).toBe(EXIT_OK);
    expect((await optimize(b)).code).toBe(EXIT_OK);
    const names = fs
      .readdirSync(modelsDir(a))
      .filter((n) => n !== "raw")
      .sort();
    expect(names).toEqual(
      fs
        .readdirSync(modelsDir(b))
        .filter((n) => n !== "raw")
        .sort(),
    );
    expect(names.length).toBeGreaterThan(2);
    for (const name of names) {
      expect(
        fs
          .readFileSync(path.join(modelsDir(a), name))
          .equals(fs.readFileSync(path.join(modelsDir(b), name))),
      ).toBe(true);
    }
  });

  it("exits 1 under --strict when a file cannot meet its byte budget, and still writes it", async () => {
    // A byte budget no mesh can meet: the floor of 64 triangles is still bigger than this.
    const budgets = { ...BUDGETS, lod1Bytes: 200 };
    const repo = makeRepo({ budgets, raw: { "gridfinity.glb": dense } });
    const relaxed = await optimize(repo);
    expect(relaxed.code).toBe(EXIT_OK);
    expect(relaxed.err.join("\n")).toMatch(
      /WARNING: 1 output\(s\) over their byte budget/,
    );

    const strict = await optimize(repo, ["--strict"]);
    expect(strict.code).toBe(EXIT_BUDGET);
    expect(strict.err.join("\n")).toMatch(
      /ERROR: 1 output\(s\) over their byte budget/,
    );
    expect(strict.err.join("\n")).toContain("gridfinity.lod1.glb");
    expect(
      fs.existsSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")),
    ).toBe(true);
    expect(readManifest(repo).models[0].lod1.bytes).toBeGreaterThan(200);
    expect(strict.out.join("\n")).toMatch(/OVER \+\d+%/);
  });

  it("a budget kept by exception passes --strict and is recorded on the manifest entry", async () => {
    // Same floor as above; the exception raises gridfinity's lod1 cap, with a reason, and nothing else.
    const reason = "test lattice: the simplifier floors above 200 B";
    const budgets = {
      ...BUDGETS,
      lod1Bytes: 200,
      exceptions: { gridfinity: { lod1Bytes: 65536, reason } },
    };
    const repo = makeRepo({
      budgets,
      raw: { "gridfinity.glb": dense, "motor-mount.glb": small },
    });
    const strict = await optimize(repo, ["--strict"]);
    // gridfinity passes by exception; motor-mount still breaks the 200 B block budget.
    expect(strict.code).toBe(EXIT_BUDGET);
    expect(strict.err.join("\n")).toMatch(
      /ERROR: 1 output\(s\) over their byte budget/,
    );
    expect(strict.err.join("\n")).toContain("motor-mount.lod1.glb");
    expect(strict.err.join("\n")).not.toContain("gridfinity.lod1.glb");
    expect(strict.out.join("\n")).toMatch(
      /gridfinity\.lod1\.glb.*ok \(by exception/,
    );
    const manifest = readManifest(repo);
    const gridfinity = manifest.models.find(
      (m: { slug: string }) => m.slug === "gridfinity",
    );
    const motorMount = manifest.models.find(
      (m: { slug: string }) => m.slug === "motor-mount",
    );
    expect(gridfinity.budget).toEqual({ lod1Bytes: 65536, reason });
    expect(gridfinity.lod1.bytes).toBeGreaterThan(200);
    expect(motorMount).not.toHaveProperty("budget");
    // The block as this repo declares it (lod1 at 200 B), never the exceptions map.
    expect(manifest.budgets).toEqual(
      manifestBudgets({ ...BUDGETS, lod1Bytes: 200 }),
    );
    expect(manifest.budgets).not.toHaveProperty("exceptions");
  });

  it("rejects a malformed exceptions map as a usage error, before touching any file", async () => {
    const budgets = {
      ...BUDGETS,
      exceptions: { gridfinity: { lod1Bytes: 65536 } },
    }; // no reason
    const repo = makeRepo({ budgets, raw: { "gridfinity.glb": small } });
    const result = await optimize(repo);
    expect(result.code).toBe(EXIT_USAGE);
    expect(result.err.join("\n")).toMatch(
      /meshes\.exceptions\.gridfinity needs a written reason/,
    );
    expect(fs.existsSync(path.join(modelsDir(repo), "manifest.json"))).toBe(
      false,
    );
  });

  it("appends the report to $GITHUB_STEP_SUMMARY when set", async () => {
    const repo = makeRepo({ raw: { "gridfinity.glb": small } });
    const summary = path.join(repo, "summary.md");
    const io = capture();
    const code = await run({
      argv: ["--generated", "2026-09-19T00:00:00Z", "--commons-pin", "none"],
      repo,
      env: { GITHUB_STEP_SUMMARY: summary },
      ...io,
    });
    expect(code).toBe(EXIT_OK);
    const text = fs.readFileSync(summary, "utf8");
    expect(text).toContain("### Commons models");
    expect(text).toContain("| gridfinity | lod1 |");
  });

  it("reports an unreadable input as a failure without dropping the others", async () => {
    const repo = makeRepo({
      raw: {
        "broken.glb": new Uint8Array([1, 2, 3, 4]),
        "gridfinity.glb": small,
      },
    });
    const { code, err } = await optimize(repo);
    expect(code).toBe(EXIT_FAILED);
    expect(err.join("\n")).toMatch(/FAILED broken\.glb/);
    expect(
      fs.existsSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")),
    ).toBe(true);
    expect(
      readManifest(repo).models.map((m: { slug: string }) => m.slug),
    ).toEqual(["gridfinity"]);
  });

  it("refuses to run with nothing to do", async () => {
    const repo = makeRepo({ raw: {} });
    const { code, err } = await optimize(repo);
    expect(code).toBe(EXIT_USAGE);
    expect(err.join("\n")).toMatch(/No inputs/);
  });
});

// ─── CLI: --check and --clean ───────────────────────────────────────────────

describe("run --check / --clean", () => {
  it("passes right after a run, fails on a tampered output, and never writes", async () => {
    const repo = makeRepo({ raw: { "gridfinity.glb": small } });
    expect((await optimize(repo)).code).toBe(EXIT_OK);
    const check = await optimize(repo, ["--check"]);
    expect(check.code).toBe(EXIT_OK);
    expect(check.out.join("\n")).toMatch(/up to date/);

    const lod1 = path.join(modelsDir(repo), "gridfinity.lod1.glb");
    fs.appendFileSync(lod1, "x");
    const drift = await optimize(repo, ["--check"]);
    expect(drift.code).toBe(EXIT_DRIFT);
    expect(drift.err.join("\n")).toMatch(/DRIFT/);
    expect(drift.err.join("\n")).toContain("differs: gridfinity.lod1.glb");
    // --check compares; it never repairs.
    expect(fs.readFileSync(lod1).subarray(-1).toString()).toBe("x");
  });

  it("reuses the on-disk manifest timestamp under --check, so only content counts as drift", async () => {
    const repo = makeRepo({ raw: { "gridfinity.glb": small } });
    expect((await optimize(repo)).code).toBe(EXIT_OK);
    const io = capture();
    // No --generated here: a fresh timestamp must not read as drift.
    expect(
      await run({
        argv: ["--check", "--commons-pin", "none"],
        repo,
        env: {},
        ...io,
      }),
    ).toBe(EXIT_OK);
  });

  it("removes stale outputs only with --clean", async () => {
    const repo = makeRepo({ raw: { "gridfinity.glb": small } });
    const stale = path.join(modelsDir(repo), "retired.lod1.glb");
    const staleFrame = path.join(modelsDir(repo), "retired.sweep.0.glb");
    fs.writeFileSync(stale, "old");
    fs.writeFileSync(staleFrame, "old");

    const kept = await optimize(repo);
    expect(kept.code).toBe(EXIT_OK);
    expect(kept.err.join("\n")).toMatch(
      /would be removed by --clean: retired\.lod1\.glb, retired\.sweep\.0\.glb/,
    );
    expect(fs.existsSync(stale)).toBe(true);

    const checkClean = await optimize(repo, ["--check", "--clean"]);
    expect(checkClean.code).toBe(EXIT_DRIFT);
    expect(checkClean.err.join("\n")).toContain(
      "stale (would be removed): retired.lod1.glb",
    );

    const cleaned = await optimize(repo, ["--clean"]);
    expect(cleaned.code).toBe(EXIT_OK);
    expect(fs.existsSync(stale)).toBe(false);
    expect(fs.existsSync(staleFrame)).toBe(false);
    expect(
      fs.existsSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")),
    ).toBe(true);
  });
});

// ─── CLI: legacy inputs ─────────────────────────────────────────────────────

describe("run — legacy uncompressed inputs", () => {
  it("reads public/models/<slug>.glb when there is no raw dir and removes it only with --clean", async () => {
    const repo = makeRepo({
      legacy: { "gridfinity.glb": dense, "motor-mount.glb": small },
    });
    const legacy = path.join(modelsDir(repo), "gridfinity.glb");

    const first = await optimize(repo);
    expect(first.code).toBe(EXIT_OK);
    expect(fs.existsSync(legacy)).toBe(true);
    expect(
      fs.existsSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")),
    ).toBe(true);
    expect(readManifest(repo).source.kind).toBe("legacy-glb");
    expect(first.err.join("\n")).toMatch(
      /would be removed by --clean: gridfinity\.glb, motor-mount\.glb/,
    );

    const second = await optimize(repo, ["--clean"]);
    expect(second.code).toBe(EXIT_OK);
    expect(fs.existsSync(legacy)).toBe(false);
    expect(fs.existsSync(path.join(modelsDir(repo), "motor-mount.glb"))).toBe(
      false,
    );
    expect(fs.readdirSync(modelsDir(repo)).sort()).toEqual([
      "gridfinity.lod0.glb",
      "gridfinity.lod1.glb",
      "manifest.json",
      "motor-mount.lod1.glb",
    ]);
    expect(
      readManifest(repo).models.map((m: { slug: string }) => m.slug),
    ).toEqual(["gridfinity", "motor-mount"]);

    // With the legacy files consumed there is nothing left to read: say so, do not silently rewrite.
    const third = await optimize(repo);
    expect(third.code).toBe(EXIT_USAGE);
    expect(
      fs.existsSync(path.join(modelsDir(repo), "gridfinity.lod1.glb")),
    ).toBe(true);
  });

  it("never treats its own outputs as inputs", async () => {
    const repo = makeRepo({ legacy: { "gridfinity.glb": small } });
    expect((await optimize(repo)).code).toBe(EXIT_OK);
    const again = await optimize(repo);
    expect(again.code).toBe(EXIT_OK);
    expect(readManifest(repo).models).toHaveLength(1);
    expect(
      fs.readdirSync(modelsDir(repo)).filter((n) => n.includes(".lod1.lod")),
    ).toEqual([]);
  });
});

// ─── lod0 selection ─────────────────────────────────────────────────────────

describe("resolveLod0Selection", () => {
  it("defaults to all for a small set and to hero above the threshold", () => {
    const repo = makeRepo({
      manifests: [
        { slug: "motor-mount", animations: true },
        { slug: "gridfinity" },
      ],
    });
    const ctx = makeContext({ repo });
    const few = ["gridfinity", "motor-mount"];
    expect(resolveLod0Selection(undefined, few, ctx)).toEqual({
      mode: "all",
      slugs: new Set(few),
    });

    const many = Array.from(
      { length: LOD0_ALL_MAX_INPUTS + 1 },
      (_, i) => `cartridge-${i}`,
    ).concat(few);
    const picked = resolveLod0Selection(undefined, many, ctx);
    expect(picked.mode).toBe("hero");
    expect([...picked.slugs]).toEqual(["motor-mount"]);
  });

  it("prefers models.hero.json over the animated manifests", () => {
    const repo = makeRepo({
      manifests: [{ slug: "motor-mount", animations: true }],
      hero: ["gridfinity"],
    });
    const ctx = makeContext({ repo });
    expect([
      ...resolveLod0Selection("hero", ["gridfinity", "motor-mount"], ctx).slugs,
    ]).toEqual(["gridfinity"]);
  });

  it("accepts an explicit list, ignoring slugs with no input, and none", () => {
    const ctx = makeContext({ repo: makeRepo() });
    const list = resolveLod0Selection(
      "gridfinity, nope",
      ["gridfinity", "motor-mount"],
      ctx,
    );
    expect([...list.slugs]).toEqual(["gridfinity"]);
    expect(list.unknown).toEqual(["nope"]);
    expect(resolveLod0Selection("none", ["gridfinity"], ctx).slugs.size).toBe(
      0,
    );
  });

  it("--lod0 hero from the CLI emits lod0 for animated cartridges only", async () => {
    const repo = makeRepo({
      raw: { "gridfinity.glb": dense, "motor-mount.glb": dense },
      manifests: [
        { slug: "motor-mount", animations: true },
        { slug: "gridfinity" },
      ],
    });
    expect((await optimize(repo, ["--lod0", "hero"])).code).toBe(EXIT_OK);
    const files = fs.readdirSync(modelsDir(repo));
    expect(files).toContain("motor-mount.lod0.glb");
    expect(files).not.toContain("gridfinity.lod0.glb");
  });
});

// ─── Manifest builder ───────────────────────────────────────────────────────

describe("buildManifest", () => {
  it("sorts models by slug and frames by animation then index", () => {
    const entries = new Map([
      [
        "zeta",
        {
          lod1: { file: "zeta.lod1.glb", bytes: 10, triangles: 5 },
          lod0: null,
          frames: [],
        },
      ],
      [
        "alpha",
        {
          lod1: { file: "alpha.lod1.glb", bytes: 30, triangles: 5 },
          lod0: { file: "alpha.lod0.glb", bytes: 40, triangles: 9 },
          frames: [
            {
              file: "alpha.b.1.glb",
              bytes: 8,
              triangles: 1,
              animation: "b",
              index: 1,
            },
            {
              file: "alpha.a.10.glb",
              bytes: 9,
              triangles: 1,
              animation: "a",
              index: 10,
            },
            {
              file: "alpha.a.2.glb",
              bytes: 7,
              triangles: 1,
              animation: "a",
              index: 2,
            },
          ],
        },
      ],
    ]);
    const manifest = buildManifest({
      generated: "g",
      sourceKind: "render-api",
      commonsPin: null,
      budgets: BUDGETS,
      entries,
    });
    expect(manifest.models.map((m: { slug: string }) => m.slug)).toEqual([
      "alpha",
      "zeta",
    ]);
    expect(manifest.models[0].size).toBe(7);
    expect(
      manifest.models[0].frames.map((f: { file: string }) => f.file),
    ).toEqual(["alpha.a.2.glb", "alpha.a.10.glb", "alpha.b.1.glb"]);
    expect(manifest.models[1]).toEqual({
      slug: "zeta",
      size: 10,
      lod1: { file: "zeta.lod1.glb", bytes: 10, triangles: 5 },
    });
    expect(manifest.source).toEqual({ kind: "render-api", commons_pin: null });
  });
});

describe("budget exceptions (meshes.exceptions)", () => {
  const lattice = {
    lod1Bytes: 32768,
    reason:
      "a lattice: the simplifier floors at 12,365 triangles / 28 KB; needs a smaller preview instance",
  };

  it("validates the map: slug keys, a written reason, budget keys only, positive numbers", () => {
    expect(validateExceptions(undefined)).toEqual({});
    expect(
      validateExceptions({
        _comment: "why",
        "implicit-lattice-hyperobject": lattice,
      }),
    ).toEqual({
      "implicit-lattice-hyperobject": {
        lod1Bytes: 32768,
        reason: lattice.reason,
      },
    });
    expect(() => validateExceptions([])).toThrow(
      /must be an object keyed by slug/,
    );
    expect(() => validateExceptions({ "Not A Slug": lattice })).toThrow(
      /invalid slug/,
    );
    expect(() => validateExceptions({ lattice: { lod1Bytes: 32768 } })).toThrow(
      /written reason/,
    );
    expect(() =>
      validateExceptions({ lattice: { lod1Bytes: 32768, reason: "   " } }),
    ).toThrow(/written reason/);
    expect(() =>
      validateExceptions({ lattice: { reason: "r", lod1Kilobytes: 3 } }),
    ).toThrow(/not a budget key/);
    expect(() =>
      validateExceptions({ lattice: { reason: "r", lod1Bytes: 0 } }),
    ).toThrow(/positive number/);
    expect(() => validateExceptions({ lattice: { reason: "r" } })).toThrow(
      /overrides nothing/,
    );
  });

  it("targetsFor applies the override to that slug only and reports the exception", () => {
    const budgets = { ...BUDGETS, exceptions: { lattice } };
    const forLattice = targetsFor(budgets, "lattice");
    expect(forLattice.lod1).toEqual({
      triangles: BUDGETS.lod1Triangles,
      bytes: 32768,
    });
    expect(forLattice.lod0).toEqual({
      triangles: BUDGETS.lod0Triangles,
      bytes: BUDGETS.lod0Bytes,
    });
    expect(forLattice.frame).toEqual({
      triangles: BUDGETS.lod0Triangles,
      bytes: BUDGETS.keyframeBytes,
    });
    expect(forLattice.exception).toEqual({
      lod1Bytes: 32768,
      reason: lattice.reason,
    });
    const forOther = targetsFor(budgets, "gridfinity");
    expect(forOther.lod1).toEqual({
      triangles: BUDGETS.lod1Triangles,
      bytes: BUDGETS.lod1Bytes,
    });
    expect(forOther.exception).toBeNull();
    expect(targetsFor(BUDGETS, "lattice").exception).toBeNull();
  });

  it("the manifest keeps the block scalar and records the exception on the entry", () => {
    const budgets = { ...BUDGETS, exceptions: { lattice } };
    expect(manifestBudgets(budgets)).toEqual(manifestBudgets(BUDGETS));
    expect(manifestBudgets(budgets)).not.toHaveProperty("exceptions");
    const entries = new Map([
      [
        "lattice",
        {
          lod1: { file: "lattice.lod1.glb", bytes: 28316, triangles: 12365 },
          lod0: null,
          frames: [],
          budget: { lod1Bytes: 32768, reason: lattice.reason },
        },
      ],
      [
        "plain",
        {
          lod1: { file: "plain.lod1.glb", bytes: 900, triangles: 300 },
          lod0: null,
          frames: [],
          budget: null,
        },
      ],
    ]);
    const manifest = buildManifest({
      generated: "g",
      sourceKind: "render-api",
      commonsPin: null,
      budgets,
      entries,
    });
    const [latticeModel, plainModel] = manifest.models;
    expect(latticeModel.budget).toEqual({
      lod1Bytes: 32768,
      reason: lattice.reason,
    });
    expect(plainModel).not.toHaveProperty("budget");
    expect(manifest.budgets).not.toHaveProperty("exceptions");
  });
});
