import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { HERO_SWEEP, sweepFrameUrl } from '../data/hero-sweep';

const repo = resolve(__dirname, '../../../..');
const publicDir = resolve(__dirname, '../../public');

describe('the hero sweep says only what the meshes show', () => {
  // The landing CI has no submodules, so the sweep definition is read from a frozen copy.
  const fixture = JSON.parse(
    readFileSync(resolve(__dirname, 'fixtures/scara-reach-sweep.json'), 'utf8'),
  );
  const project = { parameters: fixture.parameters, animations: [fixture.animation] };
  const animation = fixture.animation;
  const commonsFile = resolve(repo, `projects/${HERO_SWEEP.slug}/project.json`);

  it.skipIf(!existsSync(commonsFile))('the frozen copy still matches the Commons', () => {
    const live = JSON.parse(readFileSync(commonsFile, 'utf8'));
    expect(fixture.slug).toBe(HERO_SWEEP.slug);
    expect(live.animations.find((a: { id: string }) => a.id === HERO_SWEEP.animation)).toEqual(
      fixture.animation,
    );
    for (const p of fixture.parameters) {
      const l = live.parameters.find((x: { id: string }) => x.id === p.id);
      for (const k of Object.keys(p)) expect(l[k]).toEqual(p[k]);
    }
  });

  it('names a real sweep of real parameters, and its label names the readout', () => {
    expect(animation).toBeDefined();
    expect(Object.keys(animation.to_state).sort()).toEqual([...HERO_SWEEP.params].sort());
    for (const id of HERO_SWEEP.params) {
      expect(project.parameters.find((p: { id: string }) => p.id === id)).toBeDefined();
    }
    expect(animation.label.es.startsWith(HERO_SWEEP.label.es)).toBe(true);
    expect(animation.label.en.startsWith(HERO_SWEEP.label.en)).toBe(true);
    expect(animation.label.en).toContain(HERO_SWEEP.unit);
  });

  it('lists the value each frame was rendered at (linear, rounded, snapped to the slider grid)', () => {
    // Python's round() rounds half to even; mirror it so a half-way frame matches the pipeline.
    const pyRound = (v: number) => {
      const f = Math.floor(v);
      const d = v - f;
      if (Math.abs(d - 0.5) < 1e-9) return f % 2 === 0 ? f : f + 1;
      return Math.round(v);
    };
    const n = animation.frames;
    const expected = Array.from({ length: n }, (_, i) => {
      const t = i / (n - 1);
      return HERO_SWEEP.params.reduce((sum, id) => {
        const def = project.parameters.find((p: { id: string }) => p.id === id);
        const from = animation.from_state[id];
        const to = animation.to_state[id];
        let v = from + (to - from) * t;
        if (Number.isInteger(from) && Number.isInteger(to)) v = pyRound(v);
        let snapped = def.min + pyRound((v - def.min) / def.step) * def.step;
        snapped = Math.max(def.min, Math.min(def.max, snapped));
        return sum + snapped;
      }, 0);
    });
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
    for (const w of [640, 672]) {
      expect(existsSync(resolve(publicDir, `hero-sweep-still-${w}w.webp`))).toBe(true);
    }
  });
});
