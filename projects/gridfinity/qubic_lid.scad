// Qubic wrapper — translates scalar params to Gridfinity lid format

include <gridfinity_extended/modules/gridfinity_constants.scad>
use <gridfinity_extended/modules/module_gridfinity_block.scad>
use <gridfinity_extended/modules/module_gridfinity_lid.scad>

// Qubic scalar parameters (overridden by -D flags)
width_units = 2;
depth_units = 1;
lid_include_magnets = true;
lid_efficient_floor = 0.7;
lid_type_id = 0;             // 0=default, 1=flat, 2=halfpitch, 3=efficient
fn = 0;

// Translate scalar ID to lid options string
_lid_types = ["default", "flat", "halfpitch", "efficient"];

$fa = 6; $fs = 0.1; $fn = fn;

set_environment(
  width = [width_units, 0],
  depth = [depth_units, 0],
  render_position = "center",
  help = "disabled")
gridfinity_lid(
  num_x = width_units,
  num_y = depth_units,
  magnetSize = lid_include_magnets ? [6.5, 2.4] : [0,0],
  lidIncludeMagnets = lid_include_magnets,
  lidEfficientFloorThickness = lid_efficient_floor,
  lidOptions = _lid_types[lid_type_id]);
