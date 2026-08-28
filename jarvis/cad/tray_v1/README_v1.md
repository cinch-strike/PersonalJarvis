# Tray v1 — print & assembly notes

## Files
- `tray_FL.stl / tray_FR.stl / tray_BL.stl / tray_BR.stl` — the 4 tray quadrants (Front/Back x Left/Right). Each is ~220x225mm, well inside the P2S's 256x256mm bed.
- `mount_anchor.stl` — bolts to the tray at the centre crossroads (where all 4 panels meet). Fixed.
- `mount_rod.stl` — slides inside the anchor's sleeve for height adjustment; top is a snap-fit ball socket.
- `mount_plate.stl` — glues inside the skull's base. Ball stud on the underside snaps into the rod's socket.

## Print settings
- 0.2mm layer height, 15–20% infill, 3 wall loops — matches what's already dialled in for the skull itself.
- Tray panels: no supports needed (flat, legs print fine straight up).
- `mount_rod.stl`: the ball-socket top needs a touch of support (Bambu Studio will flag the overhang automatically — supports touching build plate is enough, no tree supports needed).
- `mount_plate.stl`: the ball stud is a slight overhang too — same, light auto-supports are enough. If you'd rather not support it, it also prints fine upside down (plate face down, ball up) — your call.

## Assembly order
1. Print all 4 tray panels. Test-fit them dry (no glue) — bolt the seam bosses together with M4 bolts + nuts (nuts drop into the recessed pockets on the underside, reachable in the 30mm leg gap).
2. Print the 3 mount parts. Bolt `mount_anchor.stl` down through the tray at the centre (4x M4, same bolt circle as the tray's centre holes) — this happens to land across all 4 panels at once, which is what ties the grid together at the point that'll carry the skull's weight.
3. Slide `mount_rod.stl` into the anchor's sleeve, set your height, snug the M4 clamp bolt through the slit.
4. Test-fit `mount_plate.stl` onto the rod's ball socket before gluing anything — check the snap feels right and the skull sits level. Once happy, glue the plate inside the skull's base with epoxy (the waffled face is there for grip), then snap it onto the rod.

## Still open / to confirm once you've test-fit
- Cable bore hole positions are placed from the layout plan's component centres — good enough to start routing wires, but nudge any that land in an awkward spot once you're laying real hardware down.
- Ball-socket friction hasn't been tuned against a real print yet — if it's too loose/tight, that's an easy single-part reprint (rod or plate only, tray stays as-is).
- Covers/mounts (rock, bone, tombstone) are next — separate part, once the tray + skull mount are confirmed sitting right.
