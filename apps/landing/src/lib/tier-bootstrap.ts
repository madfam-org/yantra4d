/**
 * The exact text BaseLayout injects into <head>: `tier-core.js` with its
 * `export ` keywords stripped (so it is a classic script), followed by the
 * `tier-inline.js` bootstrap. Built here, once, so the layout and the parity
 * test cannot drift apart.
 */
import core from './tier-core.js?raw';
import boot from './tier-inline.js?raw';

export function buildTierBootstrap(): string {
  const classic = core.replace(/^export\s+/gm, '');
  return `${classic}\n${boot}`;
}
