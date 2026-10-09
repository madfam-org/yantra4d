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
**Registry product**: Yantra4D (`yantra4d`, live, front door yantra4d.com).

### Deployed services

| Service            | Public domain      | Container port |
| ------------------ | ------------------ | -------------- |
| `yantra4d-landing` | yantra4d.com       | 3000           |
| `yantra4d-studio`  | app.yantra4d.com   | 3001           |
| `yantra4d-backend` | api.yantra4d.com   | 8000           |
| `yantra4d-admin`   | admin.yantra4d.com | 3002           |

**Kubernetes namespace**: `yantra4d`
**Cluster**: bare-metal k3s (see topology section below).

### Upstream dependencies (this repo consumes)

- geom-core (C++ geometry analysis + WASM bindings) — **planned, not yet wired**;
  geometry is currently implemented in-house (Python SDF engine + OpenSCAD/CadQuery)
- postgres (catalog, user designs)
- cloudflare R2 (asset storage) — **planned, not yet wired**; render artifacts are
  currently written to ephemeral local disk (garbage-collected), not R2
- janua (auth)
- dhanam (billing for paid features)
- selva (LLM-assisted design) — inference routed through the Selva gateway
  (`SELVA_BASE_URL`); direct provider calls are disallowed

### Downstream consumers (this repo is consumed by)

- forj (WIRED — the catalog materializer reads `GET /api/projects` + `GET /api/projects/<slug>/storefront` and drives `POST /api/render` for glb+stl, authenticated as the `forj-catalog-materializer` Janua client_credentials client with scope `yantra4d:render`)
- digifab-quoting (PLANNED — no quoting call exists; parametric designs → quotes is aspirational)
- pravara-mes (print-ready G-code export)
- external creators (Hyperobjects Commons contributors)

### Key environment variables

- `DATABASE_URL — Postgres`
- `R2_ACCESS_KEY_ID / R2_SECRET — asset storage`
- `JANUA_JWKS_URI — auth`
- `SELVA_BASE_URL — LLM routing`
- `YANTRA4D_OPENSCAD_BACKEND — auto (default) / manifold / cgal; auto-probes the OpenSCAD build and falls back when Manifold is unavailable`
- `YANTRA4D_CQ_WORKERS — warm CadQuery worker pool size (default 2; 0 disables the pool)`

---

## MADFAM Ecosystem Map

Everything below is embedded here so this document stands alone. The product
tables are rendered from the public projection of the MADFAM product registry
(`madfam-org/solarpunk-foundry` → `packages/core/src/products/projection.public.json`,
generated from the registry in `madfam-org/internal-devops`). To change a row,
change the registry and re-render — never hand-edit a rendered copy.

Estate counts (services, ArgoCD applications, namespaces) are deliberately not
typed here: they move weekly. The dated figures live in the private operations
record, `madfam-org/internal-devops` (`infrastructure/topology.md`).

### Products in the registry

32 customer-facing products, grouped by the registry's category and listed in registry order. `—` means the registry records no public front door yet.

#### Infrastructure

| Product          | Repo                      | Front door | Lifecycle  | Role                                                                                    |
| ---------------- | ------------------------- | ---------- | ---------- | --------------------------------------------------------------------------------------- |
| **Enclii**       | `madfam-org/enclii`       | enclii.dev | live       | PaaS control plane — every deploy goes through it                                       |
| **Janua**        | `madfam-org/janua`        | janua.dev  | live       | OIDC/OAuth 2.0 identity provider — RS256 JWKS at `auth.madfam.io/.well-known/jwks.json` |
| **Selva**        | `madfam-org/selva-office` | selva.town | live       | LLM inference gateway (OpenAI-compatible `/v1`) + agent orchestration                   |
| **Fragua**       | `madfam-org/enclii`       | —          | incubating | —                                                                                       |
| **Enclii Depot** | `madfam-org/enclii`       | —          | incubating | —                                                                                       |

#### Intelligence

| Product        | Repo                    | Front door         | Lifecycle  | Role                                                                      |
| -------------- | ----------------------- | ------------------ | ---------- | ------------------------------------------------------------------------- |
| **Forgesight** | `madfam-org/forgesight` | forgesight.app     | live       | Digital-fabrication industry intelligence (pricing/vendor feed to Cotiza) |
| **Dhanam**     | `madfam-org/dhanam`     | dhan.am            | live       | Billing, entitlements and payment gateways (Stripe, Mercado Pago, SPEI)   |
| **Fortuna**    | `madfam-org/fortuna`    | fortuna.tube       | live       | Problem intelligence / zeitgeist analysis                                 |
| **Rondelio**   | `madfam-org/rondelio`   | rondel.io          | live       | Games                                                                     |
| **Factlas**    | `madfam-org/factlas`    | factl.as           | live       | Geospatial facts                                                          |
| **Tlacuilo**   | `madfam-org/tlacuilo`   | tlacuilo.madfam.io | beta       | Document intelligence (OCR)                                               |
| **LexiDrop**   | `madfam-org/lexidrop`   | ld.madfam.io       | incubating | —                                                                         |

