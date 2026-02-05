import '@testing-library/jest-dom'

// Mock window.matchMedia (not available in jsdom)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock IntersectionObserver (not available in jsdom)
class IntersectionObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.IntersectionObserver = window.IntersectionObserver || (IntersectionObserverStub as any)
