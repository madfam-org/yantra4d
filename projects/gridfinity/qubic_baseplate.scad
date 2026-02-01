// Qubic wrapper — translates scalar params to Gridfinity baseplate format

include <gridfinity_extended/modules/gridfinity_constants.scad>
use <gridfinity_extended/modules/module_gridfinity_block.scad>
use <gridfinity_extended/modules/module_gridfinity_baseplate.scad>

// Qubic scalar parameters (overridden by -D flags)
width_units = 2;
depth_units = 2;
bp_enable_magnets = false;
bp_enable_screws = false;
bp_corner_radius = 3.75;
bp_reduced_wall = -1;
bp_reduced_wall_taper = false;
fn = 0;

$fa = 6; $fs = 0.1; $fn = fn;

set_environment(
  width = [width_units, 0],
  depth = [depth_units, 0],
  render_position = "center",
  help = "disabled",
  pitch = [42,42,7])
gridfinity_baseplate(
  num_x = width_units,
  num_y = depth_units,
  plate_corner_radius = bp_corner_radius,
  magnetSize = bp_enable_magnets ? [6.5, 2.4] : [0,0],
  reducedWallHeight = bp_reduced_wall,
  reduceWallTaper = bp_reduced_wall_taper,
  cornerScrewEnabled = bp_enable_screws);
