// --- Grading Slab Dimensions (Width x Height x Thickness) ---

function slab_dims(type) =
  (type == "PSA") ? [82.55, 136.53, 6.35]
  : // 3.25" x 5.375" x 0.25"
  (type == "BGS") ? [81.28, 130.18, 9.53]
  : // 3.20" x 5.125" x 0.375"
  (type == "SGC") ? [86.16, 138.68, 8.19]
  : // 3.392" x 5.460" x 0.3225"
  (type == "CGC") ? [79.38, 133.35, 5.08]
  : // 3.125" x 5.25" x 0.20"
  [82.55, 136.53, 6.35]; // Default to PSA

module slab_void(type = "PSA", tolerance = 0.2) {
  dims = slab_dims(type);
  w = dims[0] + tolerance * 2;
  h = dims[1] + tolerance * 2;
  t = dims[2] + tolerance * 2;

  cube([w, h, t], center=true);
}
