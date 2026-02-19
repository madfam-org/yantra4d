// Yantra4D wrapper — Text Plaque
// Rectangular base with raised or inset text

message = "Hello";
font_size = 12;
text_depth = 1.5;
base_width = 80;
base_height = 40;
base_thickness = 3;
raised = true;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

if (raised) {
    // Raised text: base + extruded text on top
    union() {
        cube([base_width, base_height, base_thickness]);
        translate([base_width / 2, base_height / 2, base_thickness])
            linear_extrude(text_depth)
                text(message, size = font_size, halign = "center", valign = "center");
    }
} else {
    // Inset text: base with text carved in
    difference() {
        cube([base_width, base_height, base_thickness]);
        translate([base_width / 2, base_height / 2, base_thickness - text_depth])
            linear_extrude(text_depth + 0.1)
                text(message, size = font_size, halign = "center", valign = "center");
    }
}
