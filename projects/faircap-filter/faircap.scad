include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/threading.scad>

// Yantra4D Parameters
filter_type = "charcoal"; // [charcoal, ceramic, mesh, empty]
housing_od_mm = 40;
housing_length_mm = 80;

// CDG Constants from Reference PCO 1881
PCO_ID = 21.74; // Approx internal diameter
PCO_OD = 26.7;  // Thread major diameter
PCO_PITCH = 3.18;

module faircap_filter() {
    diff()
    cylinder(h=housing_length_mm, d=housing_od_mm, $fn=64) {
        // Hollow chamber
        attach(TOP)
        down(housing_length_mm/2)
        cylinder(h=housing_length_mm-5, d=housing_od_mm-4, $fn=64);
        
        // PCO 1881 Interface (Female Thread) at Bottom
        tag("remove")
        down(housing_length_mm/2 - 0.1)
        zrot(180) // Orient for printing/attachment
        threaded_rod(
            d=PCO_OD,
            pitch=PCO_PITCH,
            l=15,
            internal=true,
            $fn=64
        );
        
        // Flow output at Top
        tag("remove")
        up(housing_length_mm/2 - 2)
        cylinder(h=10, d=8, $fn=32);
    }
    
    // Internal Structure based on type
    if (filter_type == "mesh") {
        up(5)
        cylinder(h=housing_length_mm-20, d=housing_od_mm-5, $fn=32)
        grid_2d(spacing=2, thickness=0.5); // Abstract mesh representation
    }
}

faircap_filter();
