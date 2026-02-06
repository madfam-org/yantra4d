// Yantra4D wrapper — translates scalar params to Gridfinity cup format
// Scalar parameters are overridden by -D flags from Yantra4D API

include <gridfinity_extended/modules/gridfinity_constants.scad>
use <gridfinity_extended/modules/module_gridfinity_cup.scad>
use <gridfinity_extended/modules/module_gridfinity_block.scad>

// Yantra4D scalar parameters (overridden by -D flags)
width_units = 2;
depth_units = 1;
height_units = 3;
cup_wall_thickness = 0;       // 0 = auto
cup_floor_thickness = 0.7;
vertical_chambers = 1;
horizontal_chambers = 1;
enable_magnets = false;
enable_screws = false;
fingerslide_enabled = false;
label_enabled = false;
wallpattern_enabled = false;
lip_style_id = 0;            // 0=normal, 1=reduced, 2=minimum, 3=none
wallpattern_style_id = 0;    // 0=hexgrid, 1=grid, 2=voronoi, 3=brick
headroom = 0.8;
efficient_floor_id = 0;      // 0=off, 1=on, 2=rounded, 3=smooth
sliding_lid_enabled = false;
tapered_corner_id = 0;       // 0=none, 1=rounded, 2=chamfered
tapered_corner_size = 10;
fn = 0;

// Translate scalar IDs to Gridfinity string enums
_lip_styles = ["normal", "reduced", "minimum", "none"];
_wp_styles = ["hexgrid", "grid", "voronoi", "brick"];
_tapered_styles = ["none", "rounded", "chamfered"];

$fa = 6; $fs = 0.4; $fn = fn;

set_environment(
  width = [width_units, 0],
  depth = [depth_units, 0],
  height = [height_units, 0],
  render_position = "center",
  help = "disabled",
  pitch = [42,42,7],
  clearance = [0.5, 0.5, 0])
gridfinity_cup(
  wall_thickness = cup_wall_thickness,
  headroom = headroom,
  vertical_chambers = ChamberSettings(
    chambers_count = vertical_chambers),
  horizontal_chambers = ChamberSettings(
    chambers_count = horizontal_chambers),
  cupBase_settings = CupBaseSettings(
    magnetSize = enable_magnets ? [6.5, 2.4] : [0,0],
    screwSize = enable_screws ? [3, 6] : [0,0],
    floorThickness = cup_floor_thickness,
    efficientFloor = efficient_floor_id),
  lip_settings = LipSettings(
    lipStyle = _lip_styles[lip_style_id]),
  finger_slide_settings = FingerSlideSettings(
    type = fingerslide_enabled ? "rounded" : "none",
    radius = -3,
    walls = [1,0,0,0],
    lip_aligned = true),
  label_settings = LabelSettings(
    labelStyle = label_enabled ? "normal" : "disabled"),
  wall_pattern_settings = PatternSettings(
    patternEnabled = wallpattern_enabled,
    patternStyle = _wp_styles[wallpattern_style_id],
    patternFill = "none",
    patternCellSize = [10,10],
    patternHoleSides = 6,
    patternStrength = 2,
    patternHoleRadius = 0.5),
  sliding_lid_enabled = sliding_lid_enabled,
  tapered_corner = _tapered_styles[tapered_corner_id],
  tapered_corner_size = tapered_corner_size);
