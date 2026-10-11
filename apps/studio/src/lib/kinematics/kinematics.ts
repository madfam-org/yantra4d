/**
 * Forward kinematics for the viewer: a TypeScript mirror of the keystone's reference
 * (`y4d_spec/assembly/kinematics.py` joint values and axis bindings, and
 * `validate._place`), run on the compiled model the keystone exports. Owner decision D4:
 * the keystone defines kinematics, the viewer computes poses, pravara forwards raw axis
 * values only. Parity with the keystone's golden pose files is a test.
 */
import type { KinematicModel, ModelEdge, ModelJoint } from './model'
import { pySum, radians } from './pyFloat'
import { type Matrix, IDENTITY, flipRz, jointMatrix, matmul, rigidInverse } from './transforms'

export class PoseError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PoseError'
  }
}

/** One step of the placement plan: place `target` from `from` across `edge`. */
interface PlanStep {
  edge: ModelEdge
  joint: ModelJoint | null
  /** true: from side a to side b; false: from side b to side a. */
  forward: boolean
  hA: Matrix
  hB: Matrix
  hBInv: Matrix
  hAInv: Matrix
  m: Matrix
}

/**
 * A model compiled for repeated posing. The placement tree does not depend on joint
 * values (only passive joints are skipped), so the breadth-first walk of `_place` is run
 * once and replayed per pose; the arithmetic per step is unchanged.
 */
export interface CompiledKinematics {
  model: KinematicModel
  joints: ModelJoint[]
  byId: Map<string, ModelJoint>
  followOrder: ModelJoint[]
  plan: PlanStep[]
  /** Components the walk never reaches (a passing assembly has none). */
  unreached: string[]
}

function followOrder(joints: ModelJoint[]): ModelJoint[] {
  const done = new Set(joints.filter((j) => !j.follows || j.follows.terms.length === 0).map((j) => j.id))
  const ids = new Set(joints.map((j) => j.id))
  let pending = joints.filter((j) => j.follows && j.follows.terms.length > 0)
  const order: ModelJoint[] = []
  while (pending.length) {
    const next: ModelJoint[] = []
    let progressed = false
    for (const j of pending) {
      if (j.follows!.terms.every((t) => done.has(t.joint) || !ids.has(t.joint))) {
        order.push(j)
        done.add(j.id)
        progressed = true
      } else {
        next.push(j)
      }
    }
    if (!progressed) throw new PoseError(`followers form a cycle: ${next.map((j) => j.id).join(', ')}`)
    pending = next
  }
  return order
}

export function compileKinematics(model: KinematicModel): CompiledKinematics {
  const byId = new Map(model.joints.map((j) => [j.id, j]))
  const placed = new Set([model.root])
  const queue = [model.root]
  const plan: PlanStep[] = []
  // Pre-built per edge, exactly as `_place` builds them on every visit.
  const frames = model.edges.map((e) => ({
    hA: e.h_a as Matrix,
    hB: e.h_b as Matrix,
    hAInv: rigidInverse(e.h_a),
    hBInv: rigidInverse(e.h_b),
    m: flipRz(radians(e.theta_deg)),
  }))
  for (let head = 0; head < queue.length; head++) {
    const current = queue[head]
    model.edges.forEach((edge, index) => {
      const joint = edge.joint === null ? null : byId.get(edge.joint) ?? null
      if ((current !== edge.a && current !== edge.b) || joint?.role === 'passive') return
      let forward: boolean
      if (current === edge.a && !placed.has(edge.b)) forward = true
      else if (current === edge.b && !placed.has(edge.a)) forward = false
      else return
      const target = forward ? edge.b : edge.a
      placed.add(target)
      queue.push(target)
      plan.push({ edge, joint, forward, ...frames[index] })
    })
  }
  return {
    model,
    joints: model.joints,
    byId,
    followOrder: followOrder(model.joints),
    plan,
    unreached: model.components.map((c) => c.id).filter((id) => !placed.has(id)),
  }
}

function withinLimits(j: ModelJoint, value: number): boolean {
  return j.limits === null || (j.limits[0] <= value && value <= j.limits[1])
}

