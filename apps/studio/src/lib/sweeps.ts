/**
 * Parameter sweeps a cartridge declares in its manifest (`animations[]`).
 *
 * A sweep is a path from one parameter state to another, sampled into frames
 * the server renders (`POST /api/projects/<slug>/animations/<id>/render`). The
 * list itself is part of the manifest every visitor already has, so the Studio
 * reads it from there: everyone can see which sweeps a cartridge declares, and
 * only playback (rendering the frames) is gated on the `animation` feature.
 */

export interface SweepDefinition {
  id: string
  label?: string | Record<string, string>
  description?: string | Record<string, string>
  /** Frames the server renders; the API defaults a missing value to 5. */
  frames: number
  /** One pass through every frame, in milliseconds. */
  duration_ms: number
  easing?: string
  /** The mode whose geometry the frames show; the API defaults to the first mode. */
  mode?: string
}

/** The API's own default (`anim.get("frames", 5)` in routes/projects/animations.py). */
export const DEFAULT_SWEEP_FRAMES = 5
/** What the player used before a manifest stated a duration. */
export const DEFAULT_SWEEP_DURATION_MS = 2000
/** Never flip frames faster than this, whatever a manifest asks for. */
export const MIN_SWEEP_FRAME_MS = 80

function positiveInteger(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null
}

function positiveNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null
}

/** The sweeps a manifest declares, normalised; entries without an id are dropped. */
export function manifestSweeps(manifest: unknown): SweepDefinition[] {
  const list = (manifest as { animations?: unknown } | null | undefined)?.animations
  if (!Array.isArray(list)) return []
  const sweeps: SweepDefinition[] = []
  for (const entry of list) {
    if (!entry || typeof entry !== 'object') continue
    const raw = entry as Record<string, unknown>
    if (typeof raw.id !== 'string' || raw.id === '') continue
    sweeps.push({
      ...(raw as unknown as SweepDefinition),
      frames: positiveInteger(raw.frames) ?? DEFAULT_SWEEP_FRAMES,
      duration_ms: positiveNumber(raw.duration_ms) ?? DEFAULT_SWEEP_DURATION_MS,
      mode: typeof raw.mode === 'string' && raw.mode ? raw.mode : undefined,
    })
  }
  return sweeps
}

/** Milliseconds each frame is held so one pass lasts the sweep's duration. */
export function sweepFrameInterval(sweep: Pick<SweepDefinition, 'duration_ms'> | null | undefined, frameCount: number): number {
  const duration = positiveNumber(sweep?.duration_ms) ?? DEFAULT_SWEEP_DURATION_MS
  const count = frameCount > 0 ? frameCount : 1
  return Math.max(MIN_SWEEP_FRAME_MS, duration / count)
}

/** One pass in seconds, for display ("2.5 s"). */
export function sweepSeconds(sweep: Pick<SweepDefinition, 'duration_ms'>): string {
  const seconds = sweep.duration_ms / 1000
  return Number.isInteger(seconds) ? String(seconds) : seconds.toFixed(1)
}
