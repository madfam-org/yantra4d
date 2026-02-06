// Yantra4D wrapper — KeyV2 Keycap Generator
// Provides scalar parameters for profile/row/size selection
// compatible with Yantra4D manifest-driven rendering.

include <vendor/keyv2/includes.scad>

// --- Yantra4D Parameters (mapped from project.json) ---

profile_id    = 0;      // 0=DCS, 1=DSA, 2=SA, 3=OEM, 4=Cherry
row_id        = 1;      // Row number (1-4, meaning varies by profile)
key_size_id   = 0;      // 0=1u, 1=1.25u, 2=1.5u, 3=2u
stem_type_id  = 0;      // 0=Cherry MX, 1=Alps, 2=Box Cherry
legend_enabled = false;  // Enable legend text on keycap
legend_text   = "A";    // Legend character or string
font_size     = 6;      // Legend font size (pt)
dish_depth    = 1;      // Depth of keytop dish (mm)
wall_thickness = 3;     // Total wall thickness (mm, both sides)
keytop_thickness = 1;   // Top surface thickness (mm)
stem_slop     = 0.35;   // Stem tolerance (mm, raise if keycap sticks)
render_mode   = 0;      // Part selector (0=keycap)
fn            = 0;      // Resolution override (0=auto/32)

// --- Lookup Tables ---

_sizes = [1, 1.25, 1.5, 2];
_stems = ["cherry", "alps", "box_cherry"];

// --- KeyV2 Global Variable Overrides ---

$key_length       = _sizes[key_size_id];
$stem_type        = _stems[stem_type_id];
$stem_slop        = stem_slop;
$font_size        = font_size;
$dish_depth       = dish_depth;
$wall_thickness   = wall_thickness;
$keytop_thickness = keytop_thickness;
$legends          = legend_enabled ? [[legend_text]] : [];

$fn = fn > 0 ? fn : 32;

// --- Profile Dispatch ---

if (profile_id == 0)      { dcs_row(row_id)    key(); }
else if (profile_id == 1) { dsa_row(row_id)    key(); }
else if (profile_id == 2) { sa_row(row_id)     key(); }
else if (profile_id == 3) { oem_row(row_id)    key(); }
else                      { cherry_row(row_id)  key(); }
