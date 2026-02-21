include <../../libs/BOSL2/std.scad>

// Yantra4D Parameters
tool_type = "stethoscope_head"; // [stethoscope_head, otoscope_specula]
diaphragm_size_mm = 44;
speculum_size_mm = 4; // [2.5, 3, 4, 5]
render_mode = 0;

module stethoscope_head() {
    // Glia-style bell
    diff()
    cylinder(h=20, d=diaphragm_size_mm + 4, $fn=64) {
        // Hollow sound chamber
        tag("remove")
        up(2)
        cylinder(h=18.1, d=diaphragm_size_mm, $fn=64);
        
        // Tube connector
        tag("keep")
        attach(RIGHT)
        cylinder(h=20, d=8, $fn=32);
        
        tag("remove")
        attach(RIGHT)
        down(1)
        cylinder(h=22, d=5, $fn=32); // Air channel
        
        // Locking groove for ring
        tag("remove")
        up(18)
        difference() {
            cylinder(h=2, d=diaphragm_size_mm + 4.1, $fn=64);
            cylinder(h=2, d=diaphragm_size_mm, $fn=64);
        }
    }
}

module otoscope_specula() {
    // Standard speculum cone
    height = 30;
    base_d = 8;
    tip_d = speculum_size_mm;
    
    diff()
    cylinder(h=height, d1=base_d, d2=tip_d, $fn=64) {
        // Hollow channel
        tag("remove")
        down(0.1)
        cylinder(h=height+0.2, d1=base_d-1.5, d2=tip_d-0.8, $fn=64);
        
        // Snap ring at base
        tag("keep")
        down(0.5)
        cylinder(h=2, d=base_d+1, $fn=64);
    }
}

if (render_mode == 1 || (render_mode == 0 && tool_type == "stethoscope_head")) {
    stethoscope_head();
} else if (render_mode == 2 || (render_mode == 0 && tool_type == "otoscope_specula")) {
    otoscope_specula();
}
