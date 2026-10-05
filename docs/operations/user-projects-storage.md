# User projects storage

**What lives here:** every cartridge a user creates, which means forks, GitHub
imports, onboarded cartridges and AI-synthesised cartridges. They are stored in
their own root, `USER_PROJECTS_DIR`, apart from the cartridges that ship with a
release.

| Root | Config | Content | Writable? |
|---|---|---|---|
| Commons | `PROJECTS_DIR` (`/app/projects`) | The `projects` submodule, baked into the image | No. It is release content |
| Private | `PRIVATE_PROJECTS_DIR` (`/app/private-projects`) | Client-private cartridges, baked into the image | No. It is release content |
| **User** | **`USER_PROJECTS_DIR` (`/app/user-projects`)** | **Forks, imports, onboarding, AI synthesis** | **Yes. It is a persistent volume** |

Locally, `USER_PROJECTS_DIR` defaults to a gitignored `user-projects/` at the
repo root, and the docker-compose files mount a named `user_projects` volume.

## How the API uses it

The code is in `apps/api/utils/project_resolver.py`.

- **Resolution order:** commons, then private, then user. The user root comes
  **last**, so a user cartridge can never shadow a curated one. The manifest
  service follows the same order through `Config.CARTRIDGES_DIRS`, where the
  user root is the last entry.
- **Writes:** `project_write_root()` returns the user root, and nothing else
  creates cartridges. Edits to an existing cartridge are written wherever it
  resolves. The editor's write routes allow only forks and imports.
- **Slug uniqueness:** `slug_in_use()` checks every root, including the extra
  `CARTRIDGES_DIRS`, before any fork, import, onboarding or synthesis, so a new
  slug never collides.
- **A release can still collide.** If a later commons release adds a slug that
  a user already took, the commons cartridge answers and the user's copy stops
  resolving. The copy is never deleted. The API logs such slugs at startup:

  `User cartridges hidden by a curated cartridge with the same slug (rename them in /app/user-projects): <slugs>`

  To fix it, rename the directory on the volume (see *Maintenance*).
- **Search paths:** the user root is **not** on `OPENSCADPATH` or the CadQuery
  `PYTHONPATH`. Those paths name directories by slug, and user slugs are chosen
  by users, so only curated roots are trusted there. A fork still renders,
  because its own entry file is executed by path.
- **The render worker** reads forks from the same path. Both containers must
  mount the volume at the same `mountPath`, because a render job carries the
  absolute source path.

## Kubernetes

The PVC is `k8s/production/yantra4d-user-projects-pvc.yaml`. It is mounted
read-write at `/app/user-projects` in **both** containers of the
`yantra4d-backend` pod (`backend` and `render-worker`).

- **Access mode:** `ReadWriteOnce`. Both containers are in one pod, and
  therefore on one node, so RWO is enough. Keep the Deployment's `Recreate`
  strategy: a rolling update would start a second pod that can't attach the
  volume while the first one holds it.
- **Root filesystem:** `readOnlyRootFilesystem` stays `true`. The volume is the
  only new writable path.
- **Ownership:** the pod runs as UID 1001 with `fsGroup: 1001`. The volume is
  group-writable for that group, so the non-root process can create cartridges.
- **Size:** 2 Gi, a convention rather than a measured limit. The whole commons
  is about 25 MB and its largest cartridge about 2.2 MB, so 2 Gi holds roughly a
  thousand forks of the largest cartridge. A GitHub import is a full clone with
  history, so imports cost more. There are no per-user quotas.
- **Growing it:** raise `spec.resources.requests.storage` in the manifest. The
  storage class supports online expansion. A PVC can't shrink.
- **Storage class:** `longhorn`, set explicitly because the backup below
  depends on it.

## Backup

The volume is covered by the cluster's **Longhorn recurring backup jobs**: the
`default` job group, with daily snapshots and daily and weekly backups to
off-cluster object storage. The PVC carries the labels that place its volume
in that group:

- `recurring-job.longhorn.io/source: enabled`, which makes Longhorn copy
  recurring-job labels from the PVC to the volume;
- `recurring-job-group.longhorn.io/default: enabled`.

No application credentials are involved: the backup target and its credentials
belong to the cluster. **Check after the first rollout** that the volume is in
the group and that a backup exists:

```bash
kubectl -n yantra4d get pvc yantra4d-user-projects -o jsonpath='{.spec.volumeName}{"\n"}'
kubectl -n longhorn-system get volumes.longhorn.io <volume-name> --show-labels
kubectl -n longhorn-system get backups.longhorn.io -l backup-volume=<volume-name>
```

## Restore

Restore into a **new** volume, then copy back what is needed. This works for a
single cartridge or the whole root, and the live PVC (which GitOps owns) stays
untouched.

1. In the Longhorn UI, go to **Backup**, open the volume's backup, choose
   **Restore**, and name it `yantra4d-user-projects-restore`.
2. On the restored volume, use **Create PV/PVC** with namespace `yantra4d` and
   PVC name `yantra4d-user-projects-restore`.
3. Start a one-off pod that runs as UID 1001 with `fsGroup: 1001` and mounts
   both claims: the live claim at `/live` and the restored claim at
   `/restore`. Copy what you need, preserving modes:
   `cp -a /restore/<slug> /live/` for one cartridge, or
   `cp -a /restore/. /live/` for everything.
4. Delete the one-off pod, the restore PVC and the restored volume.

The API sees restored cartridges on the next request. The catalog index
rebuilds when the directory changes.

To restore the whole volume in place instead, scale the Deployment to zero
first. Pause GitOps auto-sync so it is not scaled straight back up, then do
the copy and scale back up.

## Maintenance

- **Rename a shadowed cartridge:** use the same one-off pod pattern, or
  `kubectl exec` into `backend`:
  `mv /app/user-projects/<slug> /app/user-projects/<new-slug>`.
- **Usage:** `kubectl -n yantra4d exec deploy/yantra4d-backend -c backend -- du -sh /app/user-projects`
