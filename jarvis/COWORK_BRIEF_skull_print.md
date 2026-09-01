# Cowork Brief — 3D-Printed Talking Skull (Halloween prop)

Hand this whole file to Cowork. It describes what to design and the hard
constraints it must satisfy.

---

## What this is

A Halloween party centrepiece: a skull that detects guests walking up, calls out
to them, and holds a spoken conversation in character. **The electronics and
software are already built and working** — this brief is only about the
**physical build**: a 3D-printed skull with a servo-driven moving jaw that
houses the existing hardware.

Audience is a mixed party of adults and children. It sits on a table at roughly
chest/eye height, and people approach it from the front, typically 0.5–1.5m away.

## What already works (do not redesign)

| Function | Hardware |
|---|---|
| Brain | Raspberry Pi 5 (8GB) + official Active Cooler |
| Hearing | **ReSpeaker Mic Array v2.0** (Seeed 107990053, XMOS XVF-3000) — round USB board, Micro-B connector, USB ID `2886:0018` |
| Voice | Creative Pebble V3 speaker (USB powered, 3.5mm in) |
| Presence detection | Jaycar XC4444 PIR motion sensor |
| Jaw (to add) | TowerPro SG90 micro servo, 9g, 1.6 kg·cm |

The software drives everything over USB/GPIO. The print must **house** these,
not replace them.

⚠️ **Not the "ReSpeaker 4-Mic Array"** — that is a different Seeed product, a
GPIO HAT that bolts to the Pi's header with no USB at all. This build uses the
round **Mic Array v2.0** USB board. ⚠️ **Measure the actual board** before
designing its opening; this project has already lost three reprints to a
trusted-but-wrong spec (lesson 2 in `CAD_HANDOVER.md`).

---

## The servo — design around these numbers

**TowerPro SG90 (Jaycar YM2758), 9g, 1.6 kg·cm @ 4.8V, ~90° travel**

| Property | Value |
|---|---|
| Body size | ~22.8 × 12.2 × 22.5 mm (plus mounting tabs) |
| Height incl. spline | ~28.5–29 mm |
| Mounting tabs | Two, one each side; ~32.5 mm between screw-hole centres |
| Screw holes | ~2 mm dia (M2 self-tappers) |
| Output spline | 21-tooth, ~4.8 mm dia |
| Cable | 3-wire, ~150 mm — needs a routing path |

⚠️ **This unit is a 90° servo, not 180°.** Design the linkage so the jaw's full
open/close falls comfortably inside 90° of rotation. **Ask the user to measure
their actual servo before finalising** — clone dimensions vary by a millimetre
or two, and a servo pocket that's 1mm too small is a reprint.

## Jaw mechanism

The jaw only needs to swing about **20–30°** — that reads as talking. Two
options; **recommend the simpler one for a first build:**

**Option A — direct drive (recommended)**
The servo spline *is* the jaw pivot. Servo sits inside the cranium at the jaw
hinge position, horn bolted to the jaw. Fewest parts, nothing to bind, easiest
to debug. Downside: constrains where the servo can sit.

**Option B — pushrod linkage**
Servo mounted higher inside the cranium, a short rod runs down to a tab on the
jaw. Hides the servo better and allows a more natural hinge line, but adds a
linkage that can bind or rattle.

Requirements either way:
- Jaw must **fall closed under its own weight** if the servo is unpowered — an
  open-mouthed skull looks broken.
- **No binding at either travel extreme.** Include hard stops so a mis-configured
  servo can't drive the jaw past its limit and strip its gears.
- Keep the jaw **light** — the SG90 has modest torque and a heavy jaw will
  stutter, buzz, or brown out the Pi. Print it sparse/hollow.
- Servo pocket should be a **friction fit plus screw holes**, so it can't shift.

## Housing requirements

- **Raspberry Pi 5**: 85 × 56 mm board. With the Active Cooler fitted, allow
  ~30 mm height and **airflow** — the cooler needs to breathe or the Pi throttles
  under Whisper transcription. Vents required; a sealed skull will overheat.
- **Cable access**: USB-C power in, and 4 USB-A ports must remain reachable
  (mic + speaker plug in). A removable base plate or rear hatch is strongly
  preferred over a fully-sealed print — **assume it will be opened repeatedly.**
- **Microphone**: the ReSpeaker must have a **clear opening to the front**.
  Burying it behind plastic will wreck speech recognition, which is the whole
  point of the prop. Treat mic sightline as a hard requirement.
- **Speaker**: the Pebble is a separate box — it can sit beside the skull or be
  hidden in a base. Its 3.5mm cable needs a route.
- **PIR sensor**: needs an **unobstructed forward view**, ideally mounted in an
  eye socket or the forehead. It detects through nothing — no plastic in front
  of the dome. Its board is small (~32 × 24 mm) with a domed lens.
- **Cable management**: paths for servo (3 wires to GPIO), PIR (3 wires to GPIO),
  and two USB cables.

## Print constraints

- FDM printer (Bambu Lab P2S), PLA is fine — this is indoor, no heat load.
- Design for **printability**: minimise supports, split into parts if needed
  (cranium / jaw / base are natural splits), and prefer flat mating faces.
- The user is **new to 3D printing** — favour simple, forgiving geometry and
  generous tolerances over intricate detail. Assume first-time assembly.
- Fasteners: M2 self-tappers for the servo; specify any others explicitly.

## Deliverables from Cowork

1. Recommendation on **where to source the base skull model** — a remixable
   existing model (Printables/Thingiverse "articulated skull", "animatronic
   skull hinged jaw") is almost certainly better than modelling from scratch.
   Name specific candidates if possible.
2. Guidance on **modifying it** for: the SG90 pocket, the jaw hinge, the PIR
   mount, mic opening, Pi bay, and cable routes.
3. **Print settings** — layer height, infill, supports, orientation per part.
4. **Assembly order**, including where the user should test-fit before committing
   to a full print.
5. A **staged plan** so partial progress is still usable — e.g. print and test
   the jaw mechanism alone before printing a full-size skull.

## Success criteria

- Jaw visibly moves in time with speech; motion is obvious from 2m away.
- PIR reliably triggers when someone approaches from the front.
- Mic still transcribes speech accurately with the skull fully assembled.
- Pi doesn't thermally throttle after 30+ minutes of continuous running.
- The Pi can be removed and re-inserted without destroying the print.

## Open questions for the user

- Full-size (~human, ~200mm) or smaller/stylised?
- Realistic bone finish, or cartoonish/friendly (kids at the party)?
- Should the Pebble speaker hide inside a base, or sit separately?
- Light-up eyes wanted? (LEDs are a likely phase 2 — leave space if cheap to do.)
