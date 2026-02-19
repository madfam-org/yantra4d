// ============================================================================
// holder.scad — AOCL Single Substrate Holder
// ============================================================================
// AOCL Spec: Flat rectangular piece holding one 1"×1" substrate in its center.
//
// Exterior: 5 in × 3 in × 0.59 in (127 × 76.2 × 14.986 mm → 15 mm)
// Central pocket: 1"×1" (25.4×25.4mm) through-hole, perfectly centred.
//
// Parameters are injected by the Yantra4D platform via OpenSCAD -D flag.
// ============================================================================

use <vendor/microscope-slide-holder/slide_lib.scad>
include <../../libs/BOSL2/std.scad>

// ---------------------------------------------------------------------------
// Parameters (injected by platform via -D)
// ---------------------------------------------------------------------------

// Substrate
substrate_size = 25.4; // 1 inch square substrate (mm) — fixed per AOCL spec

// Tolerances
tolerance_xy = 0.4; // Pocket XY clearance (mm) — FDM compensation
tolerance_z = 0.2; // Not used for through-hole, reserved

// Structure
wall_thickness = 2.0; // Outer wall reference thickness (mm)

// Features
label_area = 1; // 1 = debossed label recess on bottom face
chamfer_pocket = 1; // 1 = chamfered lead-in on pocket entry edges

// Quality
fn = 0; // $fn resolution; 0 = auto (32)

// ---------------------------------------------------------------------------
// Resolution
// ---------------------------------------------------------------------------
$fn = fn > 0 ? fn : 32;

// ---------------------------------------------------------------------------
// Fixed AOCL Dimensions (not user-adjustable per spec)
// ---------------------------------------------------------------------------
_length = 5 * 25.4; // 127.0 mm
_width = 3 * 25.4; // 76.2 mm
_thickness = 15.0; // 0.59 in ≈ 14.986 mm → 15 mm

// Pocket = substrate + XY clearance on each side
_pocket_size = substrate_size + tolerance_xy;
_chamfer_size = 1.5; // 45° chamfer at pocket top entry (guides substrate in)

// ---------------------------------------------------------------------------
// Label recess geometry
// ---------------------------------------------------------------------------
_label_w = 40;
_label_h = 15;
_label_d = 0.4;

// ---------------------------------------------------------------------------
// Holder body
// ---------------------------------------------------------------------------
module holder_body() {
  diff("pocket label") {
    // Outer shell — flat rectangular plate
    cuboid(
      [_length, _width, _thickness],
      rounding=1.5,
      edges=[TOP, BOTTOM],
      anchor=CENTER
    );

    // Central through-pocket (substrate opening)
    tag("pocket") {
      // Through bore
      cuboid([_pocket_size, _pocket_size, _thickness + 2], anchor=CENTER);

      // Chamfered lead-in on top entry face (AM-friendly funnel)
      if (chamfer_pocket == 1) {
        up(_thickness / 2)
          chamfer_mask_z(
            l=_pocket_size * 2,
            r=_chamfer_size,
            square=true,
            anchor=CENTER
          );
      }
    }

    // Debossed label recess on bottom face
    if (label_area == 1) {
      tag("label")
        down(_thickness / 2 - _label_d)
          cuboid([_label_w, _label_h, _label_d + 0.1], anchor=BOTTOM);
    }
  }
}

holder_body();
