// Qubic wrapper — Maze Cube
// Square maze extruded into a block with raised walls

rows = 10;
cols = 10;
cell_size = 5;
wall_thickness = 1.2;
wall_height = 3;
base_thickness = 2;
seed = 123;
render_mode = 0;

use <maze/mz_square.scad>
use <maze/mz_squarewalls.scad>
use <line2d.scad>

// Generate maze
cells = mz_square(rows, cols, seed = seed);
walls = mz_squarewalls(cells, cell_size);

maze_w = cols * cell_size;
maze_h = rows * cell_size;

union() {
    // Base plate
    cube([maze_w, maze_h, base_thickness]);

    // Maze walls
    translate([0, 0, base_thickness])
        linear_extrude(wall_height)
            for (wall = walls)
                line2d(wall[0], wall[1], width = wall_thickness);
}
