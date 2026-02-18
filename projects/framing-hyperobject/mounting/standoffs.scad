// --- Standoffs ---

module standoff_barrel(h = 20, d = 12, thread_d = 4) {
  difference() {
    cylinder(h=h, d=d);
    // Thread hole
    translate([0, 0, -1]) cylinder(h=h + 2, d=thread_d);
  }
}

module standoff_cap(h = 5, d = 12) {
  cylinder(h=h, d=d);
}

module standoff_set(spacing_x = 100, spacing_y = 100, h = 25) {
  sx = spacing_x / 2;
  sy = spacing_y / 2;

  translate([-sx, -sy, 0]) standoff_barrel(h=h);
  translate([sx, -sy, 0]) standoff_barrel(h=h);
  translate([-sx, sy, 0]) standoff_barrel(h=h);
  translate([sx, sy, 0]) standoff_barrel(h=h);
}
