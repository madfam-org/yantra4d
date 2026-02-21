// Yantra4D Gear Reducer — Full Assembly
// Uses BOSL2 gears library for parametric spur gear generation
//
// Parameters injected by Yantra4D platform via -D flags

include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/gears.scad>

// --- Parameters (overridden by platform) ---
input_teeth = 12;
output_teeth = 36;
module_size = 1.5;
gear_thickness = 8;
shaft_diameter = 5;
bore_diameter = 5;
wall_thickness = 3;
pressure_angle = 20;
fn = 0;
render_mode = 0;

// --- Derived values ---
$fn = fn > 0 ? fn : 48;
input_pd = pitch_radius(mod=module_size, teeth=input_teeth) * 2;
output_pd = pitch_radius(mod=module_size, teeth=output_teeth) * 2;
center_distance = (input_pd + output_pd) / 2;
clearance = 0.4;
bearing_od = 22;  // 608ZZ outer diameter
bearing_id = 8;   // 608ZZ inner diameter
bearing_h = 7;    // 608ZZ height

housing_width = output_pd + wall_thickness * 2 + 10;
housing_depth = center_distance + output_pd / 2 + wall_thickness * 2 + 10;
housing_height = gear_thickness + bearing_h * 2 + wall_thickness * 2;

module input_gear() {
    spur_gear(mod=module_size, teeth=input_teeth, thickness=gear_thickness,
              shaft_diam=bore_diameter, pressure_angle=pressure_angle);
}

module output_gear() {
    spur_gear(mod=module_size, teeth=output_teeth, thickness=gear_thickness,
              shaft_diam=bore_diameter, pressure_angle=pressure_angle);
}

module shaft_part() {
    cylinder(d=shaft_diameter, h=housing_height - wall_thickness, $fn=$fn);
}

module housing_half(top=false) {
    half_h = housing_height / 2;
    difference() {
        // Outer shell
        translate([-housing_width/2, -output_pd/2 - wall_thickness, 0])
            cube([housing_width, housing_depth, half_h]);

        // Input shaft bore
        translate([0, 0, -1])
            cylinder(d=bearing_od + clearance, h=bearing_h + 1, $fn=$fn);

        // Output shaft bore
        translate([center_distance, 0, -1])
            cylinder(d=bearing_od + clearance, h=bearing_h + 1, $fn=$fn);

        // Gear cavity
        translate([0, 0, bearing_h])
            hull() {
                cylinder(d=input_pd + module_size * 4 + clearance * 2, h=half_h, $fn=$fn);
                translate([center_distance, 0, 0])
                    cylinder(d=output_pd + module_size * 4 + clearance * 2, h=half_h, $fn=$fn);
            }

        // Bolt holes (4 corners)
        for (x = [-housing_width/2 + 5, housing_width/2 - 5])
            for (y = [-output_pd/2 - wall_thickness + 5, -output_pd/2 - wall_thickness + housing_depth - 5])
                translate([x, y, -1])
                    cylinder(d=3.2, h=half_h + 2, $fn=24);
    }
}

// --- Render mode dispatch ---
if (render_mode == 0) {
    // Housing bottom
    housing_half(top=false);
} else if (render_mode == 1) {
    // Housing top (mirrored)
    mirror([0, 0, 1]) housing_half(top=true);
} else if (render_mode == 2) {
    // Input gear
    input_gear();
} else if (render_mode == 3) {
    // Output gear
    output_gear();
} else if (render_mode == 4) {
    // Shaft
    shaft_part();
}
