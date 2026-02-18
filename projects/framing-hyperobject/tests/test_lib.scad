// Sanity check: Ensure all modules can be used without syntax errors
use <../profiles/classic.scad>
use <../profiles/industrial.scad>
use <../mounting/vesa.scad>
use <../mounting/cleats.scad>
use <../mounting/standoffs.scad>
use <../containers/slabs.scad>
use <../containers/capsules.scad>

echo("All modules loaded successfully.");
