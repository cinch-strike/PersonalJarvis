// ============================================================
// Halloween Skull Prop — TRAY v1
// Donnie / Cinch + Strike — 2026-08-22
//
// Full tray: 440 x 450mm, split into a 2x2 grid of panels
// (each well under the Bambu P2S 256x256mm bed). Panels join
// with alignment/fastening bosses that sit EXACTLY on the seam
// line — each panel naturally gets a matching half-boss +
// half-hole when clipped, so an M4 bolt+nut through the pair
// pulls two panels together and keeps them aligned. No fiddly
// tongue/groove protrusion logic, easy to assemble, easy to
// take apart later if you need to redo a panel.
//
// The skull mount is a SEPARATE bolt-on module (see
// skull_mount.scad) anchored right at the point where all 4
// panels meet, so the single most load-bearing point on the
// tray sits on reinforced, doubly-bolted ground rather than
// riding on one panel alone.
//
// Legs are printed SEPARATELY from the deck (v2) — a flat deck
// panel needs zero support material; printed with legs attached
// they'd hang 30mm below the panel and need support underneath
// almost the whole floor. Each leg has a flanged, split (flexy)
// peg on top that snaps into a socket hole in the deck's
// underside; glue it too if the press-fit isn't tight enough.
//
// Render one panel at a time:
//   openscad -D 'PANEL="FL"' -o tray_FL.stl tray.scad
//   openscad -D 'PANEL="FR"' -o tray_FR.stl tray.scad
//   openscad -D 'PANEL="BL"' -o tray_BL.stl tray.scad
//   openscad -D 'PANEL="BR"' -o tray_BR.stl tray.scad
//   openscad -D 'PANEL="LEG"' -o tray_leg.stl tray.scad        (print x4)
//   openscad -D 'PANEL="ALL"' -o tray_preview.stl tray.scad   (unsplit, visual only)
// ============================================================

$fn = 48;

// ---------- global dims (mm), all in GLOBAL coords (0,0) = front-left corner ----------
TRAY_W = 440;
TRAY_D = 450;
DECK_T = 6;              // deck plate thickness
CORNER_R = 14;           // outer corner rounding

LEG_H = 30;               // standoff leg height (cable clearance underneath)
LEG_D = 22;               // leg diameter
LEG_INSET = 28;           // leg centre inset from tray edges
LEG_BASE_D = 32;          // flared foot diameter (ground contact end)
LEG_BASE_H = 6;

// leg-to-deck joint: flange sits flush on the deck's underside,
// a short split peg snaps into a hole bored into the deck
LEG_FLANGE_D = 26;
LEG_FLANGE_H = 2.2;
LEG_PEG_D = 8;            // peg at rest (unsprung) diameter
LEG_PEG_H = 5;            // peg length = deck socket depth
LEG_PEG_SLIT_W = 0.6;     // two crossed slits let the peg flex slightly on insertion
LEG_SOCKET_D = 7.7;       // deck socket dia — slightly under peg_d for a snug press/snap fit
LEG_SOCKET_DEPTH = 5;     // blind hole, deck is 6mm thick so this leaves a 1mm ceiling

SPLIT_X = TRAY_W/2;       // 220 — vertical seam (global x)
SPLIT_Y = TRAY_D/2;       // 225 — horizontal seam (global y)

// cable bore holes — wires drop through the deck into the 30mm
// underfloor void, then route to the exit slot at the back edge.
CABLE_HOLE_D = 13;
cable_holes = [
    [TRAY_W/2 - 40, 37],        // PIR
    [TRAY_W/2 + 35, 37],        // mic / ReSpeaker
    [TRAY_W - 15 - 28, 60],     // Pi 5 (right-edge strip)
    [TRAY_W - 15 - 28, 300],    // breadboard (right-edge strip)
    [TRAY_W/2 - 205 + 65, 365], // speaker (back-left block)
    [TRAY_W/2 + 5,  330],       // powerboard, left end
    [TRAY_W/2 + 130, 330],      // powerboard, right end
];

EXIT_SLOT_W = 40;   // extension-cord exit, centred on the back edge
EXIT_SLOT_D = 14;

