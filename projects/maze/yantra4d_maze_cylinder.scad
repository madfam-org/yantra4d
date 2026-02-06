// Yantra4D wrapper — Maze Cylinder
// Maze wrapped onto a cylindrical surface

rows = 10;
cols = 10;
cell_size = 5;
wall_thickness = 1.2;
wall_height = 3;
base_thickness = 2;
seed = 123;
diameter = 100;
render_mode = 0;

use <maze/mz_square.scad>
use <maze/mz_squarewalls.scad>
use <line2d.scad>

radius = diameter / 2;
maze_h = rows * cell_size;

// Generate wrapping maze (x_wrapping connects left-right edges)
cells = mz_square(rows, cols, seed = seed, x_wrapping = true);
walls = mz_squarewalls(cells, cell_size);

maze_w = cols * cell_size;
circumference = PI * diameter;
angle_per_unit = 360 / maze_w;

// Cylinder base shell
difference() {
    cylinder(h = maze_h + base_thickness, r = radius);
    translate([0, 0, base_thickness])
        cylinder(h = maze_h + 1, r = radius - base_thickness);
}

// Maze walls on outer surface — approximate by placing wall segments
translate([0, 0, base_thickness])
    for (wall = walls) {
        p1 = wall[0];
        p2 = wall[1];
        a1 = p1.x * angle_per_unit;
        a2 = p2.x * angle_per_unit;
        z1 = p1.y;
        z2 = p2.y;

        hull() {
            rotate([0, 0, a1])
                translate([radius - 0.1, 0, z1])
                    cube([wall_height, wall_thickness, 0.1], center = true);
            rotate([0, 0, a2])
                translate([radius - 0.1, 0, z2])
                    cube([wall_height, wall_thickness, 0.1], center = true);
        }
    }
