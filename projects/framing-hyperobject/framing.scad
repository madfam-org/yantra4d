include <BOSL2/std.scad>
use <profiles/classic.scad>
use <profiles/industrial.scad>
use <mounting/vesa.scad>
use <mounting/standoffs.scad>
use <containers/slabs.scad>
use <containers/capsules.scad>

// --- Parameters (Updated for Exhaustiveness) ---

// [Dimensions]
width = 200; // [50:1000]
height = 250; // [50:1000]
depth = 20; // [10:100]

// [Style]
profile_style = "ogee"; // [ogee, bevel, box, floater, stretcher, seg, snap]
mounting_style = "none"; // [none, vesa_75, vesa_100, french_cleat, standoffs]

// [Components]
mat_width = 50; // [0:200]
glazing_thickness = 2; // [1:6]

// [Container Type]
container_type = "none"; // [none, PSA, BGS, SGC, CGC, Silver Eagle, Small Dollar, ID Badge]

// --- Logic ---

module frame_assembly() {
  path = rect([width, height]);

  // Select Profile Generator
  if (profile_style == "ogee") {
    color("saddlebrown") render_profile(path, "ogee", 30, depth);
  } else if (profile_style == "bevel") {
    color("saddlebrown") render_profile(path, "bevel", 30, depth);
  } else if (profile_style == "box") {
    color("saddlebrown") render_profile(path, "box", 20, depth);
  } else if (profile_style == "stretcher") {
    color("burlywood") render_textile_profile(path, "stretcher", 45, 19);
  } else if (profile_style == "seg") {
    color("silver") render_textile_profile(path, "seg", 20, 20);
  } else if (profile_style == "snap") {
    color("silver") render_industrial_profile(path, "snap", 25, 10);
  }

  // Mounting
  if (mounting_style == "vesa_75") {
    translate([0, 0, -1]) color("dimgray") vesa_pattern("MIS-D 75");
  } else if (mounting_style == "vesa_100") {
    translate([0, 0, -1]) color("dimgray") vesa_pattern("MIS-D 100");
  } else if (mounting_style == "standoffs") {
    color("silver") standoff_set(width - 40, height - 40, 25);
  }

  // Containers
  if (container_type != "none") {
    translate([0, 0, depth / 2]) {
      if (container_type == "PSA" || container_type == "BGS" || container_type == "SGC") {
        color("white", 0.8) slab_void(container_type);
      } else if (container_type == "Silver Eagle" || container_type == "Small Dollar") {
        color("white", 0.5) coin_capsule(container_type);
      } else if (container_type == "ID Badge") {
        color("white", 0.8) id_badge_holder();
      }
    }
  }
}

frame_assembly();