// skull-mount bolt pocket, centred exactly at the panel crossroads
MOUNT_BOLT_R = 40;
MOUNT_BOLT_D = 4.5;

// panel ID label, engraved into the underside near the leg socket
// so panels are easy to tell apart while sorting parts off the printer
LABEL_SIZE = 20;
LABEL_DEPTH = 0.8;
LABEL_INSET = 42;   // how far in from the leg position, toward the panel centre

// seam boss+bolt features (identical on every seam, symmetric by construction)
SEAM_BOSS_D = 18;
SEAM_BOSS_H = 8;      // proud of the deck top face
SEAM_BOLT_D = 4.5;    // M4 clearance
SEAM_NUT_POCKET_D = 8.2;  // M4 nut trap (hex ~7.7mm across flats, printed as a simple round pocket + a bit of slop)
SEAM_NUT_POCKET_H = 3.5;

// ============================================================
module rounded_rect(w, d, r) {
    hull() {
        for (sx = [-1,1]) for (sy=[-1,1])
            translate([sx*(w/2-r), sy*(d/2-r)]) circle(r=r);
    }
}

module leg_positions() {
    lx = TRAY_W/2 - LEG_INSET; ly = TRAY_D/2 - LEG_INSET;
    for (sx=[-1,1]) for (sy=[-1,1])
        translate([sx*lx, sy*ly]) children();
}

// standalone leg — print 4 of these. Flange+peg on top snaps into
// the deck's underside; flared foot at the bottom for a stable
// stance on the table.
module leg_part() {
    union() {
        // foot (bottom) — flares out for stability
        cylinder(d1=LEG_BASE_D, d2=LEG_D, h=LEG_BASE_H);
        // shaft
        translate([0,0,LEG_BASE_H]) cylinder(d=LEG_D, h=LEG_H-LEG_BASE_H);
        // flange — sits flush against the deck's underside
        translate([0,0,LEG_H]) cylinder(d=LEG_FLANGE_D, h=LEG_FLANGE_H);
        // split peg — flexes slightly on insertion for a snap fit,
        // glue the flange too if you want it permanent
        difference() {
            translate([0,0,LEG_H+LEG_FLANGE_H]) cylinder(d=LEG_PEG_D, h=LEG_PEG_H);
            translate([-LEG_PEG_SLIT_W/2,-LEG_PEG_D,LEG_H+LEG_FLANGE_H-0.5])
                cube([LEG_PEG_SLIT_W, LEG_PEG_D*2, LEG_PEG_H+1]);
            translate([-LEG_PEG_D,-LEG_PEG_SLIT_W/2,LEG_H+LEG_FLANGE_H-0.5])
                cube([LEG_PEG_D*2, LEG_PEG_SLIT_W, LEG_PEG_H+1]);
        }
    }
}

// socket cut into the deck's underside (bottom face, z=0) at a leg
// position (local coords) — blind hole, leaves a ~1mm ceiling
module leg_socket_cut(x, y) {
    translate([x,y,-0.5])
        cylinder(d=LEG_SOCKET_D, h=LEG_SOCKET_DEPTH+0.5);
}

// engraved ID text, cut into the underside (bottom face, z=0)
function label_pos(lr, fb) =
    let (sx = (lr=="L") ? -1 : 1, sy = (fb=="F") ? -1 : 1,
         lx = TRAY_W/2 - LEG_INSET, ly = TRAY_D/2 - LEG_INSET)
    [sx*(lx-LABEL_INSET), sy*(ly-LABEL_INSET)];

// engraved on the UNDERSIDE (cut upward from the bottom face, z=0) so
// it's out of sight once the tray's assembled and components are taped
// down on top. Text is pre-mirrored in X: viewed from underneath (the
// only way you'd ever see it) that cancels out and it reads correctly —
// mirror it and check before trusting this on a new font/size.
module label_cut(txt, x, y) {
    translate([x, y, -0.1])
        linear_extrude(height=LABEL_DEPTH+0.1)
            mirror([1,0,0])
                text(txt, size=LABEL_SIZE, halign="center", valign="center", font="Liberation Sans:style=Bold");
}

