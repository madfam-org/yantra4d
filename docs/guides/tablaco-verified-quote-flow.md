# Private-Cartridge Verified Quote Flow

This runbook covers the Yantra4D side of the Selva -> Yantra4D -> Cotiza -> ForgeSight flow for a client-private cartridge. `<private-slug>` below is that cartridge's slug, as listed in `PRIVATE_PROJECTS`.

## Contract

Yantra4D is the project and geometry relay. It must not claim market pricing truth on its own.

The supported flow is:

```text
Selva agent
  -> POST /api/projects/<private-slug>/cotiza-quote-request
  -> Cotiza POST /quotes/from-yantra4d
  -> ForgeSight verified market pricing
  -> Cotiza response relayed by Yantra4D
```

## Strict market verification

Requests that need a client-ready quote must send:

```json
{
  "material": "PLA",
  "quantity": 1,
  "process": "fdm",
  "currency": "MXN",
  "finish": "standard",
  "mode": "unit",
  "parameters": {
    "size": 20,
    "thick": 2.5,
    "rod_D": 3,
    "clearance": 0.2
  },
  "require_market_verified": true
}
```

Yantra4D forwards `require_market_verified` as a top-level Cotiza field and preserves the cartridge's mode/parameters in `item.options`.

## Success response

A client-ready response must include:

```json
{
  "status": "success",
  "project": "<private-slug>",
  "source": "cotiza",
  "market_verified": true,
  "pricing_source": "forgesight",
  "needs_review": false,
  "client_ready": true
}
```

## Blocked response

If strict market verification is requested and Cotiza/ForgeSight cannot verify the data, Yantra4D returns `424` with `MARKET_DATA_UNAVAILABLE`. It must not convert this into a generic `502`.

If strict verification is not requested, Yantra4D may relay a review-only quote, but it must label:

- `market_verified: false`
- `needs_review: true`
- `client_ready: false`
- `fallback_reason`

## Operations policy

Use Enclii first for production diagnostics and verification. Direct raw infrastructure access is break-glass only.

Recommended Enclii-side checks:

```text
enclii quote-flow verify --project <private-slug> --agent selva --require-market-verified
enclii ops pods diagnose yantra4d-backend -n yantra4d --json
enclii ops apps status yantra4d -n argocd --json
```

Record missing Enclii adapters as platform gaps instead of normalizing raw production commands.

## Remaining gate

The authenticated smoke path is not complete until a pro-tier Selva/Janua token can render and request a quote for the private cartridge in production without bypassing access control.
