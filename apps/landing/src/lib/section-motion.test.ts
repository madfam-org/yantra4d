import { afterEach, describe, expect, it, vi } from 'vitest';
import { observeSectionMotion } from './section-motion';

afterEach(() => vi.unstubAllGlobals());

describe('section motion', () => {
  it('observes only the section and pauses again when it leaves the viewport', () => {
    const section = document.createElement('section');
    section.innerHTML = '<div><svg></svg></div>';
    let callback: IntersectionObserverCallback;
    const observe = vi.fn();
    vi.stubGlobal('IntersectionObserver', class {
      constructor(cb: IntersectionObserverCallback) { callback = cb; }
      observe = observe;
    });
    observeSectionMotion(section);
    expect(observe.mock.calls).toEqual([[section]]);
    expect(section.hasAttribute('data-motion-visible')).toBe(false);
    for (const visible of [false, true, false, true]) {
      callback!([{ isIntersecting: visible } as IntersectionObserverEntry], {} as IntersectionObserver);
      expect(section.hasAttribute('data-motion-visible')).toBe(visible);
    }
  });

  it('leaves static content available when observers are unavailable', () => {
    vi.stubGlobal('IntersectionObserver', undefined);
    const section = document.createElement('section');
    section.innerHTML = '<p>Visible copy</p>';
    expect(() => observeSectionMotion(section)).not.toThrow();
    expect(section.textContent).toBe('Visible copy');
    expect(section.hidden).toBe(false);
    expect(() => observeSectionMotion(null)).not.toThrow();
  });
});
