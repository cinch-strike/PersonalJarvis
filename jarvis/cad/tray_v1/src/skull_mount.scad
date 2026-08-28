// ============================================================
// Halloween Skull Prop — SKULL MOUNT v1  (the non-negotiable part)
// Donnie / Cinch + Strike — 2026-08-22
//
// Three printed parts:
//   A) ANCHOR + SLEEVE  — bolts down into the tray at the panel
//      crossroads (4x M4, matches tray.scad's MOUNT_BOLT_R/D).
//      Fixed to the tray. Has a slit + horizontal clamp bolt so
//      the inner rod's height can be set by friction and locked.
//   B) INNER ROD + SOCKET CUP — slides inside the sleeve for
//      height adjustment. Top is a snap-fit ball socket (flexes
//      open slightly PLA can take it — 3 slits — to admit the
//      ball, then grips it by friction at whatever tilt you set).
//   C) ATTACHMENT PLATE + BALL STUD — this is what gets glued
//      INSIDE the skull's base (roughened top face for epoxy).
//      Snaps down into B's socket. Lift straight up to remove.
//
// Render:
//   openscad -D 'PART="ANCHOR"' -o mount_anchor.stl skull_mount.scad
//   openscad -D 'PART="ROD"'    -o mount_rod.stl    skull_mount.scad
//   openscad -D 'PART="PLATE"'  -o mount_plate.stl  skull_mount.scad
//   openscad -D 'PART="ASSY"'   -o mount_preview.stl skull_mount.scad  (visual only)
// ============================================================

$fn = 64;

// ---- must match tray.scad ----
MOUNT_BOLT_R = 40;
MOUNT_BOLT_D = 4.5;

// ---- anchor plate ----
ANCHOR_SIZE = 100;      // square plate footprint bolted to the tray
ANCHOR_T = 8;
ANCHOR_NUT_D = 8.2;     // M4 nut trap, recessed into the top face
ANCHOR_NUT_H = 3.5;

// ---- sleeve (fixed, outer tube) ----
SLEEVE_OD = 34;
SLEEVE_ID = 21.0;       // rod OD 20 + 0.5mm radial clearance
SLEEVE_H = 90;
SLEEVE_SLIT_W = 3.5;
SLEEVE_SLIT_LEN = 60;   // measured up from the top; base stays solid for strength
CLAMP_BOLT_D = 4.5;     // M4 clamp bolt through the slit, near the top
CLAMP_BOLT_Z = SLEEVE_H - 12;

// ---- inner rod + socket ----
ROD_OD = 21.0;          // was 20 → 20.6 → 20.8, still sliding each time. Donnie wants it
                         // erring big now (file it down if it's too tight rather than
                         // reprint again) — this is now EQUAL to SLEEVE_ID, i.e. zero
                         // nominal clearance. Real fit depends entirely on print
                         // tolerance; if it won't go in at all, sand the rod OD down.
ROD_L = SLEEVE_H;       // was 130 — matches the sleeve/shaft height exactly, so the rod
                         // never overshoots the sleeve and the ball/socket sits just above it
BALL_D = 32;
SOCKET_WALL = 2.6;
SOCKET_CLEAR = -0.5;    // SETTLED — validated on printed test coupon "1".
                         // History: 0.35 → 0.15 → 0.05 → 0 all slipped under load.
                         // -0.5 gives a 31.0mm cavity on a 32.0mm ball: a 1mm
                         // interference fit, the three slits flexing open to admit it.
                         // Coupon "2" (30.0mm) was the other candidate and was rejected.
                         // Do not "tidy" this to a positive number — it is deliberate.
SOCKET_SLITS = 3;

// ---- FIXED-HEIGHT POST (v2 mount — replaces sleeve + rod entirely) ----
// Height adjustment is gone: the measured build sat too high even at minimum,
// so the travel was never usable. One rigid piece = plate + post + socket.
// Side benefit: the sleeve's clamp-bolt flaw disappears with the sleeve.
FIXED_POST_D = 26;      // beefier than the old 21mm rod (no longer has to slide).
                         // MUST stay under the ball-cavity diameter, or the socket's
                         // flex fingers get fused to the post and it can't open.
FIXED_POST_H = 40;      // 90 - 50, the shaft cut by 50mm as asked.
                         // Puts the ball centre at ANCHOR_T + 40 = 48mm above the deck.
FIXED_FILLET_D = 42;    // flared gusset at the base — all the bending load is here
FIXED_FILLET_H = 9;

SOCKET_GRIP_FN = 16;     // low facet count JUST for the ball cavity surface — turns the
                         // smooth sphere into a faceted one with slight ridges at each
                         // facet edge, for a bit of mechanical grip/texture on the ball

