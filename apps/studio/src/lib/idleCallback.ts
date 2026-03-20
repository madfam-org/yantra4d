/**
 * requestIdleCallback polyfill for Safari (which lacks native support).
 * Falls back to setTimeout with a synthetic IdleDeadline object.
 */

interface IdleDeadlineLike {
  didTimeout: boolean
  timeRemaining: () => number
}

type IdleCallbackFn = (deadline: IdleDeadlineLike) => void

interface IdleRequestOptions {
  timeout?: number
}

export const requestIdleCallback: (cb: IdleCallbackFn, opts?: IdleRequestOptions) => number =
  globalThis.requestIdleCallback ||
  ((cb: IdleCallbackFn, opts?: IdleRequestOptions) =>
    setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 50 }), opts?.timeout || 1) as unknown as number)

export const cancelIdleCallback: (id: number) => void =
  globalThis.cancelIdleCallback || clearTimeout
