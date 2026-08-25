# Threaded Insert Jig

A press-fit **alignment jig** for seating brass **heat-set inserts** square and to
a consistent depth with a soldering iron. Generated with **CadQuery** (B-Rep).

Heat-set inserts (CNC-Kitchen / McMaster **IUB-IUC** series) are the de-facto way
to put a reusable **ISO metric machine-screw thread** into a 3D print: you melt a
knurled brass barrel into a moulded boss, and a metric screw then threads into it.
The hard part by hand is keeping the insert perpendicular and stopping it flush —
this jig fixes both.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Iron Guide Block** | `guide_block` | A square guide with a stepped bore: an insert counterbore on top holds the insert coaxial to the iron tip; a narrower screw-shank clearance runs below to a solid floor that sets a repeatable seat depth. |
| **Boss Test Coupon** | `boss_gauge` | A "go / seat-depth" coupon — a printed boss with the recommended moulded-in insert pocket (tapered lead-in + straight knurl-grip zone) so you can dial in boss ID before committing it to a real part. |
| **Press Collar** | `press_collar` | A thick collar that fits over an already-melted insert to press it the last fraction flush and true against a cooling part; a central through bore clears the insert bore and vents the pocket. |

All three modes render a single watertight body (`body_count == 1`).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Insert | `insert_size` | M4 | M3 / M4 / M5 / M6 / M8 (knurl OD 4.0 / 5.6 / 6.4 / 8.0 / 10.0 mm). |
| Fit & Walls | `melt_fit` | 0.15 mm | Per-side undersize of the printed pocket so the hot insert melts into a snug grip. |
| Fit & Walls | `wall` | 4.0 mm | Material thickness around the socket. |
| Sizing | `seat_depth` | 0.3 mm | Flush-seat offset (guide block). |
| Sizing | `block_h` | 14.0 mm | Guide-block height. |
| Sizing | `gauge_boss_h` | 8.0 mm | Test-coupon boss height. |

### Insert stock (nominal knurl OD × barrel length, mm)

| Size | OD | Length | Screw |
| :--- | :--- | :--- | :--- |
| M3 | 4.0 | 5.7 | M3 |
| M4 | 5.6 | 8.1 | M4 |
| M5 | 6.4 | 9.5 | M5 |
| M6 | 8.0 | 12.7 | M6 |
| M8 | 10.0 | 12.7 | M8 |

Values are typical for IUB/IUC brass heat-set stock; verify against your inserts.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interface:** `insert_boss_socket` — a `socket`, standard **M3-M8 insert**.
- **Compatible with:** `fasteners`, `locking-mechanism-hyperobject`. The seated
  insert accepts an ISO metric screw, so parts jigged with this cartridge mate the
  **iso-hex-fastener** metric family through the shared thread standard.
- **License:** CERN-OHL-W-2.0.

## Printing notes

- Print the **guide block** and **press collar** at ≥ 4 perimeters — they take
  side load while the iron is hot.
- The **melt interference** (`melt_fit`) is the single most important dial: too
  little and the insert spins; too much and it will not melt in square. Start at
  0.15 mm/side and refine with the **boss test coupon**.
- PETG and ABS bosses hold heat-set inserts better than PLA (higher glass
  transition), but PLA works for light-duty parts.