#### Standards

| Product       | Repo                   | Front door         | Lifecycle  | Role                                                                      |
| ------------- | ---------------------- | ------------------ | ---------- | ------------------------------------------------------------------------- |
| **Karafiel**  | `madfam-org/karafiel`  | karafiel.mx        | live       | Operational compliance — CFDI, NOM-151, e.firma; owns legal-ops templates |
| **Tezca**     | `madfam-org/tezca`     | tezca.mx           | live       | Mexican law oracle (informational only — feeds Karafiel)                  |
| **Avala**     | `madfam-org/avala`     | avala.studio       | live       | Learning and competency verification                                      |
| **Meridian**  | `madfam-org/meridian`  | meridian.madfam.io | degraded   | —                                                                         |
| **geom-core** | `madfam-org/geom-core` | —                  | incubating | —                                                                         |

#### Applications

| Product             | Repo                         | Front door       | Lifecycle  | Role                                                                  |
| ------------------- | ---------------------------- | ---------------- | ---------- | --------------------------------------------------------------------- |
| **Yantra4D**        | `madfam-org/yantra4d`        | yantra4d.com     | live       | Phygital fabrication                                                  |
| **Cotiza**          | `madfam-org/digifab-quoting` | cotiza.studio    | live       | Quoting engine (fabrication + services)                               |
| **Pravara MES**     | `madfam-org/pravara-mes`     | mes.madfam.io    | live       | Fabrication routing and dispatch (physical jobs)                      |
| **Voxa**            | `madfam-org/voxa`            | voxa.madfam.io   | live       | Assistive communication                                               |
| **PhyndCRM**        | `madfam-org/phynd-crm`       | phynd.app        | live       | CRM — consent, campaigns, attribution                                 |
| **CEQ**             | `madfam-org/ceq`             | ceq.lol          | degraded   | Generative asset pipeline — ComfyUI wrapper behind `/v1/render`       |
| **Acervo**          | `madfam-org/acervo`          | acervo.madfam.io | live       | Records engine                                                        |
| **Kalya**           | `madfam-org/kalya`           | kalya.app        | live       | Booking and scheduling                                                |
| **Symbiosis HCM**   | `madfam-org/symbiosis-hcm`   | hcm.madfam.io    | live       | Human capital management — Mexican payroll                            |
| **Nauta**           | `madfam-org/nauta`           | nauta.quest      | live       | Fractional CTO practice — staff cockpit and per-client ERP workspaces |
| **Fashion Cabinet** | `madfam-org/fashion-cabinet` | fashioncabi.net  | live       | Parametric fashion                                                    |
| **Periplo**         | `madfam-org/periplo`         | —                | incubating | —                                                                     |
| **RouteCraft**      | `madfam-org/routecraft`      | routecraft.app   | live       | Trip planning                                                         |
| **Telesia**         | `madfam-org/telesia`         | telesia.quest    | incubating | Completion                                                            |
| **Marca**           | `madfam-org/marca`           | madf.am          | incubating | —                                                                     |

### Retired products — never present as live

| Product | Retired on | Successor | Redirect |
| ------- | ---------- | --------- | -------- |
| PENNY   | 2026-07-25 | Selva     | none     |
| Sim4D   | 2026-08-30 | Yantra4D  | none     |
| SPARK   | 2026-04-08 | —         | none     |

### Cross-repo conventions

- **Auth**: every authenticated service verifies Janua JWTs via JWKS at
  `https://auth.madfam.io/.well-known/jwks.json`. RS256 only — HS256 is
  banned on any path that verifies a Janua token (audit 2026-04-23 H3/H4);
  an app's own session cookie needs its own secret.
- **Billing**: credit metering + entitlements flow through Dhanam. See
  `madfam-org/dhanam` for the meter/entitlement/invoice APIs.
- **Inference**: every LLM call should route through Selva
  (`selva-office`) at `/v1` (OpenAI-compatible). Do not talk directly
  to OpenAI / Anthropic from service code.
- **Agent SaaS tools**: end-user delegated tool calls (Slack, Gmail, etc.)
  route through Coupler (`madfam-org/coupler`, the Agent Tool Plane), not the
  Enclii Provider Hub.
  Operator infra actions stay on Enclii `providers.*` / `ops.*` (proxied as
  `madfam.ops.*` from Coupler for admin agents only).
- **Third-party messages**: email/SMS/chat to people outside MADFAM go out
  through Angelia Courier (`madfam-org/angelia`). Carve-outs: Janua's
  customer-configured alert notifier and Selva agent tools.
- **CORS**: explicit allowlist per service. Wildcards are banned
  (audit 2026-04-23 H2/H5/H6).
- **Images**: `@sha256:`-pinned in every manifest; mutable tags such as
  `:latest` are a Kyverno policy violation.
