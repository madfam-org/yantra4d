// Yantra4D wrapper — STEMFIE Fastener
use <vendor/stemfie/stemfie.scad>

length_units = 2;
fastener_type_id = 0; // 0=pin, 1=shaft
render_mode = 0;
fn = 0;

$fn = fn > 0 ? fn : 32;

if (fastener_type_id == 0) {
    pin(length=length_units, head=true);
} else {
    shaft(length=length_units, beveled_ends=true, center=true);
}
