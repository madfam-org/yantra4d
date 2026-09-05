# Yantra4D — Landing

Astro marketing site for yantra4d.com, with React islands for the interactive
sections (the 3D carousel and the project gallery).

```bash
npm install
npm run dev       # Astro dev server on http://localhost:4321
npm run build     # Static build to dist/
npm run preview   # Preview the build
npm run lint      # ESLint
npm test          # Vitest
```

## `src/data/projects.ts` is GENERATED — do not edit it by hand

The gallery is driven by `src/data/projects.ts`, which is generated from the
cartridge manifests (`projects/<slug>/project.json`) by
[`scripts/dev/generate-landing-projects.mjs`](../../scripts/dev/generate-landing-projects.mjs)
and committed. Regenerate it with:

```bash
npm run gen:projects        # from apps/landing
```

Two things follow from it being generated rather than maintained:

- **It needs a complete checkout.** The generator refuses to write (exit 2) when
  any public `projects/*` submodule in `.gitmodules` has no `project.json` on
  disk, because a partial checkout is exactly how the committed list went 328
  entries against a 495-cartridge commons. Run
  `git submodule update --init projects/` first. The two `update = none`
  submodules (the client-private `tablaco` pair) are *expected* to be absent and
  never count as an incomplete checkout.
- **Private cartridges are excluded, on both the signals the backend uses** —
  `access_control.view == "private"` in the manifest and the `PRIVATE_PROJECTS`
  env var, the same comma-separated shape the backend Deployment sets. The
  built-in list is a floor, not a default an empty env var can clear.
  `project.unlisted` is untouched: unlisted means "not in API listings but
  reachable by URL", which is not private.

Where it is checked:

| Lane | What it does |
| :-- | :-- |
| `ci.yml` → `manifest-validation` | `--check` fails the PR when the committed file no longer matches the manifests. It is the only job whose checkout is complete enough to judge the file — the `landing` job checks out no submodules at all. |
| `deploy.yml` → `build-landing` | **Regenerates** rather than checks, so the deployed gallery is correct by construction. Fail-closed: no `--allow-partial`, so a bad checkout stops the deploy instead of publishing a truncated commons. |

The committed file is therefore a fallback for local dev and for the
submodule-less landing CI job, not the source of truth.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See the [LICENSE](../../LICENSE) file for more details.
