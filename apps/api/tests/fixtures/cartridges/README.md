# Engine test cartridges

Cartridges that exist to exercise the render engines, **not** to be published.
They are vendored here rather than mounted under a cartridge root, so they are
never discovered by `ManifestService.discover_projects()`, never served by
`/api/projects`, and never counted in the commons.

A test that needs one points a cartridge root at this directory (or at one
cartridge inside it) — see `tests/unit/test_cq_hyperobject_fixture.py`.

## `cq-hyperobject-test`

A CadQuery-only cartridge (`box.py` + `box.step`): a parametric box carrying
hyperobject metadata. Vendored from `madfam-org/cq-hyperobject-test` at
`c970dbc` when RFC 0038 P2 made `projects/` a single submodule of the public
commons. It was never a commons object — the catalog and the licence audit have
always excluded it as `"engine test fixture, not a Commons object"` — and its
upstream repo is archived and therefore read-only, so there was nothing to
absorb into `solid-hyperobjects` and nothing left to track it from.

Its `.github/workflows/ci.yml` was dropped in the move: it is no longer a repo
of its own, and this tree is covered by the platform's own CI.

Before P2 it sat in `projects/`, which is why the API served one project more
than the commons held (501 over 500 at the time). It no longer does: **the API
serves exactly the commons count, 495 today**, plus whatever the operator mounts
under `private-projects/`.
