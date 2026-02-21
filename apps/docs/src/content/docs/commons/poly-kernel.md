---
title: Poly-Kernel Parity Rules
description: Understanding the B-Rep vs CSG constraints
---

Yantra4D mandates **Poly-Kernel** parity for any project declaring itself a Hyperobject.

## OpenSCAD (CSG Architecture)
Constructive Solid Geometry relies heavily on rendering tree booleans. By compiling `openscad-wasm`, Yantra4D lets arbitrary OpenSCAD models instantly visualize within the user's browser securely, generating `.gltf` and local `.stl` maps without burning Docker compute power.

## CadQuery (B-Rep Architecture)
CSG output lacks mathematically exact edge coordinates. 

To satisfy the **Hyperobjects Commons**, every feature mapping to a specific `mode` in `project.json` must be flawlessly recreated in python utilizing the CadQuery library.

### Why B-Rep?
A CadQuery Boundary Representation is aware of pure, parameterized surfaces. When we export `.step` artifacts to aerospace/automotive engineering endpoints, we pass them native mathematical boundaries instead of interpolated polygon spheres.

As of Phase 5.2, any Yantra4D project omitting `"cq_file"` fails ecosystem CI validates.
