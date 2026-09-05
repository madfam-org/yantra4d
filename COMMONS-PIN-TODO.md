# TODO before this PR can merge: swap the commons pin

**This branch is verified against a STAND-IN of the commons, not the real repo.**

`.gitmodules` already carries the final URL —
`https://github.com/madfam-org/solid-hyperobjects.git` — and does not change.
The only thing that must change is the **pin sha**.

| | |
| :-- | :-- |
| Current pin | `d4a4ea3d9501c784ca22ba27d3d665046cbac93c` |
| What it is | a local stand-in built by lane L3: the 500 cartridge trees from this checkout's own `projects/` at `cc99c57d`, minus `tablaco`, `tablaco-v2` and `cq-hyperobject-test`, committed as one repo with each cartridge at its root |
| Why a stand-in | when L3 reached this step, lane L1's `solid-hyperobjects` had 500 directories but only 466 `project.json` — the 34 absorbed satellite cartridges were still gitlinks awaiting their history rewrite. Pinning that would have verified against an incomplete commons |
| Verified equivalent | the stand-in reproduces today's catalog exactly: 500 cartridges / 486 with CDG interfaces / 500 with a commons licence / 21 dual-engine, and every `--check` gate passes over it |

## The swap

```bash
git submodule set-url projects https://github.com/madfam-org/solid-hyperobjects.git  # already set
git config --unset submodule.projects.url        # drop L3's local stand-in override
git submodule sync projects
rm -rf projects .git/modules/projects
git submodule update --init projects
git -C projects log --oneline -1                 # record the real pin

# regenerate everything derived from the manifests, then re-run the gates
python3 scripts/qa/sync_fallback_manifest.py
python3 scripts/qa/generate_commons_catalog.py
python3 scripts/qa/derive_mating_candidates.py
python3 scripts/qa/value_extraction_audit.py --write
node   scripts/dev/generate-landing-projects.mjs

python3 scripts/qa/validate_manifests.py
python3 scripts/qa/generate_commons_catalog.py --check
python3 scripts/qa/check_licenses.py --strict-all
python3 scripts/qa/derive_mating_candidates.py --check
python3 scripts/qa/value_extraction_audit.py --check
node   scripts/dev/generate-landing-projects.mjs --check

git add projects && git commit -m "chore(commons): pin solid-hyperobjects at <sha>"
```

**Expect the counts to move** if the real commons differs from this checkout's
`projects/` — that is the point of re-running the generators, and any diff in
`docs/commons-catalog.json` / `COMMONS.md` / the landing gallery is the real
answer, not drift.

**Delete this file in the same commit as the swap.**
