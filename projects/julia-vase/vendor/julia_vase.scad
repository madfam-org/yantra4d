// Julia Fractal Vase — Parametric twisted vase with sinusoidal profile
// Vendored for Qubic — inspired by mathematical art vases
// Original concept from Thingiverse community

julia_height = 150;
julia_radius = 40;
julia_twist = 360;
julia_freq = 5;
julia_amp = 10;
julia_wall = 2;
julia_fn = 64;
julia_resolution = 100;

$fn = julia_fn;

module vase_profile(r, wall, freq, amp) {
  difference() {
    // Outer profile with sinusoidal modulation
    polygon([for(a = [0 : 360/$fn : 360])
      let(mod = r + amp * sin(a * freq))
      [mod * cos(a), mod * sin(a)]
    ]);
    // Inner cutout (hollow)
    polygon([for(a = [0 : 360/$fn : 360])
      let(mod = r + amp * sin(a * freq) - wall)
      [mod * cos(a), mod * sin(a)]
    ]);
  }
}

// Build vase with twist
linear_extrude(height=julia_height, twist=julia_twist, slices=julia_resolution, $fn=julia_fn)
  vase_profile(julia_radius, julia_wall, julia_freq, julia_amp);
