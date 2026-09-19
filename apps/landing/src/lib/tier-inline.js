/* global window, document, TIER_STORAGE_KEY, classifyTier, parseTierOverride, parseStoredTier, readCheapSignals */
/**
 * The <head> bootstrap. Runs INLINE before first paint, after the text of
 * `tier-core.js` (exports stripped) — see BaseLayout.astro. Its only job is to
 * set `data-tier` / `data-tier-source` on <html> from the cheap signals, so the
 * CSS and the islands agree on the tier from the very first frame.
 *
 * Fail closed: the markup already carries data-tier="still"; any exception
 * leaves it there and records the reason in data-tier-source.
 */
(function () {
  var root = document.documentElement;
  try {
    var override = parseTierOverride(window.location.search);
    var stored = null;
    try {
      stored = parseStoredTier(window.localStorage.getItem(TIER_STORAGE_KEY), Date.now());
    } catch {
      stored = null; /* private mode, disabled storage — decide from signals */
    }
    var tier;
    var source;
    if (override) {
      tier = override;
      source = 'override';
    } else if (stored) {
      tier = stored.tier;
      source = stored.user ? 'user' : 'stored';
    } else {
      tier = classifyTier(readCheapSignals(window));
      source = 'signals';
    }
    root.setAttribute('data-tier', tier);
    root.setAttribute('data-tier-source', source);
  } catch {
    root.setAttribute('data-tier', 'still');
    root.setAttribute('data-tier-source', 'error');
  }
})();
