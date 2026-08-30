# Halloween Skull Prop — CAD Handover

**Last updated:** 2026-08-30
**Scope:** 3D-printed physical build (tray, skull mount, eye LED mounts).
Electronics/software are covered by `HALLOWEEN.md` — this doc is the CAD side only.

Everything here is parametric OpenSCAD. Source lives in `cad/tray_v1/src/`,
STLs render out to `cad/tray_v1/`. Every tuned number below was arrived at by
printing and testing, not by calculation — treat them as measured facts.

---

## 1. Status

| Part | State | Notes |
|---|---|---|
| Tray panels (FL/FR/BL/BR) | **Printed, done** | 2×2 split, bolt-together seams |
| Tray legs (×4) | **Printed, done** | Separate snap-peg parts |
| Skull mount v2 (fixed) | **Final STL, not yet printed** | `mount_fixed_v2.stl` |
| Ball/socket fit | **Settled** | Validated on printed coupon "1" |
| Attachment plate + ball | **Printed, works** | `mount_plate.stl`, unchanged |
| Eye LED mount | **Final STL, printing** | `eye_led_mount.stl`, ×2 needed |
| Pi 5 sled | **Briefed, not started** | See `COWORK_BRIEF_pi_sled.md` |
| Speaker covers | **Not started** | Design discussed, blocked on measurements |
| Component covers (rock/bone/tombstone) | **Not started** | — |

---

## 2. Settled dimensions — DO NOT "tidy" THESE

These look wrong on paper. They are correct. Each replaced a more "sensible"
value that failed a physical test.

### Ball / socket joint
| Param | Value | Why |
|---|---|---|
| `BALL_D` | 32.0 | Ball stud on the skull-side plate |
| `SOCKET_CLEAR` | **-0.5** | Cavity = 31.0mm on a 32mm ball — a 1mm **interference** fit. Positive clearances (0.35 / 0.15 / 0.05 / 0) ALL slipped under the skull's weight. Negative is deliberate. |
| `SOCKET_WALL` | 2.6 | |
| `SOCKET_SLITS` | 3 | Lets the cup flex open to admit the oversized ball |
| `SOCKET_GRIP_FN` | 16 | Low facet count **only** on the cavity sphere — facet edges give the ball mechanical bite. Not a rendering artefact. |

Tested: coupon "1" (31.0mm) accepted, coupon "2" (30.0mm) rejected as too tight.

### Fixed mount v2
| Param | Value | Why |
|---|---|---|
| `FIXED_POST_H` | 40 | v1 shaft was 90; cut by 50mm. v1 sat far too high even at minimum. |
| `FIXED_POST_D` | 26 | **Hard ceiling: must stay under the 31mm cavity diameter.** Go wider and the socket's flex fingers fuse to the post and the ball will not go in at all. |
| `FIXED_FILLET_D/H` | 42 / 9 | Base gusset — all bending load concentrates here |
| `ANCHOR_SIZE` / `ANCHOR_T` | 100 / 8 | Plate, unchanged from v1 |
| `MOUNT_BOLT_R` / `_D` | 40 / 4.5 | **Must match `tray.scad`** — holes already drilled in the deck |

Resulting geometry: **ball centre 48mm above the deck, 54.3mm total height.**

### Eye LED mount
| Param | Value | Why |
|---|---|---|
| `PUCK_D` | 28 | Face diameter — nests into the orbit with glue/shim, not a precise fit |
| `FLAT_H` | 1 | Straight rim only; the rest is the domed back |
| `LED_BORE_D` | **2.8** | **The LEDs are 3mm, not 5mm.** This was the root cause of three failed iterations. |
| `LED_CHAMFER_D/H` | 3.4 / 0.4 | Deliberately tiny — a wide funnel relieves grip exactly where it's needed |

Print ×2 (left + right eye), same file.

### Tray (built, for reference)
440 × 450mm deck, 6mm thick, split at 220/225 into four panels (all under the
P2S 256mm bed). Legs 30mm tall, printed separately, 8mm split peg into a 7.7mm
socket. Panel IDs engraved on the **underside**, pre-mirrored so they read
correctly when the panel is flipped over.

---

## 3. Lessons that cost time — read before changing anything

**1. This printer runs holes/cavities OVERSIZE relative to the model.**
Consistently, across the socket and the LED bore. Downloaded STLs print
dimensionally accurate, so it is not a slicer setting — it is that modelled
clearance gets eaten before it does anything. **Design fits at zero or negative
clearance and file/drill to open up.** Opening a tight hole is easy; fixing a
loose one means a reprint.

**2. Verify the part's actual dimension, don't trust the assumed spec.**
Three reprints of the eye mount were spent shrinking a hole for a "5mm" LED
that was actually 3mm. One caliper measurement would have skipped all of it.
Measure the real component first.

**3. `socket_cup()` only carves its cavity from its own geometry.**
If you union any external solid (a rod, a post) that reaches up into the ball
space, that solid stays solid and fills the cavity. **Every part that mounts the
cup must subtract the cavity sphere again at assembly level.** Both
`part_rod()` and `part_anchor_fixed()` do this — copy the pattern for any new part.

**4. Print previews need Xvfb.** Plain `openscad --imgsize` writes a 0-byte
file ("Unable to open a connection to the X server"). Always
`xvfb-run -a openscad --render ... --autocenter --viewall`.

**5. Trimming a dome by intersecting with a short cylinder chops it flat.**
To shorten a dome while keeping it round, build the full hemisphere then
`scale()` it in Z.

