// Qubic wrapper — Multiboard Tile
// Overrides customizer variables before include

x_cells = 4;
y_cells = 4;
cell_size = 25;
height = 6.4;
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

include <vendor/multiboard-parametric/multiboard_base.scad>
