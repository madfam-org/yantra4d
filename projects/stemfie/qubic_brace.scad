// Qubic wrapper — STEMFIE Brace (L-shape via brace_cross)
use <vendor/stemfie/stemfie.scad>

arm_a_units = 3;
arm_b_units = 3;
thickness_units = 1;
holes_enabled = true;
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

// L-shaped brace using library brace_cross module
// brace_cross with 2-element array produces an L/V shape
brace_cross(lengths=[arm_a_units, arm_b_units], h=thickness_units * 0.25);