// a boss+bolt-hole+nut-trap feature, used at every seam position (local coords)
module seam_boss_solid(x, y) {
    translate([x,y,DECK_T]) cylinder(d=SEAM_BOSS_D, h=SEAM_BOSS_H);
}
module seam_boss_cut(x, y) {
    translate([x,y,-1]) cylinder(d=SEAM_BOLT_D, h=DECK_T+SEAM_BOSS_H+2);
    // nut trap recessed into the underside (bolt drops from the top, nut sits
    // in the 30mm leg-clearance void and is reachable by hand there)
    translate([x,y,-LEG_H]) cylinder(d=SEAM_NUT_POCKET_D, h=SEAM_NUT_POCKET_H);
}

function seam_x_positions() = [ for (yy = [60:90:TRAY_D-60]) yy ];
function seam_y_positions() = [ for (xx = [60:90:TRAY_W-60]) xx ];

module deck_solid() {
    difference() {
        union() {
            linear_extrude(height=DECK_T) rounded_rect(TRAY_W, TRAY_D, CORNER_R);
            // seam bosses (proud, added)
            for (yy = seam_x_positions()) seam_boss_solid(SPLIT_X-TRAY_W/2, yy-TRAY_D/2);
            for (xx = seam_y_positions()) seam_boss_solid(xx-TRAY_W/2, SPLIT_Y-TRAY_D/2);
        }
        // cable bores
        for (p = cable_holes)
            translate([p[0]-TRAY_W/2, p[1]-TRAY_D/2, -1])
                cylinder(d=CABLE_HOLE_D, h=DECK_T+SEAM_BOSS_H+2);

        // extension-cord exit slot, centred on the true back edge
        translate([0, TRAY_D/2 - EXIT_SLOT_D/2, -1])
            linear_extrude(height=DECK_T+2)
                rounded_rect(EXIT_SLOT_W, EXIT_SLOT_D, 4);

        // skull-mount bolt pocket at the crossroads
        for (a=[45,135,225,315])
            translate([MOUNT_BOLT_R*cos(a), MOUNT_BOLT_R*sin(a), -1])
                cylinder(d=MOUNT_BOLT_D, h=DECK_T+SEAM_BOSS_H+2);

        // seam bolt holes + nut traps
        for (yy = seam_x_positions()) seam_boss_cut(SPLIT_X-TRAY_W/2, yy-TRAY_D/2);
        for (xx = seam_y_positions()) seam_boss_cut(xx-TRAY_W/2, SPLIT_Y-TRAY_D/2);

        // leg snap-peg sockets, underside
        leg_positions() leg_socket_cut(0, 0);
    }
}

module quadrant_clip(lr, fb) {
    x0 = (lr=="L") ? -TRAY_W/2-1 : SPLIT_X-TRAY_W/2;
    x1 = (lr=="L") ? SPLIT_X-TRAY_W/2 : TRAY_W/2+1;
    y0 = (fb=="F") ? -TRAY_D/2-1 : SPLIT_Y-TRAY_D/2;
    y1 = (fb=="F") ? SPLIT_Y-TRAY_D/2 : TRAY_D/2+1;
    translate([x0,y0,-LEG_H-1])
        cube([x1-x0, y1-y0, LEG_H+DECK_T+SEAM_BOSS_H+2]);
}

module tray_full_preview() {
    deck_solid();
}

module panel(lr, fb) {
    p = label_pos(lr, fb);
    difference() {
        intersection() {
            deck_solid();
            quadrant_clip(lr, fb);
        }
        label_cut(str(fb, lr), p[0], p[1]);
    }
}

// ============================================================
PANEL = "ALL"; // overridden via -D 'PANEL="FL"' etc.

module render_panel(name) {
    if (name=="FL") panel("L","F");
    else if (name=="FR") panel("R","F");
    else if (name=="BL") panel("L","B");
    else if (name=="BR") panel("R","B");
    else if (name=="LEG") leg_part();
    else tray_full_preview();
}

render_panel(PANEL);
