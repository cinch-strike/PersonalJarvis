// ============================================================
// Halloween Skull Prop — EYE SOCKET LED MOUNT
// Donnie / Cinch + Strike — 2026-08-22
//
// A small plug that sits in the eye socket: flat face forward
// (where the LED dome shows), a rounded/domed back so it seats
// into the socket's curve without needing to match it precisely
// (glue/shim it in — friction fit isn't the goal here). A single
// straight bore through the middle takes a standard 5mm LED —
// push it in from the back until the dome sits flush with the
// front face, legs trail out the back through the same hole for
// you to wire through the skull as planned.
//
// Print TWO of these (left + right eye) — same file both times.
//
// Render:
//   openscad -o eye_led_mount.stl eye_led_mount.scad
// ============================================================

$fn = 64;

// The ROUNDED BACK is exactly as originally designed — full hemisphere,
// PUCK_D/2 = 14mm deep, never touched. Only the flat section changes.
PUCK_D = 28;         // unchanged — same diameter/circumference as the original
FLAT_H = 1;          // was 6 — reduced by 0.5cm as asked. This is the straight-sided
                     // rim between the flat front face and where the dome starts.
// total depth = FLAT_H + PUCK_D/2 = 15mm (was 20mm)

LED_BORE_D = 2.8;    // The LEDs are 3mm, NOT 5mm — that's why 5.2/5.0/4.8 all slid
                     // straight through. 2.8 gives a light interference fit on a 3mm
                     // body; ream with a 3mm drill if it needs easing. Use 2.9 for a
                     // press fit that goes in without drilling.
LED_CHAMFER_D = 3.4; // tiny lead-in only. A wide funnel on a 2.8mm bore would relieve
LED_CHAMFER_H = 0.4; // the grip right at the face, which is the opposite of the point.

module eye_led_mount() {
    difference() {
        union() {
            cylinder(d=PUCK_D, h=FLAT_H);              // flat front section
            // domed back — original full hemisphere, unchanged. Clipped so it
            // only ever adds material BEHIND the flat front, never pokes past it.
            intersection() {
                translate([0,0,FLAT_H]) sphere(d=PUCK_D);
                translate([0,0,FLAT_H]) cylinder(d=PUCK_D, h=PUCK_D);
            }
        }
        // LED bore, straight through the whole depth
        translate([0,0,-1])
            cylinder(d=LED_BORE_D, h=FLAT_H+PUCK_D/2+2);
        // entry chamfer at the front so the LED dome guides in easily
        translate([0,0,-0.1])
            cylinder(d1=LED_CHAMFER_D, d2=LED_BORE_D, h=LED_CHAMFER_H);
    }
}

eye_led_mount();
