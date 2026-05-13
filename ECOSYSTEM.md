# yantra4d — Ecosystem Context

> [!IMPORTANT]
> MADFAM-ENCLII-FIRST-LEGACY-RAW v1: This document contains legacy raw infrastructure command examples.
> Routine production operations must use Enclii web, API, or CLI. Treat raw
> `kubectl`, `helm`, SSH, provider CLI/API, `docker exec`, and direct container
> access as platform bootstrap or documented break-glass only, and record any
> missing Enclii adapter gap.


> **Parametric CAD + "Hyperobjects Commons" — SDF-based geometry compiler with marketplace.**

This file is self-contained: a Claude session on a fresh machine can operate
this service by reading only this one document. No external links are
load-bearing — the MADFAM ecosystem map and the full enclii CLI reference are
embedded below.

---

## 1. What this repo is

Yantra4D is a poly-kernel CAD engine: continuous SDF geometry compiler, manifest-driven parametric design, nanoscale material intelligence, interactive digital-twin simulation. Also hosts the "Hyperobjects Commons" marketplace where parametric designs can interface with each other via Common Denominator Geometry (standardized snaps, threads, joints). Domain: `yantra4d.com`.

**Pillar**: Fabrication / CAD + Commons
**Type**: service
**Status**: production

### Deployed services

| Service | Public domain | Container port |
|---|---|---|
| `yantra4d-landing` | yantra4d.com | 3000 |
| `yantra4d-studio` | app.yantra4d.com | 3001 |
| `yantra4d-backend` | api.yantra4d.com | 8000 |
| `yantra4d-admin` | admin.yantra4d.com | 3002 |

**Kubernetes namespace**: `yantra4d`
**Cluster**: bare-metal k3s on Hetzner (see topology section below).

### Upstream dependencies (this repo consumes)

- geom-core (C++ geometry analysis + WASM bindings)
- postgres (catalog, user designs)
- cloudflare R2 (asset storage)
- janua (auth)
- dhanam (billing for paid features)
- selva (LLM-assisted design)

### Downstream consumers (this repo is consumed by)

- digifab-quoting (parametric designs → quotes)
- forj (storefront listings)
- pravara-mes (print-ready G-code export)
- external creators (Hyperobjects Commons contributors)

### Key environment variables

- `DATABASE_URL — Postgres`
- `R2_ACCESS_KEY_ID / R2_SECRET — asset storage`
- `JANUA_JWKS_URI — auth`
- `SELVA_BASE_URL — LLM routing`

---

## MADFAM Ecosystem Map

MADFAM runs ~40 services on sovereign bare-metal infrastructure. Everything
below is embedded here so this document stands alone.

### The platforms every repo should know about

| Platform | Repo | Role |
|---|---|---|
| **Enclii** | `madfam-org/enclii` | PaaS control plane — all deploys go through this |
| **Janua** | `madfam-org/janua` | OIDC/OAuth 2.0 provider — RS256 JWKS at `auth.madfam.io/.well-known/jwks.json` |
| **Dhanam** | `madfam-org/dhanam` | Billing + payment gateways (Stripe, Mercado Pago, SPEI, etc.) |
| **Selva** | `madfam-org/autoswarm-office` | LLM inference routing + agent orchestration |
| **Karafiel** | `madfam-org/karafiel` | Operational compliance — CFDI, NOM-151, e.firma, SAT-adjacent. Owns legal-ops / contract templates |
| **Tezca** | `madfam-org/tezca` | Mexican law oracle (informational only — feeds Karafiel) |
| **Cotiza** | `madfam-org/digifab-quoting` | MADFAM's quoting engine (fabrication + services) |
| **Forgesight** | `madfam-org/forgesight` | Digital fabrication industry intelligence (pricing/vendor feed to Cotiza) |
| **Pravara MES** | `madfam-org/pravara-mes` | Fabrication-node routing and dispatch (physical jobs) |
| **PhyndCRM** | `madfam-org/phynd-crm` | Client-facing deliverables portal (single pane of glass per engagement) |
| **Fortuna** | `madfam-org/fortuna` | Problem intelligence / zeitgeist analysis |
| **Avala** | `madfam-org/avala` | Learning verification platform |

### Cross-repo conventions

- **Auth**: every authenticated service verifies Janua JWTs via JWKS at
  `https://auth.madfam.io/.well-known/jwks.json`. RS256 only — HS256 is
  fail-closed after the 2026-04-23 audit (H3/H4).
- **Billing**: credit metering + entitlements flow through Dhanam. See
  `madfam-org/dhanam` for the meter/entitlement/invoice APIs.
- **Inference**: every LLM call should route through Selva
  (`autoswarm-office`) at `/v1` (OpenAI-compatible). Do not talk directly
  to OpenAI / Anthropic from service code.
- **CORS**: explicit allowlist per service. Wildcards are banned
  (audit 2026-04-23 H2/H5/H6).
- **Images**: `@sha256:`-pinned in every manifest. Kyverno fail-closes on
  `:latest` or mutable tags.
- **Onboarding**: `POST /v1/admin/onboard` on switchyard-api creates
  namespace, ArgoCD app, Cloudflare tunnel routes, Janua client, and
  NetworkPolicies in one shot. See `enclii/docs/guides/ONBOARDING_GUIDE.md`.

### Production topology

Bare-metal k3s (v1.33+) on Hetzner, 3 nodes:

- `foundry-cp` (Hetzner EX44, 14C/20T, 128 GB) — control-plane + primary workload
- `foundry-worker-01` (Hetzner AX41-NVMe, Ryzen 5 3600, 64 GB) — worker + Longhorn 2nd replica
- `foundry-builder-01` (Hetzner VPS, 2 vCPU, 4 GB, tainted `builder=true:NoSchedule`) — ARC runners only

