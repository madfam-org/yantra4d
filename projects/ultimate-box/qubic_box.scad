// Qubic wrapper — Ultimate Box Maker
// Uses Advanced-Ultimate-Box-Maker customizer variables

// Qubic scalar parameters
box_length = 80;
box_width = 60;
box_height = 30;
wall_thickness = 2.8;
corner_radius = 2;
rounded_corners = true;
ventilation = true;
vent_width = 1.7;
pcb_standoffs = false;
case_feet_id = 0;   // 0=none, 1=hex, 2=cylindrical, 3=snap, 4=snap+hole
screw_hole_dia = 2.2606;
render_mode = 0;
fn = 0;

// Map to library variables
Length = box_length;
Width = box_width;
Height = box_height;
Thick = wall_thickness;
Filet = corner_radius;
Round = rounded_corners ? 1 : 0;
Vent = ventilation ? 1 : 0;
Vent_width = vent_width;
PCBDraw = pcb_standoffs ? 1 : 0;
CaseFeet = case_feet_id;
ScrewHole = screw_hole_dia;

$fn = fn > 0 ? fn : 32;

include <vendor/box-maker/scad/Advanced-Ultimate-Box-Maker-main.scad>
