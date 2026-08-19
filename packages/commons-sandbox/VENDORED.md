# Vendored: madfam-commons-sandbox

This is a **vendored copy** of the shared sandbox security core. The **canonical
source** is Fashion Cabinet: `fashion-cabinet/packages/commons-sandbox/`
(madfam-org/fashion-cabinet). Do **not** hand-edit `src/commons_sandbox/core.py` or
`__init__.py` here — change the canonical source and re-vendor.

Both Yantra4D (`cq_runner`) and Fashion Cabinet (`fc_runner`) execute untrusted
cartridge scripts through this identical restricted-execution core; keeping one
authored source means a sandbox-hardening fix lands once and cannot silently drift
between the two runners.

## Drift guard

`scripts/qa/check_sandbox_sync.py` (a blocking CI lane) asserts the vendored security
core matches the hashes in `sandbox.lock.json`. If Fashion Cabinet updates the core,
this lane goes red until the copy here is refreshed and the lock re-pinned.

## Re-vendoring

```
# from a checkout with both repos side by side:
cp ../fashion-cabinet/packages/commons-sandbox/src/commons_sandbox/*.py \
   packages/commons-sandbox/src/commons_sandbox/
cp ../fashion-cabinet/packages/commons-sandbox/tests/test_core.py \
   packages/commons-sandbox/tests/
python scripts/qa/check_sandbox_sync.py --update   # re-pin sandbox.lock.json
```

Once a shared MADFAM Python registry exists, replace this vendored copy with a plain
`pip` dependency on `madfam-commons-sandbox` and delete the guard.
