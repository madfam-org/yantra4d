// Yantra4D — SCARA Robotics Robot (BOSL2)
include <../../libs/BOSL2/std.scad>

$fn = 128;

// Parameters (injected by Yantra4D)
num_teeth = 100;      // Circular Spline teeth
gear_module = 0.5;    // Gear module
bore_diameter = 5;    // Input shaft bore
render_mode = 0;      // 0=all, 1=Wave Generator, 2=Flexspline, 3=Circular Spline

// Derived
flex_teeth = num_teeth - 2;
pitch_diam = gear_module * num_teeth;
flex_pitch_diam = gear_module * flex_teeth;
thickness = 10;
tooth_w = gear_module * 0.8;
tooth_h = gear_module * 4.0; // 2.0mm depth

module component_teeth(n, r, w, h, t) {
    for (i = [0:n-1]) {
        angle = i * (360 / n);
        zrot(angle)
        right(r)
        cube([h, w, t], center=true);
    }
}

module wave_generator() {
    color("#4a90e2")
    diff() {
        cylinder(h=thickness-2, d=flex_pitch_diam - (gear_module * 2), center=true);
        tag("remove")
        cylinder(h=thickness, d=bore_diameter, center=true, $fn=128);
    }
}

module flexspline() {
    color("#e24a4a")
    diff() {
        union() {
            // Body
            cylinder(h=thickness, d=flex_pitch_diam - 0.1, center=true, $fn=64);
            // Discrete Teeth
            component_teeth(flex_teeth, (flex_pitch_diam/2), tooth_w, tooth_h, thickness);
            // Base flange
            down(thickness/2)
            cylinder(h=2, d=flex_pitch_diam + 10, anchor=TOP, $fn=64);
        }
        // Subtraction for cup
        tag("remove")
        cylinder(h=thickness + 0.1, d=flex_pitch_diam - (gear_module * 4), center=true, $fn=64);
    }
}

module circular_spline() {
    color("#2d2d2d")
    diff() {
        cylinder(h=thickness, d=pitch_diam + 15, center=true, $fn=64);
        tag("remove") {
            cylinder(h=thickness+1, d=pitch_diam + 0.1, center=true, $fn=64);
            // Internal teeth (subtracted)
            component_teeth(num_teeth, (pitch_diam/2), tooth_w, tooth_h, thickness+1);
        }
    }
}

// Assembly / Rendering
if (render_mode == 0) {
    wave_generator();
    flexspline();
    circular_spline();
} else if (render_mode == 1) {
    wave_generator();
} else if (render_mode == 2) {
    flexspline();
} else if (render_mode == 3) {
    circular_spline();
}