// ---- attachment plate + ball stud (glued into the skull) ----
PLATE_D = 80;
PLATE_T = 6;
NECK_D = 15;
NECK_L = 14;
GRIP_GROOVES = 10;      // waffle grooves on the glue face for epoxy grip

// ============================================================
// PART A — anchor base + sleeve
// ============================================================
module part_anchor() {
    union() {
        difference() {
            union() {
                // square anchor plate, corners rounded
                linear_extrude(height=ANCHOR_T)
                    offset(r=6) offset(r=-6) square([ANCHOR_SIZE, ANCHOR_SIZE], center=true);
                // sleeve rises from the plate centre
                translate([0,0,ANCHOR_T-0.01])
                    cylinder(d=SLEEVE_OD, h=SLEEVE_H);
            }
            // bore for the inner rod
            translate([0,0,ANCHOR_T+2])
                cylinder(d=SLEEVE_ID, h=SLEEVE_H);
            // 4x M4 bolt holes down to the tray, on the same bolt circle as tray.scad
            for (a=[45,135,225,315])
                translate([MOUNT_BOLT_R*cos(a), MOUNT_BOLT_R*sin(a), -1]) {
                    cylinder(d=MOUNT_BOLT_D, h=ANCHOR_T+2);
                    translate([0,0,ANCHOR_T-ANCHOR_NUT_H])
                        cylinder(d=ANCHOR_NUT_D, h=ANCHOR_NUT_H+1);
                }
            // vertical slit through the sleeve wall, top portion only
            translate([-SLEEVE_SLIT_W/2, -SLEEVE_OD, ANCHOR_T+SLEEVE_H-SLEEVE_SLIT_LEN])
                cube([SLEEVE_SLIT_W, SLEEVE_OD*2, SLEEVE_SLIT_LEN+5]);
            // horizontal clamp-bolt hole through the slit region
            translate([0,0,ANCHOR_T+CLAMP_BOLT_Z])
                rotate([90,0,0])
                    cylinder(d=CLAMP_BOLT_D, h=SLEEVE_OD+2, center=true);
        }
    }
}

// ============================================================
// PART B — inner rod + fixed socket cup (snap-fit, ball inserts from above)
// ============================================================
// clear defaults to the global; the test coupons pass their own so we can try
// several cavity sizes without touching the cup's proven shape.
module socket_cup(clear=SOCKET_CLEAR) {
    id = BALL_D + 2*clear;
    od = id + 2*SOCKET_WALL;
    difference() {
        union() {
            sphere(d=od);
            // stem down into the rod, so the cup is solidly joined
            translate([0,0,-od/2]) cylinder(d=ROD_OD, h=od/2+2);
        }
        // hollow for the ball — low $fn on purpose (facet edges = grip texture)
        sphere(d=id, $fn=SOCKET_GRIP_FN);
        // open the top so the ball can press in / lift out
        translate([0,0,od/2*0.35]) cylinder(d=od, h=od);
        // slits so the cup can flex open slightly on insertion
        for (i=[0:SOCKET_SLITS-1])
            rotate([0,0,i*360/SOCKET_SLITS])
                translate([-1,0,-od/2-1]) cube([2, od, od]);
        // flatten the bottom so it sits cleanly on the rod
        translate([0,0,-od-od/2]) cube([od*2,od*2,od*2], center=true);
    }
}

module part_rod() {
    // socket_cup() only carves its own cavity out of the material it adds
    // itself (its sphere + stem) — it has no idea the plain shaft below it
    // exists. Since the shaft runs all the way up to the cup's centre
    // (ROD_L now matches SLEEVE_H exactly), the shaft was poking solid
    // material straight into the space the ball needs. Fix: carve the same
    // ball cavity out of the whole assembly (shaft included), not just the
    // cup on its own. socket_cup() itself is untouched.
    id = BALL_D + 2*SOCKET_CLEAR;
    difference() {
        union() {
            cylinder(d=ROD_OD, h=ROD_L);
            translate([0,0,ROD_L]) socket_cup();
        }
        translate([0,0,ROD_L]) sphere(d=id, $fn=SOCKET_GRIP_FN);
    }
}

