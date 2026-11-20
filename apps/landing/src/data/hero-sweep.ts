/**
 * The hero's live parameter sweep: one real Commons cartridge, one real parameter, and the frames
 * the models pipeline already rendered for it (`scripts/dev/render_commons_models.py`).
 *
 * The pipeline steps `t` linearly over the frames and rounds integer parameters, so frame `i` of a
 * 7-frame sweep from 6 to 48 is exactly `round(6 + 42 * i / 6)`. `hero-sweep.test.ts` re-derives
 * these values from the cartridge's own `project.json` and checks every frame file exists and is
 * distinct, so the slider can never claim a value the mesh does not show.
 */

export interface HeroSweep {
  slug: string;
  animation: string;
  /** Parameter id in the cartridge. */
  param: string;
  label: { es: string; en: string };
  /** The cartridge's display name. */
  name: string;
  /** The parameter's value in each rendered frame, in frame order. */
  values: number[];
  /** Frame index shown first and in the still image. */
  restFrame: number;
}

export const HERO_SWEEP: HeroSweep = {
  slug: 'planetary-gearset',
  animation: 'ratio-sweep',
  param: 'sun_teeth',
  label: { es: 'Dientes del Sol', en: 'Sun Teeth' },
  name: 'Planetary Gearset',
  values: [6, 13, 20, 27, 34, 41, 48],
  restFrame: 3,
};

export function sweepFrameUrl(sweep: HeroSweep, index: number): string {
  return `/models/${sweep.slug}.${sweep.animation}.${index}.glb`;
}
