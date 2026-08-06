# Parametric Pipe Fitting

A slip-fit **coupler**, **elbow**, or **tee** generated with **CadQuery** (B-Rep)
for repairing PVC and poly pipe. Each fitting is a hollow socket that slides
**over** the pipe outer diameter (slip fit): the bore is the pipe OD plus a
printable clearance, and the fitting wall wraps it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Coupler** | `coupler` | Straight splice — two slip sockets, one through-bore, optional central stop ring. |
| **Elbow** | `elbow` | Two sockets meeting at `elbow_angle` over a filleted corner hub. |
| **Tee (3-way)** | `tee` | Straight run plus a 90° branch socket; cross-shaped fluid channel. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on, so every
mode renders its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pipe Size | `pipe_size` | 3/4in | Nominal PVC (1/2" / 3/4" / 1") or Custom. |
| Pipe Size | `pipe_od` | 26.7 mm | Measured OD, used when size = Custom. |
| Socket & Fit | `wall` | 3.0 mm | Fitting wall thickness. |
| Socket & Fit | `socket_depth` | 22.0 mm | Pipe engagement depth per socket. |
| Socket & Fit | `clearance` | 0.4 mm | Per-side slip gap over the pipe OD. |
| Socket & Fit | `stop_ring` | on | Internal shoulder for repeatable seating. |
| Fitting Shape | `elbow_angle` | 90° | Bend angle (elbow mode). |

## Presets

- **1/2" Repair Coupler** — thin-wall straight splice for 1/2" PVC.
- **3/4" 90° Elbow** — the everyday irrigation/plumbing corner.
- **1" Tee** — 3-way branch with a deeper socket.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Pipe Slip Socket** (`socket`, PVC sched nominal) — the slip-fit geometry that
    mates the fitting to a pipe, defined by `pipe_od` / `pipe_size`, `wall`,
    `socket_depth`, `clearance`. Any fitting built at the same nominal size +
    clearance interchanges on the same pipe run.
- **Material awareness:** `clearance` is exposed so the slip fit can be tuned per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** on-demand plumbing repair — a printed slip fitting splices a
  broken run in minutes where the hardware store is far or the part is out of stock.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Sockets are built from one shared `pipe_socket()` helper; stubs overlap into a
  solid hub before the through-channel is bored, so all three fittings export
  **watertight**. The elbow uses a spherical corner hub to fuse its legs volumetrically.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
