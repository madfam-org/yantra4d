// Yantra4D Gridfinity Cup - BOSL2 Implementation
include <../../libs/BOSL2/std.scad>

width_units = 2;
depth_units = 1;
height_units = 3;
cup_floor_thickness = 0.7;
fn = 0;
$fa = 6; $fs = 0.4; $fn = fn > 0 ? fn : 32;

pitch = 42;
zpitch = 7;
corner_radius = 3.75;

module gridfinity_cup() {
    total_w = width_units * pitch - 0.5;
    total_d = depth_units * pitch - 0.5;
    total_h = height_units * zpitch;
    
    // Core geometry
    difference() {
        cuboid([total_w, total_d, total_h], p1=[-total_w/2, -total_d/2, 0], rounding=corner_radius, edges="Z");
        
        // Inner scoop
        up(cup_floor_thickness)
            cuboid([total_w - 2.4, total_d - 2.4, total_h], p1=[-(total_w - 2.4)/2, -(total_d - 2.4)/2, 0], rounding=corner_radius, edges="Z");
            
        // Bottom profile (interface)
        for (x=[0:width_units-1], y=[0:depth_units-1]) {
            translate([x*pitch - (total_w)/2 + pitch/2, y*pitch - (total_d)/2 + pitch/2, 0]) {
                down(0.1) prismoid(size1=[39.2, 39.2], size2=[42, 42], h=5, rounding1=corner_radius, rounding2=corner_radius, anchor=BOT);
            }
        }
    }
}

gridfinity_cup();
