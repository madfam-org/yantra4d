// Yantra4D wrapper — Julia Fractal Vase
// Single mode: vase

height = 150;
base_radius = 40;
twist_angle = 360;
wave_frequency = 5;
wave_amplitude = 10;
wall_thickness = 2;
fn = 64;
resolution = 100;
render_mode = 0;

// Map to library params
julia_height = height;
julia_radius = base_radius;
julia_twist = twist_angle;
julia_freq = wave_frequency;
julia_amp = wave_amplitude;
julia_wall = wall_thickness;
julia_fn = fn > 0 ? fn : 64;
julia_resolution = resolution;

include <vendor/julia_vase.scad>
