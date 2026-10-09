# Publication source acceptance

The [publisher](../../.github/workflows/deploy.yml) starts after the `CI` workflow
completes on main, or from a manual dispatch. Before change detection or image
builds, [the source gate](../../scripts/ci/require_source_ci.py) requires:

- The checkout, publication SHA and current main are identical.
- Automatic triggers came from a main push in this repository and identify that
  same SHA. Pull-request and fork runs cannot authorize a release.
- The exact-source `ci.yml` run completed successfully, including its required
  `ci-success` aggregate. Missing, unreadable, running, failed or cancelled
  evidence refuses publication. Manual dispatch and `force_deploy` obey this gate.

GitHub's [`workflow_run` semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
use the latest default-branch commit as `GITHUB_SHA`; it is not necessarily the
triggering run's source. The gate checks both identities. It reads run metadata
through a read-only token and never consumes triggering-workflow artifacts.

Rejected triggers fail the publisher rather than producing a green skipped run:
a green run can become the next release's change-detection baseline. Accepted
publication still compares against the last successful publisher, carrying all
unreleased changes forward. A digest-only CI completion may start a no-op
publisher, which produces no further commit and therefore no loop.

Immediately before each image-pin push attempt, the publisher fetches main again.
If main moved during the builds, it refuses to pin those images onto a different
source. The signed images may exist in the registry, but publication is incomplete.
Wait for the new main's CI and publish that accepted source; do not bypass the
check or describe a built image as deployed.

The gate establishes source acceptance, not runtime readiness, deployment
availability or geometry correctness. Follow the [render release verification
contract](render-artifact-storage.md#cache-identity-across-releases), inspect the
actual serving images through Enclii and verify the affected user journeys.
[Regression tests](../../scripts/tests/test_require_source_ci.py) cover rejected
source/CI identities and execute the stale-pin guard from the actual workflow.

[Platform overview](../../README.md) · [Compact LLM index](../../llms.txt) ·
[Full LLM map](../../llms-full.txt)
