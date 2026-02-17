include <BOSL2/std.scad>

// Yantra4D Parameters
mount_width_mm = 40;
bolt_spacing_mm = 20;
bolt_size = "M4"; // [M3, M4, M5]

// CDG Constants (TS35)
RAIL_WIDTH = 35;
RAIL_DEPTH = 7.5;
LIP_THICKNESS = 1.0;

module din_clip() {
    diff()
    cuboid([mount_width_mm, RAIL_WIDTH + 10, 8], anchor=BOTTOM) {
        // DIN Rail Cutout
        tag("remove")
        attach(BOTTOM)
        down(0.1)
        prismoid([mount_width_mm, RAIL_WIDTH + 0.5], [mount_width_mm, RAIL_WIDTH - 2], h=RAIL_DEPTH, anchor=BOTTOM);
        
        // Locking Lip (Fixed Top)
        tag("keep")
        attach(TOP+BACK)
        down(2)
        prismoid([mount_width_mm, 3], [mount_width_mm, 1], h=3, anchor=TOP+BACK);
        
        // Spring Lip (Flexible Bottom)
        tag("keep")
        attach(TOP+FWD)
        down(2)
        prismoid([mount_width_mm, 3], [mount_width_mm, 1], h=3, anchor=TOP+FWD);

        // Mounting Holes
        tag("remove")
        bolt_d = (bolt_size == "M3") ? 3.2 : (bolt_size == "M4") ? 4.2 : 5.2;
        
        attach(TOP)
        left(bolt_spacing_mm/2)
        cylinder(h=20, d=bolt_d, center=true, $fn=32);
        
        attach(TOP)
        right(bolt_spacing_mm/2)
        cylinder(h=20, d=bolt_d, center=true, $fn=32);
    }
}

din_clip();
