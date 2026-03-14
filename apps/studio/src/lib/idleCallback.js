/**
 * requestIdleCallback polyfill for Safari (which lacks native support).
 * Falls back to setTimeout with a synthetic IdleDeadline object.
 */
export const requestIdleCallback =
  globalThis.requestIdleCallback ||
  ((cb, opts) => setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 50 }), opts?.timeout || 1))

export const cancelIdleCallback =
  globalThis.cancelIdleCallback || clearTimeout
