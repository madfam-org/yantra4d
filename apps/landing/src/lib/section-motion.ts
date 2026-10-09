/** Observe only the section boundary so content-visibility can skip its subtree. */
export function observeSectionMotion(section: HTMLElement | null): void {
  if (!section || typeof IntersectionObserver === 'undefined') return;
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      section.toggleAttribute('data-motion-visible', entry.isIntersecting);
    }
  });
  observer.observe(section);
}
