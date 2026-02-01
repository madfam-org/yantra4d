// Qubic Superformula Vase
// Uses dotSCAD shape_superformula for cross-section generation
// Extrudes with varying parameters along height for vase shape

use <dotSCAD/src/shape_superformula.scad>

// --- Parameters (overridden by platform) ---
m1 = 5;
m2 = 5;
n1 = 2;
n2 = 7;
n3 = 7;
height = 100;
wall_thickness = 2;
radius = 40;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 48;
steps = max(20, floor(height / 3));

// Generate a superformula cross-section at given scale
function sf_shape(r, m, n1_v, n2_v, n3_v, pts=64) =
    shape_superformula(phi_step=360/pts, m1=m, m2=m, n1=n1_v, n2=n2_v, n3=n3_v) * r;

// Vase profile: taper from narrow base to wider body, then narrow at top
function vase_radius(z, h, r) =
    let(t = z / h)
    r * (0.4 + 0.6 * sin(t * 180));  // sinusoidal taper

module vase_body() {
    // Stack cross-sections with linear_extrude approximation
    for (i = [0 : steps - 1]) {
        z0 = i * height / steps;
        z1 = (i + 1) * height / steps;
        r0 = vase_radius(z0, height, radius);
        r1 = vase_radius(z1, height, radius);

        hull() {
            translate([0, 0, z0])
                linear_extrude(0.01)
                    polygon(sf_shape(r0, m1, n1, n2, n3));
            translate([0, 0, z1])
                linear_extrude(0.01)
                    polygon(sf_shape(r1, m1, n1, n2, n3));
        }
    }
}

module vase_hollow() {
    difference() {
        vase_body();
        translate([0, 0, wall_thickness])
            scale([(radius - wall_thickness)/radius,
                   (radius - wall_thickness)/radius,
                   1])
                vase_body();
    }
}

// --- Render ---
if (render_mode == 0) {
    vase_hollow();
}
