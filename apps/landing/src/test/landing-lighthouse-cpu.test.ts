/**
 * The Lighthouse CPU calibration (scripts/ci/landing-lighthouse-cpu.mjs): the
 * pure arithmetic, pinned to the numbers the runner actually produced on
 * 2026-09-19 (ci run 35460027219) so the rationale in the script stays true.
 */
import { describe, expect, it } from "vitest";
import {
  DEFAULTS,
  median,
  multiplierFor,
  parseArgs,
} from "../../../../scripts/ci/landing-lighthouse-cpu.mjs";

describe("multiplierFor", () => {
  it("gives Lighthouse's own 4× to the host its default is documented for", () => {
    expect(multiplierFor(1750)).toBe(4);
    expect(DEFAULTS.base).toBe(4);
    expect(DEFAULTS.anchor).toBe(1750);
  });

  it("scales in proportion to the BenchmarkIndex, one decimal", () => {
    expect(multiplierFor(875)).toBe(2);
    expect(multiplierFor(2200)).toBe(5);
    expect(multiplierFor(1335)).toBe(3.1); // the first ARC pod measured
  });

  it("keeps the emulated device constant across the spread one job saw", () => {
    // BenchmarkIndex → multiplier; benchmarkIndex / multiplier ≈ 437 throughout.
    const seen = { 937: 2.1, 985: 2.3, 1173: 2.7, 1504: 3.4, 1782: 4.1 };
    for (const [bi, expected] of Object.entries(seen)) {
      const m = multiplierFor(Number(bi));
      expect(m).toBe(expected);
      expect(Number(bi) / m).toBeGreaterThan(400);
      expect(Number(bi) / m).toBeLessThan(480);
    }
  });

  it("clamps to the range Lighthouse's guide gives for the reference bracket", () => {
    expect(multiplierFor(100)).toBe(1);
    expect(multiplierFor(10_000)).toBe(10);
    expect(multiplierFor(3000, { max: 6 })).toBe(6);
  });

  it("falls back to the default on anything that is not a positive number", () => {
    for (const bad of [NaN, 0, -1, undefined, null, "x", Infinity])
      expect(multiplierFor(bad)).toBe(4);
  });

  it("honours a different base and anchor", () => {
    expect(multiplierFor(1000, { base: 2, anchor: 1000 })).toBe(2);
    expect(multiplierFor(500, { base: 4, anchor: 1000, min: 1 })).toBe(2);
  });
});

describe("median", () => {
  it("handles odd, even, single and empty lists, ignoring non-numbers", () => {
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 3, 2])).toBe(2.5);
    expect(median([7])).toBe(7);
    expect(median([])).toBeNaN();
    expect(median([1, "x", 3, NaN])).toBe(2);
  });
});

describe("parseArgs", () => {
  it("defaults, then options, then the command after --", () => {
    expect(parseArgs([])).toEqual({
      samples: 3,
      anchor: 1750,
      base: 4,
      json: false,
      command: [],
    });
    expect(
      parseArgs([
        "--samples",
        "5",
        "--json",
        "--",
        "lhci",
        "autorun",
        "--collect.numberOfRuns=1",
      ]),
    ).toEqual({
      samples: 5,
      anchor: 1750,
      base: 4,
      json: true,
      command: ["lhci", "autorun", "--collect.numberOfRuns=1"],
    });
  });

  it("rejects unknown options and non-positive numbers", () => {
    expect(() => parseArgs(["--bogus"])).toThrow(/unknown option --bogus/);
    expect(() => parseArgs(["--anchor", "0"])).toThrow(/positive number/);
    expect(() => parseArgs(["--samples", "many"])).toThrow(/positive number/);
  });
});
