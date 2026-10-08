/**
 * Render budget: a self-contained adaptive-quality controller for a three.js
 * WebGLRenderer. It has no React, store or app imports, so any three.js page
 * can use it; the host feeds it frames and applies the scale it reports.
 *
 * - Runtime GPU benchmark: every frame is timed on the GPU with
 *   EXT_disjoint_timer_query_webgl2, and when a scene of a new size appears
 *   the view is rendered offscreen at two scales to fit t(s) = a + b·s².
 * - Scale policy: Sharp, Balanced and Battery are fixed scales. Auto starts at
 *   the sharpest scale whose predicted GPU time fits 80% of the frame budget,
 *   steps down when the p90 of a 30-frame window is over budget and steps up
 *   after three windows of headroom, each with a cooldown.
 * - Readings for a diagnostics UI: stats().
 *
 *   const budget = createRenderBudget(renderer, {
 *     onScale: (scale) => renderer.setPixelRatio(Math.min(devicePixelRatio, MAX_DPR) * scale),
 *     probeTarget: () => ({ scene, camera }),
 *   })
 *   budget.onFrame(() => renderer.render(scene, camera))   // or beginFrame()/endFrame()
 */
import { Vector2, WebGLRenderTarget, type Camera, type Object3D, type WebGLRenderer } from 'three'

export type QualityMode = 'auto' | 'sharp' | 'balanced' | 'battery'
export const QUALITY_MODES: readonly QualityMode[] = ['auto', 'sharp', 'balanced', 'battery']

/** Render scales Auto may choose, sharpest first (multiplies the device pixel ratio). */
export const SCALE_LADDER: readonly number[] = [1, 0.85, 0.7, 0.55]
const FIXED_SCALE: Record<Exclude<QualityMode, 'auto'>, number> = { sharp: 1, balanced: 0.75, battery: 0.5 }

/** Pixel-ratio ceiling: beyond 2 the extra pixels cost GPU time without a visible gain. */
export const MAX_DPR = 2
export const FRAME_BUDGET_MS = 1000 / 60
/** Auto keeps the GPU at or below this fraction of the frame budget. */
export const BUDGET_FRACTION = 0.8

/** Nearest-rank percentile (p in 0..1); null for an empty sample. */
export function percentile(values: readonly number[], p: number): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const rank = Math.ceil(p * sorted.length) - 1
  return sorted[Math.min(sorted.length - 1, Math.max(0, rank))]
}

/** The render scale a mode asks for, given Auto's current choice. */
export function targetScale(mode: QualityMode, autoScale: number): number {
  return mode === 'auto' ? autoScale : FIXED_SCALE[mode]
}

/** Sharpest ladder scale whose predicted GPU time (t = a + b·s²) fits the budget. */
export function scaleFromProbe(
  fullMs: number,
  reducedMs: number,
  reducedScale: number,
  budgetMs: number = FRAME_BUDGET_MS * BUDGET_FRACTION,
): number {
  if (!Number.isFinite(fullMs) || !Number.isFinite(reducedMs) || fullMs <= budgetMs) return 1
  const r2 = reducedScale * reducedScale
  const perPixel = r2 < 1 ? Math.max(0, (fullMs - reducedMs) / (1 - r2)) : 0
  const fixed = Math.max(0, fullMs - perPixel)
  for (const scale of SCALE_LADDER) {
    if (fixed + perPixel * scale * scale <= budgetMs) return scale
  }
  return SCALE_LADDER[SCALE_LADDER.length - 1]
}

/** Auto mode's closed loop over per-frame GPU times. */
export class AdaptiveScaler {
  static readonly WINDOW = 30
  static readonly DOWN_COOLDOWN_MS = 1000
  static readonly UP_COOLDOWN_MS = 3000
  /** p90 below this fraction of the budget counts as headroom. */
  static readonly HEADROOM = 0.5
  /** Consecutive headroom windows needed before stepping up. */
  static readonly UP_WINDOWS = 3

  scale: number
  private readonly budgetMs: number
  private samples: number[] = []
  private lastChange = Number.NEGATIVE_INFINITY
  private headroomWindows = 0

  constructor(scale = 1, budgetMs: number = FRAME_BUDGET_MS * BUDGET_FRACTION) {
    this.scale = scale
    this.budgetMs = budgetMs
  }

  reset(scale: number): void {
    this.scale = scale
    this.samples = []
    this.headroomWindows = 0
    this.lastChange = Number.NEGATIVE_INFINITY
  }

