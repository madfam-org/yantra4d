include <BOSL2/std.scad>

// Yantra4D Parameters
upper_circumference_mm = 320;
lower_circumference_mm = 240;
socket_length_mm = 250;
voronoi_density = 10;

// Internal Calcs
r_upper = upper_circumference_mm / (2 * PI);
r_lower = lower_circumference_mm / (2 * PI);
distal_interface_d = 50; // Standard distal cap

module voronoi_pattern(r, h, density) {
    // Simplified Voronoi-like pattern using spheres
    // Real Voronoi on curved surface is hard in pure SCAD without heavy comp.
    // Approximating with random spherical cutouts.
    
    // We use a deterministic seed relative to input params to keep it consistent
    seed_base = r * h;
    
    for (i=[0:density*2]) {
        z = rands(20, h-20, 1, i)[0];
        ang = rands(0, 360, 1, i+seed_base)[0];
        rad = rands(5, 15, 1, i+seed_base*2)[0];
        
        up(z)
        rotate([0, 0, ang])
        right(r) // Push to surface
        sphere(r=rad);
    }
}

module socket_shell() {
    wall_thickness = 4;
    
    difference() {
        // Outer Shell
        hull() {
            cylinder(h=1, r=r_lower + wall_thickness, $fn=64);
            up(socket_length_mm)
            cylinder(h=1, r=r_upper + wall_thickness, $fn=64);
        }
        
        // Inner Cavity
        hull() {
            up(wall_thickness)
            cylinder(h=1, r=r_lower, $fn=64);
            up(socket_length_mm + 1)
            cylinder(h=1, r=r_upper, $fn=64);
        }
        
        // Voronoi Ventilation
        // Apply pattern to the tapered surface
        // We approximate the surface at mid-radius for subtraction
        r_mid = (r_upper + r_lower) / 2;
        voronoi_pattern(r_mid + wall_thickness, socket_length_mm, voronoi_density);
        
        // Distal Hardware Mounting Holes
        down(1)
        cylinder(h=10, d=6, $fn=32); // Central bolt
        
        for(a=[0:90:360]) {
             rotate([0,0,a])
             right(15)
             down(1)
             cylinder(h=10, d=4, $fn=32); // Mounting pattern 4xM4
        }
    }
}

socket_shell();
