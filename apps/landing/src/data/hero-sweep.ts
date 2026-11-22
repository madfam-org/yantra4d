/**
 * The hero's live parameter sweep: one real Commons cartridge, one real sweep, and the frames the
 * models pipeline already rendered for it (`scripts/dev/render_commons_models.py`).
 *
 * The SCARA arm's `reach-sweep` moves two parameters at once, the shoulder and elbow link lengths,
 * and its own label names their sum: the arm's reach. The pipeline steps `t` linearly over the
 * frames, rounds integers and snaps each value onto its slider's grid, so frame `i` shows exactly
 * the reach listed here. `hero-sweep.test.ts` re-derives these values from the cartridge's own
 * `project.json` and checks every frame file exists and is distinct, so the readout can never
 * claim a value the mesh does not show.
 */

export interface HeroSweep {
  slug: string;
  animation: string;
  /** The parameters the sweep moves; the readout shows their sum. */
  params: string[];
  /** Readout label, from the sweep's own label. */
  label: { es: string; en: string };
  unit: string;
  /** The readout's value in each rendered frame, in frame order. */
  values: number[];
  /** Frame shown first and in the still image. */
  restFrame: number;
  /**
   * Version of the rendered pictures in `public/hero-sweep/`. They are served with a year-long
   * immutable cache, so bump this whenever they are rendered again.
   */
  pictures: number;
}

export const HERO_SWEEP: HeroSweep = {
  slug: 'scara-robotics',
  animation: 'reach-sweep',
  params: ['link1_length', 'link2_length'],
  label: { es: 'Alcance', en: 'Reach' },
  unit: 'mm',
  values: [180, 270, 355, 445, 535, 625, 710, 800],
  restFrame: 3,
  pictures: 1,
};

/** The rendered picture of frame `index`, `width` pixels wide. */
export function sweepPictureUrl(sweep: HeroSweep, index: number, width: 672 | 1344): string {
  return `/hero-sweep/frame-${index}-${width}w.webp?v=${sweep.pictures}`;
}

export function sweepFrameUrl(sweep: HeroSweep, index: number): string {
  return `/models/${sweep.slug}.${sweep.animation}.${index}.glb`;
}