**6. Underside engraved text must be pre-mirrored**, and verify by rotating
`[0,180,0]` (flip like a book page), NOT `[180,0,0]` — the wrong axis
double-flips and gives a misleading result.

---

## 4. Open items

**Speaker covers — blocked on measurements.** The two speakers turned out to be
permanently cabled together, so the plan is to stack them vertically rather than
change the tray layout: bottom speaker on the deck, a lower shell over it with a
flat top, second speaker on that, second shell on top. Styled as a ruined
headstone (better than a rock for a tall stack — the fracture line hides the
seam between tiers). **Needed to proceed:** speaker W×D×H, where the grille face
and cable exit sit on each unit, and how much slack the tether cable has.

Design constraints already identified: generous cable channel between tiers
(pinching the tether is the main risk), don't seal the speakers in — open grille
area on each tier plus foam/tape isolation so the shell doesn't buzz, key the
tiers with a recess so the stack can't shift, keep it lift-off rather than glued.

**Skull umbilical bore — needs drilling into the finished deck.** There is no
cable path through the mount: `part_anchor_fixed` is a solid plate, a solid 26mm
post and the socket cup, nothing bored through. The servo and LED wires have to
run up the **outside** of the post, which means they need to surface next to it.

Nothing in `tray.scad`'s `cable_holes` is near the centre, so **drill one 13mm
bore at ~`[245, 290]`** (coordinates from the front-left corner, same frame as
`cable_holes`). That position sits ~15mm clear behind the anchor plate's back
edge (y=275), 25mm off the x=220 seam so it lands cleanly inside the `BR` panel,
and clear of the seam bosses at `[220,330]` and `[240,225]`. It is directly
behind the skull and therefore invisible from the front.

If `tray.scad` is ever re-rendered, add it to `cable_holes` rather than
re-drilling. Full layout reasoning and the routing rule are in `HALLOWEEN.md`
("Tray layout" / "Cable routing").

⚠️ **`part_anchor_fixed` has no relief for the seam bosses.** Two of them —
`[220,240]` and `[240,225]` — fall inside the mount plate's 100 × 100 footprint
and stand 8mm proud. If those seam bolts are fitted the plate rocks on two
bosses instead of sitting flat, on the one genuinely load-bearing joint in the
build. Either relieve the plate or leave those two seam positions unbolted.

**Pi 5 sled — briefed, not started.** A printed sled to hold the Pi 5mm–10mm off
the deck with airflow for the Active Cooler, bolted down with M4 into the leg
void. Spec and constraints in `COWORK_BRIEF_pi_sled.md`. ⚠️ The Pi's four M2.5
mounting holes are 58 × 49mm and **not centred on the board** — inset 3.5mm from
three edges but 23.5mm from the USB/Ethernet end.

**Component covers** (rock / bone / tombstone) for the PIR, mic, Pi + breadboard,
and powerboard — not started.

**Superseded, kept only for reference:** `mount_anchor.stl` and `mount_rod.stl`
are the v1 adjustable-height design. v1 had a clamp-bolt flaw (the bolt hole
passed through the sleeve's axis but the rod had no matching hole, so it could
never actually clamp). **That flaw is now moot** — v2 is one rigid piece with no
height adjustment. Do not print v1 parts.

---

## 5. Files

```
cad/tray_v1/
  src/tray.scad             parametric source — tray + legs
  src/skull_mount.scad      parametric source — mount v1, v2, coupons, plate
  src/eye_led_mount.scad    parametric source — eye LED plug
  src/pi_sled.scad          (pending — see COWORK_BRIEF_pi_sled.md)

  tray_FL/FR/BL/BR.stl      deck panels (printed)
  tray_LEG.stl              leg, print ×4 (printed)
  mount_fixed_v2.stl        ** CURRENT MOUNT — print this **
  mount_plate.stl           ball stud plate, glues inside the skull (printed)
  eye_led_mount.stl         ** CURRENT EYE MOUNT — print ×2 **
  mount_socket_TEST1/2.stl  fit coupons (testing done; 1 was chosen)
  mount_anchor.stl          v1, superseded — do not print
  mount_rod.stl             v1, superseded — do not print
```

## 6. Regenerating

```bash
cd cad/tray_v1/src
openscad -D 'PART="FIXED"' -o ../mount_fixed_v2.stl skull_mount.scad
openscad -D 'PART="PLATE"' -o ../mount_plate.stl    skull_mount.scad
openscad -o ../eye_led_mount.stl eye_led_mount.scad
openscad -D 'PANEL="FL"' -o ../tray_FL.stl tray.scad   # FR / BL / BR / LEG
```

`PART` accepts: `FIXED`, `PLATE`, `TEST1`, `TEST2`, `ANCHOR` (v1), `ROD` (v1), `ASSY`.
Check `Simple: yes` in the render output — that confirms a manifold, printable mesh.
(`Volumes: 2` is normal; it counts the surrounding ambient space, not a defect.)

## 7. Print notes

- **Mount v2:** plate-down, socket-up. No supports needed that way; the finger
  overhangs and the dished ball seat come out clean.
- **Seat the ball into the socket BEFORE gluing the plate into the skull.** A 1mm
  interference fit takes real force — far easier with the plate loose in your hand.
- **Tray panels:** flat, no supports. Legs print separately for the same reason.
- **Eye mounts:** the 2.8mm bore will need reaming with a 3mm drill or round file.
  That is intentional.
