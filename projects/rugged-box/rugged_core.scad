// ============================================================================
// rugged_core.scad — Native BOSL2 Rugged Box Core
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

include <../../libs/BOSL2/std.scad>

// --- Parameters ---
// (Defaults fall back to expected Yantra4D injected vars)
internalBoxWidthXDflt = 100;
internalBoxLengthYDflt = 60;
internalBoxTopHeightZDflt = 20;
internalBoxBottomHeightZDflt = 20;
wallWidthDflt = 3.0;
chamferRadiusDflt = 4;
gasketSlotWidth = 2.2;
gasketSlotDepth = 2.2;
rimWidthMm = 2;
rimHeightMm = 3;
numberOfHinges = 2;
hingeTotalWidthMm = 25;
numberOfLatches = 2;
latchSupportTotalWidth = 25;

// Fallbacks for injected variables
_inX = is_undef(internalBoxWidthXMm) ? internalBoxWidthXDflt : internalBoxWidthXMm;
_inY = is_undef(internalboxLengthYMm) ? internalBoxLengthYDflt : internalboxLengthYMm;
_topZ = is_undef(internalBoxTopHeightZMm) ? internalBoxTopHeightZDflt : internalBoxTopHeightZMm;
_botZ = is_undef(internalboxBottomHeightZMm) ? internalBoxBottomHeightZDflt : internalboxBottomHeightZMm;
_wall = is_undef(boxWallWidthMm) ? wallWidthDflt : boxWallWidthMm;
_chamf = is_undef(boxChamferRadiusMm) ? chamferRadiusDflt : boxChamferRadiusMm;

// Outer dimensions
_outX = _inX + 2 * _wall;
_outY = _inY + 2 * _wall;

$fn = 64;

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

module rugged_bottom() {
  difference() {
    // Outer body
    cuboid([_outX, _outY, _botZ + _wall], chamfer=_chamf, edges=["Z", BOTTOM], anchor=BOTTOM);
    // Inner cavity
    up(_wall) cuboid([_inX, _inY, _botZ + 1], anchor=BOTTOM);

    // Gasket groove / Rim indent
    up(_botZ + _wall - gasketSlotDepth + 0.01)
      difference() {
        cuboid([_outX - _wall, _outY - _wall, gasketSlotDepth], anchor=BOTTOM);
        cuboid([_outX - _wall - rimWidthMm * 2, _outY - _wall - rimWidthMm * 2, gasketSlotDepth + 1], anchor=BOTTOM);
      }
  }

  // Add hinges (back)
  for (i = [1:numberOfHinges]) {
    _hx = -_outX / 2 + (_outX / (numberOfHinges + 1)) * i;
    translate([_hx, _outY / 2, _botZ + _wall - 5])
      xrot(90) cylinder(h=hingeTotalWidthMm, r=4, center=true);
    translate([_hx, _outY / 2, 0])
      cuboid([hingeTotalWidthMm, 5, _botZ + _wall - 5], anchor=BOTTOM + BACK);
  }

  // Add latch anchors (front)
  for (i = [1:numberOfLatches]) {
    _lx = -_outX / 2 + (_outX / (numberOfLatches + 1)) * i;
    translate([_lx, -_outY / 2, _botZ + _wall - 8])
      cuboid([latchSupportTotalWidth, _wall + 2, 5], anchor=BOTTOM + FRONT);
  }
}

module rugged_top() {
  difference() {
    // Outer body
    cuboid([_outX, _outY, _topZ + _wall], chamfer=_chamf, edges=["Z", TOP], anchor=BOTTOM);
    // Inner cavity
    down(0.01) cuboid([_inX, _inY, _topZ], anchor=BOTTOM);
  }

  // Rim insert (fits into bottom groove)
  down(rimHeightMm)
    difference() {
      cuboid([_outX - _wall - 0.5, _outY - _wall - 0.5, rimHeightMm], anchor=BOTTOM);
      down(0.01) cuboid([_outX - _wall - rimWidthMm * 2 + 0.5, _outY - _wall - rimWidthMm * 2 + 0.5, rimHeightMm + 1], anchor=BOTTOM);
    }

  // Add hinges (back)
  for (i = [1:numberOfHinges]) {
    _hx = -_outX / 2 + (_outX / (numberOfHinges + 1)) * i;
    translate([_hx, _outY / 2, 5])
      xrot(90) cylinder(h=hingeTotalWidthMm - 1, r=3.5, center=true);
    translate([_hx, _outY / 2, 5])
      cuboid([hingeTotalWidthMm - 1, 5, _topZ + _wall - 5], anchor=BOTTOM + BACK);
  }

  // Add latch clips (front)
  for (i = [1:numberOfLatches]) {
    _lx = -_outX / 2 + (_outX / (numberOfLatches + 1)) * i;
    translate([_lx, -_outY / 2, 8])
      cuboid([latchSupportTotalWidth, _wall + 2, 5], anchor=BOTTOM + FRONT);
  }
}

module rugged_latches() {
  for (i = [1:numberOfLatches]) {
    translate([0, i * 15, 0]) {
      difference() {
        cuboid([latchSupportTotalWidth, 20, 4], anchor=BOTTOM);
        // Hole for latch anchor
        cuboid([latchSupportTotalWidth - 4, 10, 6], anchor=BOTTOM);
      }
    }
  }
}

module rugged_gasket() {
  difference() {
    cuboid([_outX - _wall - 0.5, _outY - _wall - 0.5, gasketSlotDepth], anchor=BOTTOM);
    cuboid([_outX - _wall - rimWidthMm * 2 + 0.5, _outY - _wall - rimWidthMm * 2 + 0.5, gasketSlotDepth + 1], anchor=BOTTOM);
  }
}

module rugged_feet() {
  for (i = [-1:2:1])
    for (j = [-1:2:1]) {
      translate([i * (_outX / 2 - 10), j * (_outY / 2 - 10), 0])
        cylinder(r=5, h=3, anchor=BOTTOM);
    }
}

// ---------------------------------------------------------------------------
// Render Dispatch
// ---------------------------------------------------------------------------
if (render_part == "bottom") {
  rugged_bottom();
} else if (render_part == "top") {
  // Flip top so it prints flat
  xrot(180) rugged_top();
} else if (render_part == "latches") {
  rugged_latches();
} else if (render_part == "gasket") {
  rugged_gasket();
} else if (render_part == "feet") {
  rugged_feet();
} else if (render_part == "complete") {
  translate([0, -_outY / 2 - 20, 0]) rugged_bottom();
  translate([0, _outY / 2 + 20, 0]) xrot(180) rugged_top();
  translate([_outX / 2 + 20, 0, 0]) rugged_latches();
  translate([-_outX / 2 - 20, 0, 0]) rugged_gasket();
} else if (render_part == "closed") {
  rugged_bottom();
  up(_botZ + _wall) rugged_top();
  // Move latches into position for closed view
  for (i = [1:numberOfLatches]) {
    _lx = -_outX / 2 + (_outX / (numberOfLatches + 1)) * i;
    translate([_lx, -_outY / 2 - _wall - 1, _botZ + _wall])
      xrot(90) cuboid([latchSupportTotalWidth, 20, 4], anchor=BOTTOM + FRONT);
  }
}