**Ingress**: Cloudflare Tunnel → 2× cloudflared pods → K8s ClusterIP → container port.
Zero exposed node ports. TLS terminated at Cloudflare edge.

**Storage**: Longhorn CSI v1.7+ in 2-replica mode across dedicated nodes.
Object storage: Cloudflare R2 (zero egress).

**GitOps**: ArgoCD App-of-Apps (~28 apps across ~22 namespaces) with self-heal.
Push to `main` → CI builds → GHCR → `kustomize edit set image` commits digest →
ArgoCD syncs → Switchyard tracks lifecycle events.

**Operational access** (SSH, kubeconfigs, server IPs, cost ledger): private repo
`madfam-org/internal-devops`. Not in any public repo.

---

## Enclii CLI — DevOps Reference

**Strong preference: use `enclii` over `kubectl`** for all operational
tasks. The CLI routes through Switchyard API, which gives you audit
logging, lifecycle event tracking, and service-scoped context. Escape
to kubectl only for the gaps listed at the end of this section.

### Install

```bash
# macOS
brew install enclii/tap/enclii

# Linux
curl -sSL https://get.enclii.dev | bash

# From source (in the enclii repo)
make build-cli && ./bin/enclii --version
```

### Auth

```bash
enclii login                  # browser SSO (Janua)
enclii whoami                 # verify active session
enclii logout                 # clear local creds
```

Env vars: `ENCLII_API_URL` (default `https://api.enclii.dev`),
`ENCLII_TOKEN` (alternative to interactive login),
`ENCLII_PROJECT`, `ENCLII_ENV`.

### Day-to-day for yantra4d-backend

The commands below default to `yantra4d-backend` — the primary service name for
this repo as registered in Switchyard. For any other service in the
ecosystem, swap the name.

```bash
# Status + where the pods are running
enclii ps --wide
enclii ps yantra4d-backend --env production

# Logs (tail, filter, history)
enclii logs yantra4d-backend -f                          # live tail
enclii logs yantra4d-backend --since 1h --level error    # last hour, errors only
enclii logs yantra4d-backend --env staging -f

# Deploy (preview, staging, production)
enclii deploy --env preview                       # from current branch
enclii deploy --env staging
enclii deploy --env production --strategy canary --canary-percent 10

# Rollback
enclii rollback yantra4d-backend                         # previous release
enclii rollback yantra4d-backend --to-revision 5

# Releases + history
enclii releases yantra4d-backend                          # list builds
enclii releases yantra4d-backend --latest --output json

# Secrets (routed through Lockbox → Vault → ESO → K8s)
enclii secrets list yantra4d-backend
enclii secrets set MY_KEY=value --service yantra4d-backend --secret
enclii secrets rm MY_KEY --service yantra4d-backend

# Domains, tunnel routes, DNS
enclii domains list yantra4d-backend
enclii domains add yantra4d-backend my.example.com       # auto-provisions tunnel route + DNS

# Scheduled jobs (cron + one-off)
enclii jobs list
enclii jobs run <job-name>                         # trigger one-off

# Routing (ingress + TLS)
enclii junctions list yantra4d-backend

# Serverless (scale-to-zero functions)
enclii functions list

# Local dev environment
enclii local up         # spin up dependent services (postgres, redis, …)
enclii local logs
enclii local down
```

### Full onboarding (only used when adding a brand-new service)

```bash
# One-shot: namespace + ArgoCD app + tunnel routes + Janua client + netpol
enclii onboard --repo madfam-org/<name> --db-name <db> --secrets-file .env
```

### Enclii-first production operations

Enclii is the required control plane for routine production operations.
Use the web UI, API, or CLI before reaching for raw infrastructure tools:

- ArgoCD sync / diff / rollback — `enclii ops apps ...`
- Pod logs, diagnosis, and safe restarts — `enclii ops pods ...`
- Longhorn / PVC / PV inspection and repair planning — `enclii ops storage ...`
- Kyverno violations and time-bound waivers — `enclii ops policy ...`
- ExternalSecrets and Vault readiness — `enclii ops secrets ...`
- ARC runner inspection and drain workflows — `enclii ops runners ...`
- DNS, tunnels, SaaS hostnames, providers, and repo automation — `enclii providers ...`
- Service lifecycle, domains, secrets, jobs, and observability — `enclii deploy`, `enclii rollback`, `enclii logs`, `enclii observe`, `enclii domains`, `enclii secrets`, `enclii jobs`

### Break-glass-only access

Raw `kubectl`, `helm`, SSH, provider CLIs/APIs, `docker exec`, and direct
container access are allowed only for platform bootstrap or documented
break-glass emergencies when Enclii is unavailable or lacks an implemented
adapter. Record the actor, reason, target service/environment, commands
executed, result, and follow-up Enclii adapter gap or incident link.

### Cluster access

kubeconfig + SSH keys live in `madfam-org/internal-devops` (private repo)
for bootstrap and break-glass use only. Routine production operations must
go through Enclii web, API, or CLI.

### Exit codes (scripting against the CLI)

| Code | Meaning |
|---|---|
| 0  | success |
| 10 | validation error |
| 20 | build failed |
| 30 | deploy failed |
| 40 | timeout |
| 50 | auth error |

---

## Document provenance

Generated 2026-04-23 as part of the "each repo stands alone" docs sweep. If the
ecosystem map or CLI reference drifts from reality, update the generator at
`madfam-org/enclii/docs/templates/ECOSYSTEM.md.template` and re-render — don't
edit per-repo copies in isolation.
