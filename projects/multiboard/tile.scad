// ============================================================================
// tile.scad — Multiboard Tile (NATIVE)
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).
// 
// Native BOSL2 implementation of the Multiboard 25mm octagonal grid.

include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/threading.scad>

x_cells = 4;
y_cells = 4;
cell_size = 25;
height = 6.4;
fn = 0;
// Note: rendering threads requires higher $fn for smooth exports
$fn = fn > 0 ? fn : 32;

module multiboard_tile_native(xc, yc) {
  w = xc * cell_size;
  h = yc * cell_size;

  // The octagonal chamfer size for the outer boundary
  _chamf = cell_size / 2 * (1 - 1 / sqrt(2)) * 1.5;

  difference() {
    // Main plate (octagonal borders)
    cuboid([w, h, height], chamfer=_chamf, edges="Z", anchor=BOTTOM + LEFT + FRONT);

    // Large threading holes (Center of each 25mm cell)
    for (i = [0:xc - 1]) {
      for (j = [0:yc - 1]) {
        translate([cell_size / 2 + i * cell_size, cell_size / 2 + j * cell_size, -0.5]) {
          // Large threaded hole: M22.5 x 2.5 trapezoidal
          trapezoidal_threaded_rod(
            d=22.5,
            l=height + 1,
            pitch=2.5,
            thread_angle=29,
            internal=true,
            anchor=BOTTOM
          );
        }
      }
    }

    // Small threaded holes (Corners of each 25mm cell)
    for (i = [0:xc]) {
      for (j = [0:yc]) {
        translate([i * cell_size, j * cell_size, -0.5]) {
          // Small threaded hole: M6.07 x 3 trapezoidal
          trapezoidal_threaded_rod(
            d=7.025,
            l=height + 1,
            pitch=3,
            thread_angle=29,
            internal=true,
            anchor=BOTTOM
          );
        }
      }
    }
  }
}

// Generate the tile
multiboard_tile_native(x_cells, y_cells);
