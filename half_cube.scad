// 20mm Half-Cube (Additive Primitives)
// Units: mm

$fn = 64;

// --- Parameters ---
size = 20.0;
thick = 2.5;
rod_D = 6.0;
clearance = 0.2; // Rod/Miter clearance
snap_h = 2.0;
fit_clear = 0.1; // Miter fit clearance (physical gap)

// Derived
cyl_H = size - 2*thick - fit_clear; // Reduce height for clearance
cyl_R = 4.5; // 9mm diam

// --- Toggles ---
show_base = true;
show_walls = true;
show_mech = true;

// --- Assembly ---
module assembly() {
    difference() {
        union() {
            if (show_base) color("cyan") base_plate();
            if (show_walls) color("lime") translate([-size/2 + thick/2, 0, 0]) mitered_wall_left();
            if (show_walls) color("lime") translate([size/2 - thick/2, 0, 0]) mitered_wall_right();
            
            // Mechanism (Rooted in base)
            if (show_mech)
                translate([0,0, -size/2 + thick - 0.6]) // Overlap slightly more to be safe
                    mechanism();
             
            // Welds (Force Union of touching primitives)
            // Only show welds if we have the parts they connect
            if (show_base && show_walls) color("red") welds();
        }
        
        // --- Global Bores ---
        // Rod Hole
        cylinder(r=rod_D/2 + clearance, h=size*3, center=true);
        
        // Catch Grooves (rotated 90 deg)
        // Cut INTO the base (Z- direction from top of base)
        // Base Top is at -size/2 + thick.
        // Grooves are height snap_h+0.5.
        // We want them to end at Base Top.
        translate([0, 0, -size/2 + thick - (snap_h+0.5)])
            rotate([0,0,90]) 
            catch_grooves();
            
        // Text
        emboss_text();
    }
}

// --- Primitives ---

module base_plate() {
    difference() {
        // Original solid
         rotate([0, 90, 0])
            linear_extrude(height=size, center=true)
                polygon(points=[
                    [-thick/2, -size/2],         // Top-Left (Wide - Z-pos)
                    [thick/2, -size/2 + thick],  // Bottom-Left (Narrow - Z-neg)
                    [thick/2, size/2 - thick],   // Bottom-Right (Narrow)
                    [-thick/2, size/2]           // Top-Right (Wide)
                ]);
         
         // Clearance Cuts for Base
         // Cut the Y-faces.
         // Plane at 45 deg.
         // Use the same logic as Wall?
         // Wall cuts corner. Base IS the corner.
         // We want to shave the angled face.
         // Angled face normal (0, -1, -1). 
         // Move cutter "In".
         
         // Front
         translate([0, -size/2, -size/2 + thick]) // Tip of 45 face
            rotate([45, 0, 0]) 
            translate([0, 0, -fit_clear]) // Shift cutter 'down' (local Z)
            cube([size*2, thick*3, thick], center=true); // Flat Plate Cutter
            
         // Back
         translate([0, size/2, -size/2 + thick]) 
            rotate([-45, 0, 0]) 
            translate([0, 0, -fit_clear])
            cube([size*2, thick*3, thick], center=true);
    }
}

module mitered_wall_left() {
    intersection() {
        cube([thick, size, size*1.5], center=true); // Increase Z height to prevent clipping
        block_with_chamfers();
    }
}

module mitered_wall_right() {
    mirror([1,0,0]) mitered_wall_left();
}

module block_with_chamfers() {
    difference() {
        // Extend height slightly to force overlap with Base at bottom
        cube([thick, size, size + 0.2], center=true); 
        
         
         // Fix: Move it so its 'Bottom-Left' edge (after rotation) touches the cut line.
         // Easier: Use the polygon approach for precision.
         
         translate([thick/2, 0, size/2]) // At Top-Inner corner
             rotate([90, 0, 0])
             linear_extrude(size*2, center=true)
             polygon([[0,0], [-thick, 0], [0, -thick]]); // Triangle in XZ plane (-X, -Z)
             // This removes the corner exactly.
             
        /* 
        translate([thick/2, 0, size/2])
            rotate([0, -45, 0])
            cube([thick*2, size*2, thick*2], center=true);
        */
            
         // Front Chamfer (Y-)
         translate([thick/2, -size/2, 0])
            rotate([0, 0, 45])
            cube([thick*2, thick*2, size*2], center=true);
            
         // Back Chamfer (Y+)
         translate([thick/2, size/2, 0])
            rotate([0, 0, -45])
            cube([thick*2, thick*2, size*2], center=true);
    }
}

module mechanism() {
    difference() {
        union() {
            // 1. Shaft Solid
            cylinder(r=cyl_R, h=cyl_H); 
            
            // 2. Snaps Solid (Sink into Shaft)
            translate([0,0, cyl_H - 0.1])
                 cylinder(r1=cyl_R, r2=cyl_R + 0.5, h=snap_h + 0.1);
                 
            // 3. Flat Top
             translate([0,0, cyl_H + snap_h]) 
                cube([20,20,0.1], center=true);
        }
        
        // --- Subtractions ---
        
        // 1. Inactive Sectors
        rotate([0,0,90]) wedge_cut();
        rotate([0,0,270]) wedge_cut();
        
        // 2. Relief Slot (The Fix)
        // Cut through Snaps AND Shaft top
        // Reduce width to 1.5 to avoid sliver creation?
        translate([0,0, cyl_H])
            cube([1.5, cyl_R*2.5, snap_h*4], center=true); 
    }
}

// Snaps module is now integrated into mechanism
module snaps() {
    // Deprecated
}

module catch_grooves() {
    rotate([0,0,0]) wedge_cut(h=snap_h+0.5, r=cyl_R + 0.5 + 0.2);
    rotate([0,0,180]) wedge_cut(h=snap_h+0.5, r=cyl_R + 0.5 + 0.2);
}

module wedge_cut(h=size, r=20) {
    linear_extrude(h) polygon([[0,0], [r,0], [0,r]]); 
}

module welds() {
    // Small cubes to bridge gaps at the internal connection points
    // 1. Left Wall to Base
    translate([-size/2 + thick/2, 0, -size/2 + thick/2]) // Center of Wall/Base overlap
        cube([thick/2, size/2, thick/2], center=true); 
        
    // 2. Right Wall to Base
    translate([size/2 - thick/2, 0, -size/2 + thick/2]) 
        cube([thick/2, size/2, thick/2], center=true);
        
    // 3. Mechanism to Base
    // It's likely connected, but let's be sure.
    // Center of Mechanism. Base Floor.
    translate([0, 0, -size/2 + thick]) // Top of Base
        cube([2, 2, 2], center=true);
}

module emboss_text() {
     translate([-size/2 + 0.3/2 -0.01, 0, 0])
     rotate([90,0,270])
     linear_extrude(0.4)
     text("A", size=5, valign="center", halign="center");
}


assembly();
