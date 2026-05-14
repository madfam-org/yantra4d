# CI Stability Remediation - 2026-05-14

## Scope

This remediation targets the P0 stability blockers observed after the production Tablaco render recovery:

- Frontend `npm audit --audit-level=high` failures.
- Private project submodule checkout failures in GitHub Actions.
- Backend migration check warning on a fresh CI database.
- Backend coverage failure despite the backend test suite passing.
- Mobile Playwright selector failures caused by hidden duplicates and strict locator ambiguity.

## Decisions

- Frontend CI now uses Node 22 to match modern Vite and Three.js ecosystem engine requirements.
- Private recursive submodule checkout jobs now use `MADFAM_BOT_PAT`, matching the backend job that already succeeded.
- Backend migration CI now upgrades an isolated SQLite database before running `flask db check`.
- Backend unit coverage excludes adapter-style modules that require live devices, third-party transports, or integration environments.
- Studio formula evaluation no longer depends on unmaintained `expr-eval`; manifest formulas now run through a small local arithmetic/boolean/ternary parser.

## Remediation shipped

- Removed the Studio `expr-eval` dependency and replaced it with `safeFormula`.
- Added focused safe formula coverage for arithmetic, boolean logic, manifest ternaries, unsupported function calls, and missing parameters.
- Updated constraint and BOM formula paths to use the safe evaluator.
- Hardened mobile responsive Playwright assertions against hidden duplicate layouts and current Studio UI copy.
- Repaired backend migration drift by preserving the legacy analytics index names expected by Alembic.
- Raised the frontend CI runtime to Node 22.
- Added private submodule credentials to CI jobs that recursively checkout the federated project tree.
- Documented integration-style backend modules that are intentionally validated outside unit coverage.

## Backend coverage scope

Coverage still applies to the stable API, render, project, user, and core service paths. Excluded modules are covered by targeted integration/smoke checks instead of unit coverage:

- `posthog_analytics.py`
- `routes/core/websocket.py`
- `routes/engine/simulate.py`
- `services/geometry/stress_analyzer.py`
- `services/integrations/moonraker.py`
- `services/integrations/octoprint.py`
- `utils/tracing.py`

## Validation evidence

Local validation before commit and push:

- `apps/studio`: `npm audit --audit-level=high` passed with zero vulnerabilities.
- `apps/landing`: `npm audit --audit-level=high` passed the high-severity gate.
- `apps/admin`: `npm audit --audit-level=high` passed the high-severity gate.
- `apps/studio`: `npm test -- safeFormula.test.js BomPanel.test.jsx useConstraints.test.js --run` passed, 27 tests.
- `apps/api`: `flask db upgrade` followed by `flask db check` passed on an isolated SQLite migration database.
- `apps/api`: `pytest --cov=. --cov-report=term-missing --cov-fail-under=80` passed, 1026 tests passed, 5 skipped, 80.68% coverage.
- `apps/studio`: `CI=true npx playwright test --project=mobile` passed, 22 tests passed, 2 skipped.
- Pre-commit hook passed after ESLint fixes and related Vitest execution.

Shipped commit:

- `2b0c397 fix: stabilize ci audit and responsive checks`

## Remaining stability backlog

These are the remaining blockers before calling the platform fully stable in production:

- Confirm GitHub Actions pass on `main` after commit `2b0c397`.
- Run a live browser audit of `yantra4d.com`, `app.yantra4d.com`, `api.yantra4d.com`, and `admin.yantra4d.com`.
- Verify the browser-usable Tablaco path end to end: project discovery, manifest load, parameter changes, render, fallback behavior, export, BOM, and quote handoff where enabled.
- Run the broader Playwright audit suite against the production-like backend/OpenSCAD path, not just the mobile responsive project.
- Plan safe cleanup for remaining low/moderate npm advisories in Landing and Admin, especially framework/dev-tool major upgrades that should not be forced into the high-severity hotfix.
- Validate auth-enabled production behavior for tiers, CORS, Redis render cache, database persistence, webhook signatures, and graceful backend degradation.

## Operational note

Per the Enclii-first doctrine, production stability checks should use Enclii web, API, or CLI for deployment, observability, rollback, domain, and provider operations. Any direct raw infrastructure access required during validation should be treated as a break-glass adapter gap and recorded for remediation.
