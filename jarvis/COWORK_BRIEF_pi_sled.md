# Cowork Brief — Raspberry Pi 5 Sled (Halloween prop tray)

Hand this whole file to Cowork. It describes one small part to design and the
hard constraints it must satisfy.

**Related:** `CAD_HANDOVER.md` (the CAD picture), `HALLOWEEN.md` (electronics,
wiring, and the as-built tray layout). Source lives in `cad/tray_v1/src/`.

---

## What this is

A printed **sled** that carries the Raspberry Pi 5 and bolts to the prop's
tray deck. The Pi currently has nothing holding it down. The sled must:

1. Hold the Pi rigidly, 5–10mm clear of the deck.
2. Let the Pi lift out as a unit for servicing.
3. Not block the Active Cooler's airflow.
4. Let cables come up through a deck bore and reach the board.

It is **not** a case — a decorative rock/bone cover goes over the whole thing
separately, so the sled needs no walls, lid, or styling.

## What is already fixed (do not redesign)

| Thing | Value |
|---|---|
| Board | Raspberry Pi 5 8GB, 85 × 56mm, with official Active Cooler fitted |
| Deck | 6mm PLA, flat, already printed and bolted together |
| Deck void | 30mm clear underneath (legs) — reachable by hand |
| Fasteners on hand | M4 bolts + nuts (tray seams), M2 self-tappers (servo kit) |
| Printer | Bambu Lab P2S, 256 × 256mm bed, PLA |

---

## The mounting holes — get this right

**Four M2.5 holes, 2.7mm diameter, 58.0 × 49.0mm spacing.**

⚠️ **The pattern is NOT centred on the board.** Holes are inset 3.5mm from
three edges but **23.5mm from the USB/Ethernet end**. Centring the 58 × 49
pattern on the 85 × 56 board is the standard mistake and produces a sled that
looks right and fits nothing.

Relative to board centre, with the 85mm axis as X and the microSD end at −X:

| | X | Y |
|---|---|---|
| Hole centres | **−39.0** and **+19.0** | **−24.5** and **+24.5** |

The Active Cooler uses its own two push-pin holes near the SoC, so all four
corner holes are free.

⚠️ **Ask the user to measure the actual board before finalising.** This repo
lost three reprints of the eye mount to a "5mm" LED that was actually 3mm
(lesson 2 in `CAD_HANDOVER.md`). One caliper measurement skips all of it.

## Printer behaviour — this is a measured fact, not a theory

**This printer runs holes and cavities OVERSIZE relative to the model**, consistently,
across every part tried so far. Downloaded STLs print dimensionally accurate, so it is
not a slicer setting — modelled clearance gets eaten before it does anything.

**Design fits at zero or negative clearance and file/ream to open up.** Opening a
tight hole is easy; a loose one is a reprint. For M2.5 self-tappers biting into
printed posts, model the pilot at **~2.1mm**.

(Full list: `CAD_HANDOVER.md` section 3.)

---

## Constraints

**Envelope.** The sled sits in the tray's right-hand lane with the board's
**85mm axis running front-to-back**. Keep the sled **≤66mm wide** across the
lane — it needs ~30mm clearance to the tray edge for the cover wall and a
finger. Length is not tight.

**Standoff height.** Board must finish **5–10mm clear of the deck**. Underside
solder joints and the PCIe connector mean it cannot lie flat, and the gap is
also the cable route (below).

**Airflow.** Large cutout through the base plate. The Active Cooler draws from
above and exhausts sideways/down; the brief for this prop requires the Pi not
thermally throttle after 30+ minutes of continuous Whisper transcription. A
sealed base defeats it.

**Cable pass-through.** A 13mm bore at tray position `[397, 60]` sits under the
Pi's lane. Raising the board ~11mm means cables can come **up under the Pi and
turn out sideways** — tidier than routing around the board. The base cutout
should span that bore. Note a USB-A plug's overmoulding (15–18mm) will not pass
a 13mm bore, so thin GPIO wires use the bore and fat USB cables pass under the
cover's skirt instead.

**Deck attachment: M4.** Put the M4 clearance holes on **ears that sit outside
the Pi's footprint**, so the sled can be unbolted without first stripping the Pi
off it. Bolt heads or nuts sit in the 30mm void, reachable by hand — that is how
the tray's own seam nut traps already work. The flat underside should also be
usable with VHB tape as a no-drill alternative.

**Board attachment: M2.5 self-tappers into printed posts.** Standard practice
and good for several removal cycles. If the user has no M2.5 on hand, M2 servo
screws work (loose in the 2.7mm hole but fine into a printed post).

**Print orientation:** flat on the bed, posts up, no supports.

---

## Deliverables

1. A parametric **OpenSCAD source** file, `cad/tray_v1/src/pi_sled.scad`,
   following the conventions of the existing parts: named constants at the top,
   every tuned number carrying a comment saying *why*, a `PART=` style render
   switch if more than one object.
2. The rendered **`pi_sled.stl`** in `cad/tray_v1/`.
3. **Print settings** (the rest of this build runs 0.2mm layers, 15–20% infill,
   3 wall loops).
4. Any **reaming/finishing** steps the user should expect, called out explicitly
   — this build assumes holes come out tight.

Check `Simple: yes` in the OpenSCAD render output — that confirms a manifold,
printable mesh. (`Volumes: 2` is normal; it counts ambient space.)

## Success criteria

- Pi sits 5–10mm above the deck, rigid, no rock.
- Sled unbolts from the deck without removing the Pi from the sled.
- Pi does not thermally throttle after 30+ minutes of continuous running.
- Cables reach the board from the `[397, 60]` bore without strain.
- The whole thing disappears under a separately-printed decorative cover.

## Open questions for the user

- Confirm the measured hole spacing and board thickness on the actual Pi.
- Does the sled need to accommodate a HAT later (the Hailo-8L AI HAT+ is a
  possible Phase 3.5 purchase)? That would raise the stack ~15mm.
- Preference on deck attachment: M4 bolts through to the void, or VHB tape?
