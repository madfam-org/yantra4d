# Truthful Tablaco quote remediation roadmap

Last updated: 2026-05-14

## Scope

Yantra4D owns the Tablaco project geometry and the project quote export endpoint used by Selva and Cotiza.

## Current evidence

- `https://app.yantra4d.com/project/tablaco` serves the Yantra4D SPA shell.
- Enclii reports `yantra4d-backend`, `yantra4d-studio`, `yantra4d-admin`, and `yantra4d-landing` healthy.
- `POST /api/projects/tablaco/cotiza-quote-request` exists and fails closed behind pro-tier auth.
- The local Cotiza export tests pass for strict quote behavior and `MARKET_DATA_UNAVAILABLE` handling.
- Yantra's own ForgeSight BOM quote helper still reports `forgesight_pending` for full BOM-to-cart quoting.

## Production gap

The Tablaco quote endpoint is present, but Selva needs a dedicated service identity to call it, and the endpoint cannot return a client-ready result until Cotiza receives verified ForgeSight market data.

## Remediation plan

1. Keep `POST /api/projects/tablaco/cotiza-quote-request` pro/service-auth protected.
2. Add a dedicated Selva service account grant for `yantra4d:quote`.
3. Require `require_market_verified=true` for Selva-initiated client quotes.
4. Ensure the canonical Tablaco render exists before quote export and returns non-zero geometry.
5. Preserve `424 MARKET_DATA_UNAVAILABLE` when Cotiza or ForgeSight cannot verify market data.
6. Surface `client_ready`, `market_verified`, `needs_review`, and provenance in the Studio UI.
7. Keep BOM/cart quote helper marked non-client-ready until ForgeSight offer integration is complete.

## Acceptance gates

- Selva can call the Tablaco quote endpoint with a service token.
- Missing auth returns an explicit auth/tier failure.
- Missing render returns a render-required failure.
- Unverified market data returns `424`.
- Successful quotes include `client_ready=true`, `market_verified=true`, and ForgeSight provenance.
