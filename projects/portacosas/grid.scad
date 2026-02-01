// Grid — Portacosas
// Tiled tray system: rows × cols array with snap-fit connectors

include <desk_organizer.scad>

// Grid parameters (overridden by manifest)
rows = 1;
cols = 1;

// Connector dimensions
connector_w = 10;
connector_h = 4;
connector_d = 8;

// Grid spacing
grid_gap = 2; // gap between tiles

// --- Connector modules ---
module grid_connector_male() {
    translate([0, 0, 0])
        cube([connector_w, connector_d, connector_h]);
    // Snap ridge
    translate([connector_w * 0.2, connector_d, connector_h * 0.3])
        cube([connector_w * 0.6, 1, connector_h * 0.4]);
}

module grid_connector_female() {
    translate([0, 0, -0.05])
        cube([connector_w + snap_tol*2,
              connector_d + snap_tol*2,
              connector_h + 0.1]);
    // Snap ridge slot
    translate([connector_w * 0.2 - snap_tol, connector_d,
               connector_h * 0.3 - snap_tol])
        cube([connector_w * 0.6 + snap_tol*2,
              1 + snap_tol*2,
              connector_h * 0.4 + snap_tol*2]);
}

// --- Grid Assembly ---
for (r = [0 : rows - 1]) {
    for (c = [0 : cols - 1]) {
        translate([c * (tray_width + grid_gap),
                   r * (tray_depth + grid_gap),
                   0]) {
            difference() {
                tray_base();
                // Female connectors on right edge (except last col)
                if (c < cols - 1) {
                    translate([tray_width - 0.1,
                               (tray_depth - connector_d) / 2,
                               0])
                        grid_connector_female();
                }
                // Female connectors on top edge (except last row)
                if (r < rows - 1) {
                    translate([(tray_width - connector_w) / 2,
                               tray_depth - 0.1,
                               0])
                        rotate([0, 0, 0])
                            grid_connector_female();
                }
            }
            // Male connectors on left edge (except first col)
            if (c > 0) {
                translate([-grid_gap,
                           (tray_depth - connector_d) / 2,
                           0])
                    grid_connector_male();
            }
            // Male connectors on bottom edge (except first row)
            if (r > 0) {
                translate([(tray_width - connector_w) / 2,
                           -grid_gap,
                           0])
                    grid_connector_male();
            }
        }
    }
}
