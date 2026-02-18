// --- Coin Capsules (Direct Fit) ---

// Returns [outer_dia, inner_dia, thickness]
function capsule_dims(type) =
  (type == "Silver Eagle") ? [44.45, 40.6, 3.2]
  : (type == "Small Dollar") ? [30.9, 26.5, 2.0]
  : (type == "Large Dollar") ? [44.45, 38.1, 3.1]
  : [44.45, 40.6, 3.2];

module coin_capsule(type = "Silver Eagle", tolerance = 0.15) {
  dims = capsule_dims(type);
  od = dims[0];
  id = dims[1];
  h = dims[2];

  // Simple ring representation
  difference() {
    cylinder(h=h, d=od + tolerance * 2);
    translate([0, 0, -1]) cylinder(h=h + 2, d=id);
  }
}

// --- ID Badges (CR80) ---

module id_badge_holder(orientation = "horizontal") {
  w = 86; // CR80 width + tolerance
  h = 54; // CR80 height + tolerance
  d = 4; // Holder thickness

  slot_w = 14;
  slot_h = 3;

  difference() {
    // Body
    cube([w + 4, h + 4, d], center=true);
    // Card Slot
    translate([0, 2, 0]) cube([w, h, d - 1], center=true);
    // Lanyard Punch
    translate([0, (h / 2) + 1, 0]) cube([slot_w, slot_h, d + 2], center=true);
  }
}
