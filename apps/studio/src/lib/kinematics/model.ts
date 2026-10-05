/**
 * The keystone's compiled kinematic model, `hyperobjects.assembly-kinematics` 1.0.0
 * (hyperobjects-spec `y4d_spec.assembly.posing.kinematic_model`, ASM-1 §9). The viewer
 * poses from it; the keystone resolves the frames. Numbers are JSON numbers in their
 * shortest round-trip form, so `JSON.parse` reads exactly the keystone's doubles.
 */
import type { JointAxis, JointType } from './transforms'

export const KINEMATICS_FORMAT = 'hyperobjects.assembly-kinematics'
/** The major version this reader understands. */
export const KINEMATICS_MAJOR = 1

export type JointRole = 'driven' | 'follower' | 'passive'

export interface ModelJoint {
  id: string
  mate: string
  type: JointType
  axis: JointAxis
  role: JointRole
  unit: 'mm' | 'deg'
  parent: string
  child: string
  limits: [number, number] | null
  home: number | null
  follows: { terms: { joint: string; scale: number }[]; offset: number } | null
}

export interface ModelEdge {
  mate: string
  a: string
  b: string
  theta_deg: number
  h_a: number[]
  h_b: number[]
  joint: string | null
}

export interface EnvelopeBox { shape: 'box'; min: [number, number, number]; max: [number, number, number] }
export interface EnvelopeCylinder {
  shape: 'cylinder'
  axis: JointAxis
  radius: number
  length: number
  base: [number, number, number]
}
export type EnvelopeSolid = EnvelopeBox | EnvelopeCylinder

export type ComponentGeometry =
  | { kind: 'envelope'; solids: EnvelopeSolid[] }
  | {
      kind: 'cartridge'
      commons: string | null
      slug: string | null
      mode: string | null
      instance_id: string | null
      parts: string[]
      parameters: Record<string, unknown>
    }

export interface ModelComponent {
  id: string
  source_type: string
  label: string
  geometry: ComponentGeometry | null
}

export interface MachineBinding { axis: string; joint: string; scale: number; offset: number }

export interface KinematicModel {
  format: typeof KINEMATICS_FORMAT
  format_version: string
  assembly: string | null
  assembly_digest: string | null
  root: string
  components: ModelComponent[]
  edges: ModelEdge[]
  joints: ModelJoint[]
  machine: { kinematics: string | null; axes: MachineBinding[] } | null
}

export class ModelError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ModelError'
  }
}

function isFiniteArray(v: unknown, length: number): v is number[] {
  return Array.isArray(v) && v.length === length && v.every((x) => typeof x === 'number' && Number.isFinite(x))
}

/**
 * Check a parsed document and return it typed. Throws ModelError naming the first
 * problem: a wrong format or major version, a missing root, a malformed edge or joint,
 * an edge or binding that names an unknown component or joint. Never repairs anything.
 */
export function parseKinematicModel(doc: unknown): KinematicModel {
  if (!doc || typeof doc !== 'object') throw new ModelError('the model is not a JSON object')
  const m = doc as Record<string, unknown>
  if (m.format !== KINEMATICS_FORMAT) {
    throw new ModelError(`format is ${JSON.stringify(m.format)}, expected "${KINEMATICS_FORMAT}"`)
  }
  const version = String(m.format_version ?? '')
  if (Number.parseInt(version.split('.')[0], 10) !== KINEMATICS_MAJOR) {
    throw new ModelError(`format_version ${version} is not ${KINEMATICS_MAJOR}.x`)
  }
  if (!Array.isArray(m.components) || !Array.isArray(m.edges) || !Array.isArray(m.joints)) {
    throw new ModelError('components, edges and joints must be arrays')
  }
  const components = m.components as ModelComponent[]
  const ids = new Set(components.map((c) => c.id))
  if (typeof m.root !== 'string' || !ids.has(m.root)) {
    throw new ModelError(`root ${JSON.stringify(m.root)} is not a component`)
  }
  const joints = m.joints as ModelJoint[]
  const jointIds = new Set<string>()
  for (const j of joints) {
    if (jointIds.has(j.id)) throw new ModelError(`joint '${j.id}' is listed twice`)
    jointIds.add(j.id)
    if (j.type !== 'prismatic' && j.type !== 'revolute') {
      throw new ModelError(`joint '${j.id}': unknown type ${JSON.stringify(j.type)}`)
    }
    if (!['x', 'y', 'z'].includes(j.axis)) throw new ModelError(`joint '${j.id}': unknown axis`)
    if (!['driven', 'follower', 'passive'].includes(j.role)) {
      throw new ModelError(`joint '${j.id}': unknown role ${JSON.stringify(j.role)}`)
    }
    if (j.role === 'follower' && !j.follows) throw new ModelError(`joint '${j.id}': a follower with no terms`)
  }
  for (const j of joints) {
    for (const t of j.follows?.terms ?? []) {
      if (!jointIds.has(t.joint)) throw new ModelError(`joint '${j.id}' follows unknown joint '${t.joint}'`)
    }
  }
  for (const e of m.edges as ModelEdge[]) {
    if (!ids.has(e.a) || !ids.has(e.b)) throw new ModelError(`edge '${e.mate}' names an unknown component`)
    if (!isFiniteArray(e.h_a, 16) || !isFiniteArray(e.h_b, 16)) {
      throw new ModelError(`edge '${e.mate}': h_a and h_b must be 16 finite numbers`)
    }
    if (typeof e.theta_deg !== 'number' || !Number.isFinite(e.theta_deg)) {
      throw new ModelError(`edge '${e.mate}': theta_deg must be a finite number`)
    }
    if (e.joint !== null && !jointIds.has(e.joint)) {
      throw new ModelError(`edge '${e.mate}' names unknown joint '${e.joint}'`)
    }
  }
  const machine = m.machine as KinematicModel['machine']
  for (const b of machine?.axes ?? []) {
    if (!jointIds.has(b.joint)) throw new ModelError(`axis '${b.axis}' binds unknown joint '${b.joint}'`)
  }
  return m as unknown as KinematicModel
}
