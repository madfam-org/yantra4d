// Qubic wrapper — STEMFIE Beam
use <vendor/stemfie/stemfie.scad>

length_units = 4;
width_units = 1;
height_units = 1;
holes_x = true;
holes_y = true;
holes_z = true;
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

beam_block(size=[length_units, width_units, height_units],
           holes=[holes_x, holes_y, holes_z],
           center=true);