- **Onboarding**: `enclii onboard` (`POST /v1/admin/onboard` on
  switchyard-api) creates namespace, ArgoCD app, Cloudflare tunnel routes,
  Janua client, and NetworkPolicies in one shot. See
  `enclii/docs/guides/ONBOARDING_GUIDE.md`.

### Production topology

Bare-metal k3s (v1.33+), 4 nodes, described by ROLE only. This file is
generated and copied into public repos, so it never carries node hostnames,
IP addresses or hardware SKUs (2026-07-16 exposure class 1). Node identity
lives only in `madfam-org/internal-devops`.

- control-plane node — control plane + primary workload
- worker node — workloads + Longhorn second replica
- two builder nodes (labelled `role=builder`, tainted
  `builder=true:NoSchedule`) — ARC runners only

**Ingress**: Cloudflare Tunnel → cloudflared pods → K8s ClusterIP → container port.
Zero exposed node ports. TLS terminated at Cloudflare edge.

**Storage**: Longhorn CSI in 2-replica mode across the control-plane and
worker nodes. Object storage: Cloudflare R2 (zero egress).

**GitOps**: ArgoCD App-of-Apps with self-heal. Push to `main` → CI builds →
GHCR → `kustomize edit set image` commits the digest →
ArgoCD syncs → Switchyard tracks lifecycle events.

**Operational access** (SSH, kubeconfigs, node identity, estate counts, cost
ledger): private repo `madfam-org/internal-devops`. Not in any public repo.
Policy: the repo-boundary contract, `internal-devops/docs/repo-boundary-contract.md`.

---

## Enclii CLI — DevOps Reference

**Strong preference: use `enclii` over `kubectl`** for all operational
tasks. The CLI routes through Switchyard API, which gives you audit
logging, lifecycle event tracking, and service-scoped context. Escape
to kubectl only for the gaps listed at the end of this section.

### Install

GitHub Releases are the verified binary channel (Linux, macOS and Windows
archives with checksums): `https://github.com/madfam-org/enclii/releases`.
Homebrew, Scoop and `get.enclii.dev` are convenience targets, not yet
monitored.

```bash
# From source (any OS with Go)
git clone https://github.com/madfam-org/enclii.git
cd enclii && make build-cli && ./bin/enclii --version
```

### Auth

```bash
enclii login                  # browser SSO (Janua)
enclii whoami                 # verify active session
enclii logout                 # clear local creds
```

Global flags: `--api-endpoint` (or `ENCLII_API_ENDPOINT`, default
`https://api.enclii.dev`) and `--api-token` (or `ENCLII_API_TOKEN`; legacy
`ENCLII_TOKEN` is still read) for non-interactive use. Set
`ENCLII_PROJECT=<project-slug>` (or pass `--project`) when a command has to
resolve a service name.

### Day-to-day for yantra4d-backend

The commands below default to `yantra4d-backend` — the primary service name for
this repo as registered in Switchyard. For any other service in the
ecosystem, swap the name. Environments are `dev`, `staging` and `prod`;
most commands default to `dev`, so pass `--env prod` for production.

```bash
# Status
enclii ps --env prod

# Logs
enclii logs yantra4d-backend --env prod -f                    # live tail
enclii logs yantra4d-backend --env prod --since 1h -n 200     # last hour

# Deploy (reads service.yaml)
enclii deploy --env staging --wait
enclii deploy --env prod --canary 10% --change-ticket <url>

# Rollback
enclii rollback yantra4d-backend --env prod                   # previous release
enclii rollback yantra4d-backend v42 --env prod

# Releases + deployment history
enclii releases yantra4d-backend -n 20
enclii deployments list

# Secrets (routed through Lockbox → Vault → ESO → K8s)
enclii secrets list --env prod
enclii secrets set MY_KEY=value --secret --env prod

# Chat-safe operator intake (values never pass through agent chat)
enclii secrets intake submit <target> --reason "<audit reason>" --stdin
enclii secrets intake status <intake-id>

# Domains, tunnel routes, DNS
enclii domains list --service yantra4d-backend
enclii domains add my.example.com --service yantra4d-backend   # auto-provisions tunnel route + DNS

# Scheduled jobs, routing, serverless
enclii jobs list --project <project-slug>
enclii junctions list --project <project-slug>
enclii functions list

# Observability
enclii observe health --service <service-id>

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

| Code | Meaning          |
| ---- | ---------------- |
| 0    | success          |
| 10   | validation error |
| 20   | build failed     |
| 30   | deploy failed    |
| 40   | timeout          |
| 50   | auth error       |

---

## Document provenance

Rendered by `madfam-org/enclii/docs/templates/ecosystem/generator.py` from this
repo's metadata entry (plus any private overlay kept in this repo) and the
public product-registry projection. First generated 2026-04-23 for the "each
repo stands alone" docs sweep. Do not hand-edit this file: change the metadata,
overlay or registry and re-render. `generator.py --check <repo-path>` fails when
this file differs from what the generator would write.
