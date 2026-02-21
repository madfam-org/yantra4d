// =============================================================================
// Yantra4D Core OpenSCAD Library
// Wrappers for BOSL2 standard usage across all projects.
// =============================================================================

include <BOSL2/std.scad>
include <BOSL2/threading.scad>

module y4d_standard_thread(d, p, l, internal = false, anchor = CENTER) {
  // A standard wrapper around BOSL2's threading to enforce Yantra4D defaults
  if (internal) {
    threaded_nut(nutwidth=d + 5, id=d, h=l, pitch=p, ibevel=true, $fa=2, $fs=0.5, anchor=anchor);
  } else {
    threaded_rod(d=d, l=l, pitch=p, end_len1=0, end_len2=0, internal=false, $fa=2, $fs=0.5, anchor=anchor);
  }
}

module y4d_french_cleat(length = 100, height = 30, depth = 15, angle = 45) {
  polygon_points = [
    [0, 0],
    [depth, 0],
    [depth, height],
    [depth - (height * tan(angle)), height],
    [0, 0],
  ];
  translate([-length / 2, -height / 2, 0])
    rotate([90, 0, 90])
      linear_extrude(height=length) {
        polygon(points=polygon_points);
      }
}
