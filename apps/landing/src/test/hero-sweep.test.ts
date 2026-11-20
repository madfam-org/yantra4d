import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { HERO_SWEEP, sweepFrameUrl } from '../data/hero-sweep';

const repo = resolve(__dirname, '../../../..');
const publicDir = resolve(__dirname, '../../public');

describe('the hero sweep says only what the meshes show', () => {
  const project = JSON.parse(
    readFileSync(resolve(repo, `projects/${HERO_SWEEP.slug}/project.json`), 'utf8'),
  );
  const animation = project.animations.find((a: { id: string }) => a.id === HERO_SWEEP.animation);
  const parameter = project.parameters.find((p: { id: string }) => p.id === HERO_SWEEP.param);

  it('names a real animation of a real parameter, with its own label', () => {
    expect(animation).toBeDefined();
    expect(parameter).toBeDefined();
    expect(Object.keys(animation.to_state)).toEqual([HERO_SWEEP.param]);
    expect(HERO_SWEEP.label).toEqual({ es: parameter.label.es, en: parameter.label.en });
  });

  it('lists the value each frame was rendered at (linear over frames, integers rounded)', () => {
    const from = animation.from_state[HERO_SWEEP.param];
    const to = animation.to_state[HERO_SWEEP.param];
    const n = animation.frames;
    const expected = Array.from({ length: n }, (_, i) => Math.round(from + ((to - from) * i) / (n - 1)));
    expect(HERO_SWEEP.values).toEqual(expected);
    expect(HERO_SWEEP.restFrame).toBeGreaterThanOrEqual(0);
    expect(HERO_SWEEP.restFrame).toBeLessThan(n);
  });

  it('has every frame on disk, and no two frames are the same mesh', () => {
    const hashes = HERO_SWEEP.values.map((_, i) => {
      const file = resolve(publicDir, sweepFrameUrl(HERO_SWEEP, i).replace(/^\//, ''));
      expect(existsSync(file)).toBe(true);
      return createHash('sha256').update(readFileSync(file)).digest('hex');
    });
    expect(new Set(hashes).size).toBe(hashes.length);
  });

  it('has its still pictures on disk', () => {
    for (const w of [640, 1280]) {
      expect(existsSync(resolve(publicDir, `hero-sweep-still-${w}w.webp`))).toBe(true);
    }
  });
});
