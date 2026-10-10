/**
 * Where a live twin's pose comes from (Phase 7c/7d). A source emits machine axis values
 * in PRINTER coordinates (Klipper X/Y/Z in mm) or raw joint values; the viewer applies
 * the assembly's §9 `machine` bindings itself (pravara never maps axes, owner rule D4).
 */
import type { MachineMotion, MachineStatus } from './machineMotion'

/** One pose update. Exactly one of `axes` or `joints` drives the pose. */
export interface PoseSample {
  /** Printer axis values in mm, keyed by the machine block's axis ids (x, y, z). */
  axes?: Partial<Record<string, number>>
  /** Raw driven-joint values (mm or degrees), bypassing the bindings. */
  joints?: Record<string, number>
  /** The stream's motion object when the sample came from pravara. */
  motion?: MachineMotion
  /** Epoch ms when the sample was produced (edge clock for a streamed sample). */
  sampledAtMs?: number
  /** Stream sequence number (pravara `seq`), when there is one. */
  seq?: number
}

export type PoseSourceState = 'idle' | 'connecting' | 'live' | 'error' | 'closed'

export interface PoseSourceEvents {
  pose?: (sample: PoseSample) => void
  status?: (status: MachineStatus) => void
  state?: (state: PoseSourceState, detail?: string) => void
}

/** A stream of poses. `subscribe` returns its unsubscribe function. */
export interface PoseSource {
  readonly kind: string
  subscribe(events: PoseSourceEvents): () => void
  close(): void
}

/** A source with listeners, for the concrete sources below. */
export abstract class BasePoseSource implements PoseSource {
  abstract readonly kind: string
  protected listeners = new Set<PoseSourceEvents>()
  protected lastState: PoseSourceState = 'idle'

  subscribe(events: PoseSourceEvents): () => void {
    this.listeners.add(events)
    events.state?.(this.lastState)
    return () => {
      this.listeners.delete(events)
    }
  }

  protected emitPose(sample: PoseSample): void {
    for (const l of this.listeners) l.pose?.(sample)
  }

  protected emitStatus(status: MachineStatus): void {
    for (const l of this.listeners) l.status?.(status)
  }

  protected emitState(state: PoseSourceState, detail?: string): void {
    this.lastState = state
    for (const l of this.listeners) l.state?.(state, detail)
  }

  close(): void {
    this.emitState('closed')
    this.listeners.clear()
  }
}

/**
 * A dev panel's source: set printer axes (within the bound joints' limits, which are
 * Klipper's soft ranges for A) or raw joint values by hand.
 */
export class ManualPoseSource extends BasePoseSource {
  readonly kind = 'manual'
  private axes: Record<string, number> = {}

  constructor(initialAxes: Record<string, number> = {}) {
    super()
    this.axes = { ...initialAxes }
    this.lastState = 'live'
  }

  current(): Record<string, number> {
    return { ...this.axes }
  }

  setAxes(axes: Record<string, number>): void {
    this.axes = { ...this.axes, ...axes }
    this.emitPose({ axes: { ...this.axes }, sampledAtMs: Date.now() })
  }

  setJoints(joints: Record<string, number>): void {
    this.emitPose({ joints: { ...joints }, sampledAtMs: Date.now() })
  }
}
