// --- French Cleat ---
// Common Denominator Geometry for 45-degree mating cleats

module french_cleat(length = 100, height = 30, depth = 15, angle = 45) {
  // A standard french cleat cross-section
  polygon_points = [
    [0, 0],
    [depth, 0],
    [depth, height],
    [depth - (height * tan(angle)), height], // 45 deg slope
    [0, 0], // Return to origin
  ];

  translate([-length / 2, -height / 2, 0])
    rotate([90, 0, 90])
      linear_extrude(height=length) {
        polygon(points=polygon_points);
      }
}
