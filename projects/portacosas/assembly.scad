// Assembly — Portacosas
// Positions all components on the tray base
// render_mode: 0=tray_base, 1=pen_holder, 2=phone_stand,
//              3=card_slot, 4=cable_clip, 5=label_plate

include <desk_organizer.scad>

// Override render_mode to show all or individual parts
render_mode = 0;

// --- Assembly Layout ---

// Tray base
tray_base();

// Pen holder — left side of tray
translate([wall_thickness + 5,
           (tray_depth - pen_holder_d) / 2,
           base_h])
    pen_holder();

// Phone stand — right side of tray
translate([tray_width - wall_thickness - phone_width - 5,
           (tray_depth - 40 - wall_thickness) / 2,
           base_h])
    phone_stand();

// Card slot — front center
translate([(tray_width - card_width) / 2,
           wall_thickness + 2,
           base_h])
    card_slot();

// Cable clips — back edge
for (i = [0 : clip_count - 1]) {
    cx = wall_thickness + 20 + i * (tray_width - 40) / max(clip_count - 1, 1);
    translate([cx, tray_depth - wall_thickness - 15, base_h])
        cable_clip();
}

// Label plate — front lip
translate([(tray_width - tray_width * 0.4) / 2,
           0,
           base_h + 4])
    label_plate();
