import '@testing-library/jest-dom'

// Polyfill localStorage/sessionStorage — vitest 4.x jsdom environment wraps
// Storage in a Proxy that lacks standard methods (clear, getItem, etc.).
function createStoragePolyfill() {
  const store = {}
  return {
    getItem(key) { return key in store ? store[key] : null },
    setItem(key, value) { store[key] = String(value) },
    removeItem(key) { delete store[key] },
    clear() { for (const key in store) delete store[key] },
    get length() { return Object.keys(store).length },
    key(index) { return Object.keys(store)[index] ?? null },
  }
}
if (typeof localStorage === 'undefined' || typeof localStorage.clear !== 'function') {
  Object.defineProperty(globalThis, 'localStorage', { value: createStoragePolyfill(), writable: true })
}
if (typeof sessionStorage === 'undefined' || typeof sessionStorage.clear !== 'function') {
  Object.defineProperty(globalThis, 'sessionStorage', { value: createStoragePolyfill(), writable: true })
}

// Configurable matchMedia mock — allows tests to simulate mobile/tablet viewports.
// Usage in tests:
//   globalThis.__setMediaQuery('(max-width: 767px)', true)  // simulate mobile
//   globalThis.__resetMediaQueries()                         // reset to defaults
const mediaQueryOverrides = new Map()

globalThis.__setMediaQuery = (query, matches) => {
  mediaQueryOverrides.set(query, matches)
}

globalThis.__resetMediaQueries = () => {
  mediaQueryOverrides.clear()
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: mediaQueryOverrides.has(query) ? mediaQueryOverrides.get(query) : false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// ResizeObserver is not available in jsdom
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = window.ResizeObserver || ResizeObserverStub

// URL.createObjectURL / revokeObjectURL are not available in jsdom
if (typeof URL.createObjectURL === 'undefined') {
  URL.createObjectURL = () => 'blob:mock-url'
}
if (typeof URL.revokeObjectURL === 'undefined') {
  URL.revokeObjectURL = () => {}
}
