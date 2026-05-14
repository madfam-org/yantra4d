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
- Studio formula evaluation no longer depends on unmaintained `expr-eval`; manifest formulas now run through a small local arithmetic/boolean parser.

## Backend coverage scope

Coverage still applies to the stable API, render, project, user, and core service paths. Excluded modules are covered by targeted integration/smoke checks instead of unit coverage:

- `posthog_analytics.py`
- `routes/core/websocket.py`
- `routes/engine/simulate.py`
- `services/geometry/stress_analyzer.py`
- `services/integrations/moonraker.py`
- `services/integrations/octoprint.py`
- `utils/tracing.py`
