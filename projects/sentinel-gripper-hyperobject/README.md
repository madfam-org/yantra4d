# Sentinel Soft Gripper

> _A physics-aware, generatively optimizable, multi-material robotic end-effector. The Crown Demo of the Yantra4D platform._

---

## Overview

The **Sentinel Soft Gripper** is a parametric, print-in-place robotic manipulator that fuses compliant mechanism design, multi-material 3D printing, and a physics pipeline into a single unified hyperobject. (Solver execution is not yet real — see the status note below.)

Unlike conventional rigid grippers that require servo motors and metal bearings, the Sentinel uses **V-Notch living flexures** — ultra-thin geometry cross-sections that bend elastically under actuation force. The design is inspired by the bio-mechanical architecture of cephalopod tentacles: proximal rigidity transitioning into distal compliance.

### The Four Structural Zones

| Part | Material | Mode | Role |
|---|---|---|---|
| `housing` | PETG / Rigid | 0 | ISO 9409-1 wrist flange with 6-bolt mounting pattern and tendon routing channels |
| `skeleton` | PETG / Rigid | 0 | Organic proximal + distal phalanges with weight-reduction cutouts and lofted fingertips |
| `flexure` | TPU / Compliant | 1 | V-Notch living hinges that actuate via elastic bending — no bearings, no screws |
| `grip_pad` | TPU / Compliant | 1 | Ribbed friction pads on inner distal face — increases contact surface area and prevents slip |

---

## Platform Integration

This cartridge is purpose-built to exercise the **Yantra4D physics pipeline**. Note that solver execution is mocked today: `apps/api/tasks/simulation_tasks.py` generates the PPF script but never runs it, and the stress endpoint returns a labeled geometry proxy (`stress_proxy_v1`), not a structural solve. What follows describes the intended loop:

### 1. Multi-Material IDEX Configuration
Select TPU Shore A hardness for the flexible zones and PETG for the rigid skeleton. Yantra4D automatically applies material compensation (shrinkage, clearance fits) to guarantee the assembly fits together post-print.

### 2. Kinematic Actuation Timeline
Drag the **Actuation Slider** in the Studio Viewer to simulate tendon-driven finger closure. The three fingers sweep inward −40° about the wrist knuckle, replicating the closing motion of a power grasp.

### 3. FEA Stress Heatmap (Phase 4)
Click **"Show Stress Map (Fast)"** to project a geometry-derived stress proxy onto the mesh vertices. The heaviest-load zones show at the V-Notch waist — where a real solver would concentrate its attention.

### 4. AI Topology Optimization (Phase 6 — Crown Feature)
Click **"AI Topo Optimization"** to launch the generative optimization loop. The backend will:
1. Sweep `flexure_thickness` from `0.4mm` up through `2.5mm`
2. For each iteration, call the PPF contact solver (roadmap — today the optimizer is a deterministic heuristic)
3. Evaluate the resulting maximum Von Mises stress (`max-sigma`)
4. Return the thinnest flexure that survives the target grip force
5. **Auto-apply the winning parameters** to your Studio — the geometry will visually snap into the optimal form!

---

## Parameters

| ID | Type | Range | Description |
|---|---|---|---|
| `finger_count` | Select | 2, 3, 4 | Radial finger symmetry |
| `finger_length` | Slider | 40–120mm | Total phalanx length tip-to-knuckle |
| `base_radius` | Slider | 25–70mm | ISO 9409 wrist interface radius |
| `flexure_thickness` | Slider | 0.4–3.0mm | **Primary optimization target** — V-Notch waist dimension |

---

## Presets

| Preset | Fingers | Length | Use Case |
|---|---|---|---|
| `precision_3f` | 3 | 65mm | General purpose precision grasping |
| `heavy_duty_4f` | 4 | 90mm | High-payload or large object grasping |
| `ultralight_2f` | 2 | 50mm | Parallel jaw, delicate handling |

---

## Print Guidelines

- **Rigid parts** (`housing`, `skeleton`): PETG at 0.2mm layer height, 3 perimeters, 20% gyroid infill
- **Flexible parts** (`flexure`, `grip_pad`): TPU 95A at 0.15mm layer height, 100% solid infill — the flexure waist is too thin for sparse infill
- **Assembly**: Print-in-place if clearances are set correctly. Otherwise, press-fit the TPU flexures into the phalanx sockets after printing.

---

## Physics Lineage

| Source | Contribution |
|---|---|
| [Festo Bionic Cobot](https://www.festo.com/e/en/e/bionic-cobot-14316/) | Bio-inspired 3-finger tendon-driven compliant topology |
| [RBO Hand 2 (TU Berlin)](https://www.robotics.tu-berlin.de/menue/research/projects/rbo_hand/) | Material-embedded compliance — no discrete joints |
| [PPF Contact Solver (ZOZO / SIGGRAPH 2024)](https://github.com/st-tech/ppf-contact-solver) | GPU-accelerated FEM contact physics for optimization |

---

## License

**CERN-OHL-W-2.0** — Open Hardware, Share Alike  
Official configurator and visualizer: [Yantra4D](https://yantra4d.com)
