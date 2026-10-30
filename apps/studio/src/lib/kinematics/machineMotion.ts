/**
 * The pravara motion stream, `pravara.machine-motion/1` (lane W4-P7MES, fixed
 * 2026-10-05): `GET /v1/machines/{id}/motion` on pravara-api, text/event-stream.
 * pravara forwards raw printer values (Klipper `motion_report.live_position`) with no
 * rounding and no kinematics; this module only types and checks them.
 */

export const MOTION_SCHEMA = 'pravara.machine-motion/1'

export interface MotionSourceRef {
  edge_node_id: string
  device_id: string
  bdseq: number
  seq: number
}

/** A motion event's data: the FULL merged state, not a diff. */
export interface MachineMotion {
  /** mm in printer coordinates; null until that axis has been reported. */
  position: { x: number | null; y: number | null; z: number | null; e: number | null }
  /** mm/s, live_velocity (≥ 0). */
  velocity: number | null
  /** toolhead.homed_axes verbatim ("", "xy", "xyz"). */
  homed: string | null
  /** true only when the edge fell back to toolhead.position (no motion_report). */
  commanded: boolean
  /** Epoch ms when the edge received the printer update (edge clock). */
  sampled_at_ms: number | null
  /** Epoch ms on the worker clock. */
  host_received_at_ms: number | null
  source: MotionSourceRef | null
}

export interface MachineStatus {
  online: boolean
  state: 'idle' | 'printing' | 'paused' | 'error' | 'offline' | null
  progress: number | null
  /** °C, rounded to 0.5 at the edge. */
  hotend_c: number | null
  bed_c: number | null
  job_id: string | null
  job_status: 'queued' | 'printing' | 'complete' | 'failed' | 'cancelled' | null
  sampled_at_ms: number | null
  host_received_at_ms: number | null
  source: MotionSourceRef | null
}

interface Envelope {
  schema: typeof MOTION_SCHEMA
  machine_id: string
  /** Per connection, from 1, gap-free, equal to the SSE id. */
  seq: number
  /** Epoch ms on the api clock. */
  sent_at_ms: number
  /** Motion events skipped for this slow client (each motion event carries full state). */
  dropped: number
}

export type MotionEvent =
  | ({ type: 'snapshot' } & Envelope & { motion: MachineMotion | null; status: MachineStatus })
  | ({ type: 'motion' } & Envelope & MachineMotion)
  | ({ type: 'status' } & Envelope & MachineStatus)

export const MOTION_EVENT_TYPES = ['snapshot', 'motion', 'status'] as const

export class MotionStreamError extends Error {
  constructor(message: string, readonly code?: string, readonly httpStatus?: number) {
    super(message)
    this.name = 'MotionStreamError'
  }
}

function num(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

function checkMotion(m: unknown, where: string): MachineMotion {
  if (!m || typeof m !== 'object') throw new MotionStreamError(`${where}: the motion object is missing`)
  const o = m as Record<string, unknown>
  const p = o.position as Record<string, unknown> | undefined
  if (!p || typeof p !== 'object') throw new MotionStreamError(`${where}: position is missing`)
  for (const axis of ['x', 'y', 'z', 'e']) {
    if (p[axis] !== null && p[axis] !== undefined && !num(p[axis])) {
      throw new MotionStreamError(`${where}: position.${axis} is not a finite number or null`)
    }
  }
  return o as unknown as MachineMotion
}

/**
 * Parse one SSE event (its `event` field and its one-line JSON `data`) into a typed
 * MotionEvent. Throws MotionStreamError on a wrong schema id, a missing seq, a seq that
 * does not equal the SSE id, or a malformed motion object. Never guesses.
 */
export function parseMotionEvent(type: string, data: string, sseId?: string): MotionEvent {
  if (!(MOTION_EVENT_TYPES as readonly string[]).includes(type)) {
    throw new MotionStreamError(`unknown event type ${JSON.stringify(type)}`)
  }
  let doc: Record<string, unknown>
  try {
    doc = JSON.parse(data)
  } catch {
    throw new MotionStreamError(`${type}: data is not JSON`)
  }
  if (doc.schema !== MOTION_SCHEMA) {
    throw new MotionStreamError(`${type}: schema ${JSON.stringify(doc.schema)} is not ${MOTION_SCHEMA}`)
  }
  if (!Number.isInteger(doc.seq) || (doc.seq as number) < 1) throw new MotionStreamError(`${type}: seq is not a positive integer`)
  if (sseId !== undefined && sseId !== '' && String(doc.seq) !== sseId) {
    throw new MotionStreamError(`${type}: seq ${String(doc.seq)} differs from the SSE id ${sseId}`)
  }
  if (type === 'motion') checkMotion(doc, 'motion')
  if (type === 'snapshot' && doc.motion !== null) checkMotion(doc.motion, 'snapshot')
  return { type, ...doc } as MotionEvent
}

/** The axis values a motion object gives the bindings: reported axes only (x, y, z). */
export function motionAxes(m: MachineMotion): Record<string, number> {
  const out: Record<string, number> = {}
  for (const axis of ['x', 'y', 'z'] as const) {
    const v = m.position[axis]
    if (v !== null && v !== undefined) out[axis] = v
  }
  return out
}
