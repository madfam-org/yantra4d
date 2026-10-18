/**
 * Server-render budget rules the Studio applies before spending a visitor's
 * hourly render quota on work the visitor did not ask for.
 */

/**
 * Whether background variant renders may run for a visitor with these tier
 * limits (a tiers.json entry, from /api/me or /api/tiers).
 *
 * Each background variant is a full `/api/render-stream` call, and the API
 * counts every one against the caller's hourly server-render bucket
 * (`backend_renders_per_hour`: guest 10, essentials 30, pro 150). The ghost
 * preview cache (hooks/render/useParameterPreviewCache) wants up to six of them
 * (three parameters x min/max) after every completed render, so one click on
 * "Generate" used to spend up to 7 renders of a metered budget on hover
 * previews the visitor never asked for: a guest hit HTTP 429 after two or
 * three clicks, and a Pro customer, whose CadQuery renders have no in-browser
 * fallback, after about twenty. Only an unlimited budget (-1) can absorb them;
 * unknown limits are treated as metered.
 */
export function backgroundRendersAllowed(limits: Record<string, unknown> | null | undefined): boolean {
  const budget = limits?.backend_renders_per_hour ?? limits?.renders_per_hour
  return budget === -1
}