  /** Feed one frame's GPU time (ms); returns the new scale when it changes. */
  push(gpuMs: number, now: number): number | null {
    this.samples.push(gpuMs)
    if (this.samples.length < AdaptiveScaler.WINDOW) return null
    const p90 = percentile(this.samples, 0.9) ?? 0
    this.samples = []
    const ladder = SCALE_LADDER
    const index = Math.max(0, ladder.findIndex((s) => s <= this.scale + 1e-6))
    if (p90 > this.budgetMs) {
      this.headroomWindows = 0
      if (index < ladder.length - 1 && now - this.lastChange >= AdaptiveScaler.DOWN_COOLDOWN_MS) {
        return this.change(ladder[index + 1], now)
      }
      return null
    }
    if (p90 < this.budgetMs * AdaptiveScaler.HEADROOM) {
      this.headroomWindows += 1
      if (this.headroomWindows >= AdaptiveScaler.UP_WINDOWS && index > 0
        && now - this.lastChange >= AdaptiveScaler.UP_COOLDOWN_MS) {
        this.headroomWindows = 0
        return this.change(ladder[index - 1], now)
      }
    } else {
      this.headroomWindows = 0
    }
    return null
  }

  private change(scale: number, now: number): number {
    this.scale = scale
    this.lastChange = now
    return scale
  }
}

/** Short browser label, e.g. "Chrome 152". */
export function describeBrowser(userAgent: string): string {
  const rules: [RegExp, string][] = [
    [/Edg\/(\d+)/, 'Edge'],
    [/Firefox\/(\d+)/, 'Firefox'],
    [/Chrome\/(\d+)/, 'Chrome'],
    [/Version\/(\d+)[^ ]* (?:Mobile\/\S+ )?Safari/, 'Safari'],
  ]
  for (const [pattern, name] of rules) {
    const match = pattern.exec(userAgent)
    if (match) return `${name} ${match[1]}`
  }
  return 'Unknown'
}

type GL = WebGLRenderingContext | WebGL2RenderingContext

export interface GpuTimer {
  available: boolean
  begin: () => void
  end: (valid: boolean, tag?: string) => void
  /** Finished queries, oldest first (disjoint or invalid ones dropped). */
  poll: () => { ms: number; tag: string }[]
  dispose: () => void
}

export function createGpuTimer(context: GL): GpuTimer {
  const gl = context as WebGL2RenderingContext
  const isWebGL2 = typeof WebGL2RenderingContext !== 'undefined' && context instanceof WebGL2RenderingContext
  const ext = isWebGL2 ? gl.getExtension('EXT_disjoint_timer_query_webgl2') : null
  let active: WebGLQuery | null = null
  const pending: { query: WebGLQuery; valid: boolean; tag: string }[] = []
  return {
    available: !!ext,
    begin() {
      if (!ext || active || pending.length > 8) return
      active = gl.createQuery()
      if (active) gl.beginQuery(ext.TIME_ELAPSED_EXT, active)
    },
    end(valid, tag = 'frame') {
      if (!ext || !active) return
      gl.endQuery(ext.TIME_ELAPSED_EXT)
      pending.push({ query: active, valid, tag })
      active = null
    },
    poll() {
      const out: { ms: number; tag: string }[] = []
      if (!ext) return out
      while (pending.length && gl.getQueryParameter(pending[0].query, gl.QUERY_RESULT_AVAILABLE)) {
        const { query, valid, tag } = pending.shift()!
        const disjoint = gl.getParameter(ext.GPU_DISJOINT_EXT)
        const ns = gl.getQueryParameter(query, gl.QUERY_RESULT) as number
        if (valid && !disjoint) out.push({ ms: ns / 1e6, tag })
        gl.deleteQuery(query)
      }
      return out
    },
    dispose() {
      if (active && ext) gl.endQuery(ext.TIME_ELAPSED_EXT)
      for (const { query } of pending) gl.deleteQuery(query)
      if (active) gl.deleteQuery(active)
      pending.length = 0
      active = null
    },
  }
}

export function readGpuName(context: GL): string | null {
  try {
    const info = context.getExtension('WEBGL_debug_renderer_info')
    const name = info ? context.getParameter(info.UNMASKED_RENDERER_WEBGL) : context.getParameter(context.RENDERER)
    return typeof name === 'string' ? name.replace(/^ANGLE \((.*)\)$/, '$1') : null
  } catch {
    return null
  }
}

export interface RenderBudgetStats {
  gpu: string | null
  browser: string
  timerQuery: boolean
  scale: number
  gpuMsP50: number | null
  gpuMsP90: number | null
  /** Frames rendered in the last second; 0 while the scene is idle. */
  fps: number
  drawCalls: number
  triangles: number
}

export interface RenderBudgetOptions {
  mode?: QualityMode
  /** Called when the render scale changes; the host applies it (pixel ratio = base DPR × scale). */
  onScale?: (scale: number) => void
  /** Scene and camera to probe offscreen when a scene of a new size appears (Auto only). */
  probeTarget?: () => { scene: Object3D; camera: Camera } | null
  budgetMs?: number
  probeScale?: number
  probeFrames?: number
}

