# Yantra4D Admin Dashboard

Internal admin dashboard for managing the Yantra4D platform.

## Current Features

- **Project Management**: List all projects with metadata (modes, parameters, SCAD file count, modification dates)
- **Project Flags**: Toggle `is_demo` and `is_hyperobject` flags on any project (writes directly to manifest)
- **Tablaco Link Panel**: View and copy the public storefront URL for the Tablaco project
- **Authentication**: Janua-based auth with role gating (`admin` role required for write operations)

## Not Implemented (Intentionally Deferred)

- Analytics dashboard (analytics API exists but no admin UI)
- Material management (materials are managed via manifest files)
- Printer fleet management (printers managed via JSON config files in `printers/`)
- User management / subscriber listing (users managed in Janua directly)
- Billing dashboard (billing via external Dhanam platform)

## Development

```bash
cd apps/admin
npm ci --legacy-peer-deps
npm run dev          # Vite dev server on port 5174
npm run build        # Production build
npm run lint         # ESLint
npm test             # Vitest (unit tests)
npm run test:coverage # With 80% coverage thresholds
```

## Architecture

- React + Vite + Shadcn UI (aliased from `apps/studio/src/components/ui/`)
- Auth: `@janua/react-sdk` + `@janua/ui` (dev bypass when `AUTH_ENABLED !== 'true'`)
- API: Fetches from `/api/admin/*` endpoints (see `apps/api/routes/users/admin.py`)

## Test Coverage

Coverage thresholds: 80% (statements, branches, functions, lines).

Run `npm run test:coverage` to verify.
