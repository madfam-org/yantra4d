# Cotiza and ForgeSight Pricing Flow

Yantra4D is the geometry source. Cotiza is the quote system. ForgeSight is the
market data source. Yantra4D must not claim market-verified pricing by itself.

## Export flow

`POST /api/projects/<slug>/cotiza-quote-request` builds a Cotiza payload from:

1. Project manifest metadata.
2. Latest rendered mesh geometry.
3. Request body fabrication preferences.

The exported payload is labeled as a quote request only:

1. `market_verified: false`
2. `fallback_reason: "Quote request export only; market pricing is determined by Cotiza."`
3. `provenance.geometry_source: "latest_render_mesh"`

Cotiza and ForgeSight are responsible for deciding market verification.

## BOM/cart flow

`POST /api/projects/<slug>/bom/cart` asks ForgeSight for BOM pricing. The
response exposes item-level and response-level provenance:

1. `source`
2. `market_verified`
3. `fallback_reason`
4. `sample_count`

Fallback or hardcoded pricing is allowed only when explicitly labeled
`market_verified: false`.

## Verification rule

Yantra4D treats ForgeSight material benchmarks as market verified only when the
response has samples, an update timestamp, and positive benchmark pricing.
