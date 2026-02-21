include <../../libs/BOSL2/std.scad>

// Yantra4D Parameters
jaw_width_inch = 6; // [4, 6, 8]
face_pattern = "prismatic"; // [smooth, prismatic, grid, leather]
magnet_holes = true;

// CDG Constants (Kurt 6")
JAW_HEIGHT = 1.25 * 25.4; // ~31.75mm
JAW_THICKNESS = 0.75 * 25.4; // ~19mm
BOLT_SPACING = 3.875 * 25.4; // Varies by model, using standard spacing
BOLT_HEAD_D = 14; 
BOLT_SHAFT_D = 9;

module soft_jaw() {
    width_mm = jaw_width_inch * 25.4;
    
    diff()
    cuboid([width_mm, JAW_THICKNESS, JAW_HEIGHT], anchor=BACK) {
        
        // Face Pattern logic
        attach(FWD)
        if (face_pattern == "prismatic") {
            // V-grooves for round stock
            zrot(90)
            linear_extrude(width_mm)
            polygon([[-5,0], [0,5], [5,0]]);
        } else if (face_pattern == "grid") {
            // Knurling pattern
           grid_2d(spacing=5, size=[width_mm, JAW_HEIGHT])
           pyramid(h=1, size=[5,5], anchor=BOTTOM);
        }
        
        // Mounting Holes (Counterbored)
        tag("remove")
        attach(BACK)
        left(BOLT_SPACING/2)
        rotate([90,0,0])
        cylinder(h=JAW_THICKNESS+1, d1=BOLT_HEAD_D, d2=BOLT_SHAFT_D, $fn=32);
        
        tag("remove")
        attach(BACK)
        right(BOLT_SPACING/2)
        rotate([90,0,0])
        cylinder(h=JAW_THICKNESS+1, d1=BOLT_HEAD_D, d2=BOLT_SHAFT_D, $fn=32);
        
        // Magnet Pockets
        if (magnet_holes) {
            tag("remove")
            attach(BACK)
            up(JAW_HEIGHT/3)
            cylinder(h=3, d=10.2, $fn=32); // 10mm magnet
            
            tag("remove")
            attach(BACK)
            down(JAW_HEIGHT/3)
            cylinder(h=3, d=10.2, $fn=32); 
        }
    }
}

soft_jaw();