/**
 * Every driven and follower joint's value (`kinematics.joint_values`): each driven joint
 * at its given value, else its home; followers computed. Throws PoseError on an unknown,
 * follower or passive joint, a non-finite value, or (with `checkLimits`) a driven value
 * outside its limits. Values are never clamped.
 */
export function jointValues(
  k: CompiledKinematics,
  given: Readonly<Record<string, number>> = {},
  { checkLimits = true }: { checkLimits?: boolean } = {},
): Record<string, number> {
  for (const id of Object.keys(given)) {
    const j = k.byId.get(id)
    if (!j) throw new PoseError(`'${id}' is not a joint of this assembly`)
    if (j.role !== 'driven') throw new PoseError(`'${id}' is a ${j.role} joint; only a driven joint is set`)
  }
  const values: Record<string, number> = {}
  for (const j of k.joints) {
    if (j.role !== 'driven') continue
    const raw = Object.prototype.hasOwnProperty.call(given, j.id) ? given[j.id] : j.home
    if (typeof raw !== 'number' || !Number.isFinite(raw)) {
      throw new PoseError(`joint '${j.id}': ${String(raw)} is not a finite number`)
    }
    if (checkLimits && !withinLimits(j, raw)) {
      throw new PoseError(
        `joint '${j.id}' = ${raw} ${j.unit} is outside its limits [${j.limits![0]}, ${j.limits![1]}] (never clamped)`,
      )
    }
    values[j.id] = raw
  }
  for (const j of k.followOrder) {
    const f = j.follows!
    values[j.id] = f.offset + pySum(f.terms.map((t) => t.scale * values[t.joint]))
  }
  return values
}

/**
 * Driven-joint values from machine axis values through the model's `machine.axes`
 * (joint = scale · axis + offset; `kinematics.axis_joint_values`). An axis the machine
 * block does not bind throws; an axis not reported leaves its joint at home.
 */
export function axisJointValues(
  model: KinematicModel,
  axes: Readonly<Record<string, number>>,
): Record<string, number> {
  const bindings = new Map((model.machine?.axes ?? []).map((b) => [b.axis, b]))
  const out: Record<string, number> = {}
  for (const [axis, value] of Object.entries(axes)) {
    const b = bindings.get(axis)
    if (!b) {
      throw new PoseError(`axis '${axis}' is not bound by the machine block (bound: ${[...bindings.keys()].sort().join(', ') || 'none'})`)
    }
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new PoseError(`axis '${axis}': ${String(value)} is not a finite number`)
    }
    out[b.joint] = b.scale * value + b.offset
  }
  return out
}

/** Every component's world transform at `values` (`KinematicModel.place`). */
export function place(k: CompiledKinematics, values: Readonly<Record<string, number>>): Map<string, Matrix> {
  const placements = new Map<string, Matrix>([[k.model.root, IDENTITY]])
  for (const s of k.plan) {
    const j = s.joint === null ? null : jointMatrix(s.joint.type, s.joint.axis, values[s.joint.id] ?? 0)
    if (s.forward) {
      const tA = placements.get(s.edge.a)!
      placements.set(s.edge.b, j === null ? matmul(tA, s.hA, s.m, s.hBInv) : matmul(tA, s.hA, j, s.m, s.hBInv))
    } else {
      const tB = placements.get(s.edge.b)!
      placements.set(
        s.edge.a,
        j === null ? matmul(tB, s.hB, s.m, s.hAInv) : matmul(tB, s.hB, s.m, rigidInverse(j), s.hAInv),
      )
    }
  }
  return placements
}

/** Pose from machine axis values: bindings, then joint values, then placement. */
export function poseFromAxes(
  k: CompiledKinematics,
  axes: Readonly<Record<string, number>>,
): { joints: Record<string, number>; placements: Map<string, Matrix> } {
  const joints = jointValues(k, axisJointValues(k.model, axes))
  return { joints, placements: place(k, joints) }
}

/**
 * The canonical fixed format of the golden pose files: `toFixed(6)` (the exact binary
 * value, ties away from zero), with "-0.000000" written "0.000000".
 */
export function formatNumber(value: number): string {
  const text = value.toFixed(6)
  return text === '-0.000000' ? '0.000000' : text
}
