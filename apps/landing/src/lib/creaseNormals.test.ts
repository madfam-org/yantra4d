import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { computeCreaseNormals, PREVIEW_CREASE_ANGLE_DEG } from './creaseNormals';

// Everything from the first shared constant down: the constants and the function.
const functionBody = (source: string) => source.slice(source.indexOf('/** A point shared by more faces'));

describe('computeCreaseNormals', () => {
  it('is the same code as the Studio twin', () => {
    const here = readFileSync(resolve(__dirname, 'creaseNormals.ts'), 'utf8');
    const studio = readFileSync(resolve(__dirname, '../../../studio/src/lib/creaseNormals.ts'), 'utf8');
    for (const source of [here, studio]) expect(source.indexOf('/** A point shared by more faces')).toBeGreaterThan(0);
    expect(functionBody(here)).toBe(functionBody(studio));
    // The Studio draws the same preview meshes, so the two angles must not drift apart.
    expect(studio).toContain(`export const PREVIEW_CREASE_ANGLE_DEG = ${PREVIEW_CREASE_ANGLE_DEG}\n`);
  });

  it('keeps a right angle sharp and shares a normal across a shallow one', () => {
    const positions = new Float32Array([
      // Two triangles folded 10° along the Y axis: one surface.
      0, 0, 0, 1, 0, 0, 0, 1, 0,
      0, 0, 0, 0, 1, 0, -Math.cos(Math.PI / 18), 0, -Math.sin(Math.PI / 18),
      // A wall at 90° to the first triangle along the X axis: an edge.
      0, 0, 0, 1, 0, -1, 1, 0, 0,
    ]);
    const normals = computeCreaseNormals(positions, PREVIEW_CREASE_ANGLE_DEG);
    const at = (corner: number) => [...normals.subarray(corner * 3, corner * 3 + 3)];
    // The origin corner of the two folded triangles: one shared normal, between the two faces.
    expect(at(0)).toEqual(at(3));
    expect(at(0)[2]).toBeLessThan(1);
    expect(at(0)[2]).toBeGreaterThan(0.99);
    // The wall keeps its own.
    expect(at(6)[1]).toBeCloseTo(-1, 5);
  });
});