// ============================================================
// PART A2 — FIXED-HEIGHT MOUNT: plate + post + socket, one piece
// Replaces the old anchor+sleeve+rod pair. Bolt pattern is unchanged,
// so it drops onto the same 4 holes already in the tray.
// ============================================================
module part_anchor_fixed(clear=SOCKET_CLEAR) {
    id = BALL_D + 2*clear;
    z_ball = ANCHOR_T + FIXED_POST_H;
    difference() {
        union() {
            // square anchor plate, corners rounded — unchanged from v1
            linear_extrude(height=ANCHOR_T)
                offset(r=6) offset(r=-6) square([ANCHOR_SIZE, ANCHOR_SIZE], center=true);
            // flared gusset at the base, then the straight post
            translate([0,0,ANCHOR_T-0.01])
                cylinder(d1=FIXED_FILLET_D, d2=FIXED_POST_D, h=FIXED_FILLET_H);
            translate([0,0,ANCHOR_T-0.01])
                cylinder(d=FIXED_POST_D, h=FIXED_POST_H+0.01);
            // socket sits directly on the post top
            translate([0,0,z_ball]) socket_cup(clear);
        }
        // 4x M4 bolt holes + nut traps — same circle as tray.scad
        for (a=[45,135,225,315])
            translate([MOUNT_BOLT_R*cos(a), MOUNT_BOLT_R*sin(a), -1]) {
                cylinder(d=MOUNT_BOLT_D, h=ANCHOR_T+2);
                translate([0,0,ANCHOR_T-ANCHOR_NUT_H])
                    cylinder(d=ANCHOR_NUT_D, h=ANCHOR_NUT_H+1);
            }
        // Carve the ball cavity out of the WHOLE part, post included — the post
        // runs up to the ball centre, so without this it fills the ball's space
        // (the exact bug we hit on the rod). Leaves a dished seat in the post top.
        translate([0,0,z_ball]) sphere(d=id, $fn=SOCKET_GRIP_FN);
    }
}

// ============================================================
// TEST COUPONS — socket only, on a stub. Cheap to print, lets us
// dial the cavity in before committing to a full mount print.
// Each carries an engraved number on a tab so they can't be mixed up.
// ============================================================
module part_socket_test(clear, lbl) {
    id = BALL_D + 2*clear;
    od = id + 2*SOCKET_WALL;
    base_d = od + 10;
    base_h = 3;
    stub_h = 7;
    z_ball = base_h + stub_h;
    difference() {
        union() {
            cylinder(d=base_d, h=base_h);
            // label tab sticking out from the base
            translate([base_d/2 - 4, -9, 0]) cube([20, 18, 1.8]);
            translate([0,0,base_h-0.01]) cylinder(d=FIXED_POST_D, h=stub_h+0.01);
            translate([0,0,z_ball]) socket_cup(clear);
        }
        translate([0,0,z_ball]) sphere(d=id, $fn=SOCKET_GRIP_FN);
        // engraved number on the tab's top face (read from above — no mirroring)
        translate([base_d/2 + 6, 0, 1.8-0.6])
            linear_extrude(height=1)
                text(lbl, size=9, halign="center", valign="center",
                     font="Liberation Sans:style=Bold");
    }
}

// ============================================================
// PART C — attachment plate + ball stud (glued inside the skull)
// ============================================================
module part_plate() {
    union() {
        difference() {
            cylinder(d=PLATE_D, h=PLATE_T);
            // waffle grooves on the top (glue) face for epoxy grip
            for (i=[0:GRIP_GROOVES-1])
                rotate([0,0,i*180/GRIP_GROOVES])
                    translate([-PLATE_D/2,-1.2,PLATE_T-1.2])
                        cube([PLATE_D, 2.4, 2]);
        }
        // neck + ball stud hanging off the underside
        translate([0,0,-NECK_L]) cylinder(d=NECK_D, h=NECK_L+0.1);
        translate([0,0,-NECK_L]) sphere(d=BALL_D);
    }
}

// ============================================================
PART = "ASSY";

module assembly_preview() {
    part_anchor();
    translate([0,0,ANCHOR_T+8]) part_rod();
    translate([0,0,ANCHOR_T+8+ROD_L+BALL_D*0.15]) part_plate();
}

// Cavity test sizes. Current printed cavity = BALL_D + 2*0 = 32.0mm and still
// slips under load. TEST1 = 1mm smaller (31.0), TEST2 = 2mm smaller (30.0).
TEST1_CLEAR = -0.5;     // cavity 31.0mm
TEST2_CLEAR = -1.0;     // cavity 30.0mm

if (PART=="ANCHOR") part_anchor();                    // v1, superseded
else if (PART=="FIXED") part_anchor_fixed();          // v2 one-piece mount
else if (PART=="ROD") part_rod();                     // v1, superseded
else if (PART=="PLATE") part_plate();
else if (PART=="TEST1") part_socket_test(TEST1_CLEAR, "1");
else if (PART=="TEST2") part_socket_test(TEST2_CLEAR, "2");
else assembly_preview();