export interface RenderBudget {
  readonly scale: number
  /** Call right before the frame's render calls. */
  beginFrame: () => void
  /** Call right after them; ticks without a render are ignored. */
  endFrame: () => void
  onFrame: (render: () => void) => void
  setMode: (mode: QualityMode) => void
  probe: (scene: Object3D, camera: Camera) => void
  stats: () => RenderBudgetStats
  dispose: () => void
}

export function createRenderBudget(renderer: WebGLRenderer, options: RenderBudgetOptions = {}): RenderBudget {
  const context = renderer.getContext()
  const timer = createGpuTimer(context)
  const budgetMs = options.budgetMs ?? FRAME_BUDGET_MS * BUDGET_FRACTION
  const probeScale = options.probeScale ?? 0.6
  const probeFrames = options.probeFrames ?? 4
  const scaler = new AdaptiveScaler(1, budgetMs)
  const gpu = readGpuName(context)
  const browser = typeof navigator === 'undefined' ? 'Unknown' : describeBrowser(navigator.userAgent)
  const samples: number[] = []
  const frameTimes: number[] = []
  let mode: QualityMode = options.mode ?? 'auto'
  let autoScale = 1
  let scale = targetScale(mode, autoScale)
  let drawCalls = 0
  let triangles = 0
  let frameAtBegin = -1
  let probedTriangles = 0
  let probing = false
  let disposed = false

  const info = renderer.info
  info.autoReset = false

  const apply = () => {
    const next = targetScale(mode, autoScale)
    if (next !== scale) {
      scale = next
      options.onScale?.(next)
    }
  }

  const probe = (scene: Object3D, camera: Camera) => {
    if (!timer.available || probing || disposed) return
    probing = true
    const size = renderer.getDrawingBufferSize(new Vector2())
    const samplesAttr = context.getContextAttributes()?.antialias ? 4 : 0
    const measure = (s: number) => {
      const target = new WebGLRenderTarget(Math.max(1, Math.round(size.x * s)), Math.max(1, Math.round(size.y * s)), { samples: samplesAttr })
      const previous = renderer.getRenderTarget()
      renderer.setRenderTarget(target)
      timer.begin()
      for (let i = 0; i < probeFrames; i++) renderer.render(scene, camera)
      timer.end(true, 'probe')
      renderer.setRenderTarget(previous)
      return target
    }
    const targets = [measure(1), measure(probeScale)]
    const results: number[] = []
    const collect = (attempt: number) => {
      if (disposed) return
      for (const r of timer.poll()) if (r.tag === 'probe') results.push(r.ms)
      if (results.length < 2 && attempt <= 60) {
        requestAnimationFrame(() => collect(attempt + 1))
        return
      }
      targets.forEach((t) => t.dispose())
      probing = false
      if (results.length >= 2) {
        autoScale = scaleFromProbe(results[0] / probeFrames, results[1] / probeFrames, probeScale, budgetMs)
        scaler.reset(autoScale)
        apply()
      }
    }
    requestAnimationFrame(() => collect(0))
  }

  const beginFrame = () => {
    if (probing || disposed) return
    for (const { ms } of timer.poll()) {
      samples.push(ms)
      if (samples.length > 120) samples.shift()
      if (mode === 'auto') {
        const next = scaler.push(ms, performance.now())
        if (next !== null) { autoScale = next; apply() }
      }
    }
    info.reset()
    frameAtBegin = info.render.frame
    timer.begin()
  }

  const endFrame = () => {
    if (frameAtBegin < 0) return
    const rendered = info.render.frame !== frameAtBegin
    timer.end(rendered)
    frameAtBegin = -1
    if (!rendered) return
    drawCalls = info.render.calls
    triangles = info.render.triangles
    const now = performance.now()
    frameTimes.push(now)
    while (frameTimes[0] < now - 1000) frameTimes.shift()
    if (mode === 'auto' && options.probeTarget && triangles > 1000
      && Math.abs(triangles - probedTriangles) > probedTriangles * 0.25) {
      probedTriangles = triangles
      setTimeout(() => {
        const target = options.probeTarget?.()
        if (target) probe(target.scene, target.camera)
      }, 0)
    }
  }

  return {
    get scale() { return scale },
    beginFrame,
    endFrame,
    onFrame(render) {
      beginFrame()
      try { render() } finally { endFrame() }
    },
    setMode(next) {
      if (next === mode) return
      mode = next
      scaler.reset(autoScale)
      apply()
    },
    probe,
    stats() {
      const now = performance.now()
      while (frameTimes.length && frameTimes[0] < now - 1000) frameTimes.shift()
      return {
        gpu, browser, timerQuery: timer.available, scale,
        gpuMsP50: percentile(samples, 0.5), gpuMsP90: percentile(samples, 0.9),
        fps: frameTimes.length, drawCalls, triangles,
      }
    },
    dispose() {
      disposed = true
      timer.dispose()
      info.autoReset = true
    },
  }
}
