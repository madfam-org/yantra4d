/**
 * Rigid 4×4 transforms, row-major, acting on column vectors (`p_world = M · p_local`):
 * a TypeScript mirror of the keystone's `y4d_spec/assembly/transforms.py` and
 * `kinematics.joint_matrix`, operation for operation, so that results are bit-identical
 * where the host's `Math.cos`/`Math.sin` agree with the C library's (a last-ulp
 * disagreement is what the golden files' `tie_guard` absorbs).
 */
import { pySum, radians } from './pyFloat'

/** 16 numbers, row-major: `m[4 * row + col]`. */
export type Matrix = readonly number[]

export const IDENTITY: Matrix = Object.freeze([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])

/** A turn of π about the x-axis: n → −n, y → −y. */
export const FLIP: Matrix = Object.freeze([1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1])

export const JOINT_AXES = ['x', 'y', 'z'] as const
export type JointAxis = (typeof JOINT_AXES)[number]
export type JointType = 'prismatic' | 'revolute'

function product(a: Matrix, b: Matrix): number[] {
  const out = new Array<number>(16)
  const terms = [0, 0, 0, 0]
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      for (let k = 0; k < 4; k++) terms[k] = a[4 * i + k] * b[4 * k + j]
      out[4 * i + j] = pySum(terms)
    }
  }
  return out
}

/** The product of one or more matrices, left to right (`transforms.matmul`). */
export function matmul(...matrices: Matrix[]): Matrix {
  if (matrices.length === 0) throw new Error('matmul needs at least one matrix')
  let out: Matrix = matrices[0]
  for (let n = 1; n < matrices.length; n++) out = product(out, matrices[n])
  return out
}

/** The inverse of a rigid transform: (R, t)⁻¹ = (Rᵀ, −Rᵀ t) (`transforms.rigid_inverse`). */
export function rigidInverse(m: Matrix): Matrix {
  const rt = [
    [m[0], m[4], m[8]],
    [m[1], m[5], m[9]],
    [m[2], m[6], m[10]],
  ]
  const t = [m[3], m[7], m[11]]
  const inv = rt.map((row) => -pySum([row[0] * t[0], row[1] * t[1], row[2] * t[2]]))
  return [
    rt[0][0], rt[0][1], rt[0][2], inv[0],
    rt[1][0], rt[1][1], rt[1][2], inv[1],
    rt[2][0], rt[2][1], rt[2][2], inv[2],
    0, 0, 0, 1,
  ]
}

/** Rz(θ), θ in radians; exact zeros at the quarter turns (`transforms.rotation_z`). */
export function rotationZ(thetaRad: number): Matrix {
  let c = Math.cos(thetaRad)
  let s = Math.sin(thetaRad)
  if (Math.abs(c) < 1e-15) c = 0
  if (Math.abs(s) < 1e-15) s = 0
  return [c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
}

/** M = Flip · Rz(θ), the frame-to-frame rotation of a mate (`transforms.flip_rz`). */
export function flipRz(thetaRad: number): Matrix {
  return matmul(FLIP, rotationZ(thetaRad))
}

/**
 * J(q): q mm along, or q degrees (right-handed) about, a frame axis
 * (`kinematics.joint_matrix`).
 */
export function jointMatrix(type: JointType, axis: JointAxis, value: number): Matrix {
  const k = JOINT_AXES.indexOf(axis)
  if (k < 0) throw new Error(`unknown joint axis ${String(axis)}`)
  if (type === 'prismatic') {
    const t = [0, 0, 0]
    t[k] = value
    return [1, 0, 0, t[0], 0, 1, 0, t[1], 0, 0, 1, t[2], 0, 0, 0, 1]
  }
  const rz = rotationZ(radians(value))
  const c = rz[0]
  const s = rz[4]
  if (k === 2) return rz
  if (k === 0) return [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1]
  return [c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1]
}
