/**
 * Two CPython float behaviours the keystone's reference forward kinematics relies on,
 * reproduced exactly so that the viewer's poses match the golden pose files to the last
 * printed digit (ASM-1 §9, D4).
 *
 * - `sum()` of floats (CPython ≥ 3.12) is Neumaier-compensated and starts from the
 *   integer 0. The keystone's 4×4 products, rigid inverses and follower terms all use it.
 * - `math.radians(x)` is `x * (π / 180)` with the constant computed once.
 */

/** π / 180 as CPython's `degToRad`: one correctly rounded division. */
export const DEG_TO_RAD = Math.PI / 180

/** `math.radians(deg)`. */
export function radians(deg: number): number {
  return deg * DEG_TO_RAD
}

/**
 * `sum(values)` of floats, as CPython ≥ 3.12 computes it (Objects/bltinmodule.c,
 * `builtin_sum_impl`): the integer start 0 plus the first item gives a float, then the
 * remaining items are added with Neumaier's compensation, and the compensation is added
 * once at the end when it is non-zero and finite.
 */
export function pySum(values: readonly number[]): number {
  const n = values.length
  if (n === 0) return 0
  // int 0 + float x is float(0) + x: this also turns -0.0 into 0.0.
  let f = 0 + values[0]
  let c = 0
  for (let i = 1; i < n; i++) {
    const x = values[i]
    const t = f + x
    if (Math.abs(f) >= Math.abs(x)) {
      c += (f - t) + x
    } else {
      c += (x - t) + f
    }
    f = t
  }
  if (c !== 0 && Number.isFinite(c)) f += c
  return f
}
