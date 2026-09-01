# Rewiring Plan — one subsystem at a time, tested as you go

*Written after the Pi and breadboard were mounted to the tray. All wiring,
the capacitor and the LED resistors were removed to make mounting easier, so
this rebuilds the electronics from bare boards.*

**State when this was written:** Pi mounted, breadboard mounted (adhesive),
USB-C power connected and routed down through the deck. Nothing else connected.

**Related:** `HALLOWEEN.md` (as-built wiring, tray layout, cable routing),
`CAD_HANDOVER.md` (the CAD side).

---

## The principle

Every stage adds **one** subsystem and ends with a test that proves that
subsystem alone. If a stage fails, the fault is in what you just added — you
never have to bisect the whole rig. Do not skip ahead to "wire it all and see".

Glue happens **last**, after a full run passes. Nothing gets glued before then.

---

## Master pin map — the single source of truth

| Pi physical pin | BCM | Wire | Goes to |
|---|---|---|---|
| **2** | 5V | 🟠 orange | PIR VCC |
| **6** | GND | 🔴 **red** | PIR GND |
| **11** | GPIO17 | 🟤 brown | PIR OUT |
| **12** | GPIO18 | 🟠 orange | Servo signal |
| **14** | GND | ⚫ black | Breadboard **blue** (−) rail |
| **16** | GPIO23 | — | LED feed → 470Ω each → LED anodes |

⚠️ **On this PIR, red is GROUND, not power.** Counterintuitive and easy to get
wrong when rebuilding from memory. Orange is VCC.

⚠️ **Nothing from the red (+5V) rail ever touches a Pi pin.** The Pi supplies
only the signal (pin 12) and the shared ground (pin 14). The servo's power comes
from its own supply.

**Breadboard:**

| From | To |
|---|---|
| PA3713 **+** screw terminal | red (+) rail |
| PA3713 **−** screw terminal | blue (−) rail |
| 470µF cap **long leg** | red rail |
| 470µF cap **striped leg** | blue rail |
| Servo 🔴 red | red rail |
| Servo 🟤 brown | blue rail |
| LED cathodes (short leg) ×2 | blue rail |
| Blue rail | Pi pin 14 |

⚠️ **The shared ground (pin 14) is mandatory**, and matters *more* with a
separate supply, not less. The servo reads position from pulse timing measured
against ground; with no shared reference it twitches randomly or ignores the Pi.

---

## Before every session at the bench

```bash
ssh jarvis@jarvis.local
sudo systemctl stop jarvis     # the service grabs the mic AND the GPIO pins at boot
cd ~/PersonalJarvis && git pull
cd jarvis/phase1
set -a; source ~/.config/jarvis/jarvis.env; set +a   # loads the API key + all flags
.venv/bin/python jarvis.py --doctor
```

⚠️ **Source `jarvis.env`, don't retype exports.** `JARVIS_JAW_ENABLED` and
`JARVIS_EYES_ENABLED` both default to **false**. If they're off, `--test-jaw`
and `--test-eyes` fail with `❌ Could not open servo:` and a **blank reason** —
which looks exactly like a wiring fault and will send you chasing a problem that
isn't there.

⚠️ **Power the Pi off and unplug it before touching GPIO pins.** Not just
shutdown — `sudo shutdown -h now`, wait for the LED to stop, then pull the plug.

---

## Stage 0 — Drill everything first

**Do all drilling before any wiring exists.** Swarf and vibration around a
populated breadboard is how you end up with an intermittent fault you can't find.

You need holes for the two USB runs (ReSpeaker at the front, Pebble at the
back-right), plus the skull umbilical bore at ~`[245,290]` if it isn't done yet
(see `CAD_HANDOVER.md`).

1. **Size from the actual plug, not the spec.** A USB-A connector is 12 × 4.5mm
   but the overmoulding is typically 15–18mm wide. Measure yours, add 3–4mm.
   **Expect ~20–22mm**, not the 13mm the existing bores use.
2. **Use a step drill.** A twist bit snatches in PLA and splits it along a layer
   line. Go slow, support the underside with scrap.
3. **Deburr and chamfer both faces.** A sharp PLA edge will chafe through a USB
   cable's jacket over months of a prop being moved around.
4. **Vacuum the swarf** out of the leg void before anything else goes in.

Dry-fit every plug through its hole before moving on.

---

## Stage 1 — Build and test the jumper extensions (bench, nothing installed)

This is the highest-value step and the best use of the multimeter. A bad
home-made extension is the single hardest fault to find later, because it
usually *mostly* works.

For each extension you make:

1. **Continuity test end to end** — should beep.
2. **Test against its neighbours** — pick two adjacent conductors in the same
   bundle and confirm they do **not** beep to each other. This catches a crimp
   whisker bridging two pins, which is invisible and behaves like a random fault.
3. **Tug test** — a firm pull on the joint. Better it fails now than inside a
   glued loom.
4. **Label both ends** while you still know what it is. Masking tape and a pen.

Only once every extension passes do you start installing.

> You have plenty of jumpers now — make them **longer than you think**. Slack
> costs nothing; a wire under tension pulls out of a breadboard eventually, and
> you can't add length once the loom is glued.

---

## Stage 2 — USB: mic and speaker

Lowest risk, no GPIO involved. Get it done and out of the way.

1. Power off. Route the ReSpeaker cable to the front position and the Pebble
   cable to the back-right, through the new holes, under the deck.
2. **Note which physical USB port each goes into** and keep it that way. See the
   warning below.
3. Power up, then:

```bash
sudo systemctl stop jarvis
lsusb                                  # XMOS/Seeed = ReSpeaker present
arecord -l                             # capture devices
aplay -l                               # playback devices — find the Pebble's card
.venv/bin/python -c "import sounddevice; print(sounddevice.query_devices())"
```

⚠️ **ALSA card numbers depend on enumeration order.** `JARVIS_AUDIO_DEVICE=0`
(ReSpeaker) and `JARVIS_AUDIO_OUTPUT=plughw:3,0` (Pebble) were correct for the
old cabling. Plugging into different ports, or in a different order, can
renumber them. Check the output above against those values, and if they've
moved, update **both** `~/.bashrc` and `~/.config/jarvis/jarvis.env` — keeping
those two in sync has bitten this build before.

4. Confirm `--doctor` shows the audio backends happy.

---

## Stage 3 — PIR (3 wires, simplest GPIO)

Power off before wiring.

| PIR pin (L→R) | Colour | Pi pin |
|---|---|---|
| VCC | 🟠 orange | 2 (5V) |
| OUT | 🟤 brown | 11 (GPIO17) |
| GND | 🔴 red | 6 (GND) |

**Meter check before you connect OUT to the Pi:** wire only VCC and GND, power
up, and measure OUT against GND. It should read **~0V idle and ~3V on motion**.
That confirms the module is alive *and* that it's safe for the Pi's 3.3V GPIO
before you connect it to a pin you can't replace.

Then connect OUT to pin 11, power up, and test:

```bash
.venv/bin/python -c "
from gpiozero import MotionSensor
p = MotionSensor(17)
print('Waiting ~60s for PIR warm-up, then wave at it...')
while True:
    p.wait_for_motion(); print('  MOTION')
    p.wait_for_no_motion(); print('  clear')
"
```

⚠️ **The PIR self-calibrates for ~60s after power-up** and may fire randomly
during that. Expected, not a fault. Also confirm the **delay pot is at minimum**
and sensitivity mid-range — a long hardware delay leaves the pin HIGH and
re-fires at an empty room.

**Don't continue until you see `MOTION` on demand.**

---

## Stage 4 — Breadboard power rails and the capacitor

Still nothing connected to the Pi from the rails.

1. ⚠️ **Check the rail continuity first.** Most full-size breadboards **split
   the power rails at the centre**. If you're spreading components out, you will
   straddle that break and half your board will have no power. Beep from one end
   of the red rail to the other — if it doesn't, bridge the gap with a jumper.
   Do the same for blue. **This is the classic one, and it looks like a dead
   component.**
2. Wire the PA3713's **+** screw terminal to the red rail, **−** to blue. Use
   solid pins in the screw terminals, not stranded wire — it clamps far better.
3. Power up the 5V adaptor **with nothing else connected**. Meter across the
   rails: expect **~5V, red positive**. Confirm the polarity now.
4. **Power down**, then fit the 470µF cap: **long leg → red rail, striped leg →
   blue rail**.

   ⚠️ An electrolytic capacitor fitted backwards will vent — sometimes loudly.
   This is the one step where getting polarity wrong is more than an
   inconvenience. Verify with the meter, then verify again by eye.

5. Power up. Rails should still read ~5V and the cap should stay cool. Anything
   warm means it's in backwards — kill power immediately.
6. **Power down.** Connect blue rail → Pi pin 14 with the black wire. Meter
   continuity from the blue rail to pin 14 to confirm.

**On spreading things out:** good idea for the resistors, but keep the **470µF
cap physically close to where the servo taps the rails**. Its whole job is
absorbing the servo's inrush; a long thin rail run between the cap and the load
defeats it.

---

## Stage 5 — Servo (jaw)

| Servo wire | To |
|---|---|
| 🔴 red | breadboard red (+) rail |
| 🟤 brown | breadboard blue (−) rail |
| 🟠 orange | Pi pin 12 (GPIO18) |

⚠️ **Run the first test with the jaw linkage DISCONNECTED.** This is an MG90S
now — metal gears **do not strip**. The plastic SG90's gears used to act as a
mechanical fuse; with metal, whatever gives will be your linkage or the printed
jaw instead.

```bash
sudo systemctl stop jarvis
set -a; source ~/.config/jarvis/jarvis.env; set +a
.venv/bin/python jarvis.py --test-jaw     # closed → open → closed → flap 5s
```

Then reconnect the linkage and **re-run the calibration** — you've remounted
things and the numbers are meaningless against a linkage that has moved:

```bash
.venv/bin/python jarvis.py --jog-jaw      # arrow keys / w,s · m marks · prints config on exit
```

⚠️ **There is only ~1° of servo travel between open and closed** on this build.
A millimetre of movement in the mount can put "closed" outside the range. Bring
the travel limits up gradually and stop at the first resistance.

The servo deliberately stops driving a second after each move — **silence
between moves is correct**, not a fault. A servo told to hold hunts around its
deadband and the mounted jaw amplifies that into obvious chatter.

---

## Stage 6 — LED eyes

⚠️ **Resistors are not optional.** An LED straight off a GPIO can destroy both.

⚠️ **Each LED gets its OWN resistor.** Two LEDs sharing one resistor don't split
current evenly — small differences mean one hogs it, runs bright, and dims the
other.

**Which value?** `HALLOWEEN.md` contradicts itself — one section says 330Ω, the
detailed section says **470Ω** with the colour code `yellow-violet-brown-gold`.
**Measure the ones you pulled out** with the meter and put those back; they're
what worked in the dry run. Then fix whichever line in `HALLOWEEN.md` is wrong.

Wiring: Pi pin 16 (GPIO23) → 470Ω → LED **long leg** (anode). LED **short leg**
(cathode) → blue (−) rail. Both eyes share GPIO23.

```bash
.venv/bin/python jarvis.py --test-eyes    # off → idle → alert → pulsing → idle
```

---

## Stage 7 — Full integration

```bash
.venv/bin/python jarvis.py --doctor       # everything green, persona = skull
.venv/bin/python jarvis.py                # walk up, talk to it
```

Watch for: motion → ambience cuts → eyes brighten → barker line → listens →
answers with jaw and eyes in sync → cooldown.

If speech recognition is worse than before, that's a mic *placement* problem,
not a wiring one — check the ReSpeaker has a clear opening to the front and that
`JARVIS_VAD_SILENCE_MS` hasn't been left at a value tuned for a different room.

---

## Stage 8 — Dress and glue (only now)

1. **Never glue a connector or a breadboard insertion.** Glue the cable a few cm
   back from the joint so you can still pull a jumper. A glued-in Dupont end is
   a destroyed breadboard hole.
2. **Strain-relieve where cables pass through the deck bores** — a blob each
   side of the hole takes the load off the connector at the far end.
3. **Leave the skull umbilical unglued** at the disconnect point. You will be
   taking the skull off to re-jog the jaw.
4. ⚠️ **Keep glue away from the Active Cooler's airflow** and off the fan.
5. Hot glue on PLA holds well but tears the printed surface when removed. Keep
   it off anything you may want to reposition.

---

## Finally — the one that's easiest to forget

```bash
sudo systemctl enable jarvis
systemctl is-enabled jarvis      # must print: enabled
```

`jarvis` was **disabled at boot** during wiring so it wouldn't interrupt. If it
stays disabled, the prop does nothing when powered up on the night, and there's
no error to see — it simply never starts.

---

## Multimeter quick reference

| Check | How | Expect |
|---|---|---|
| Extension continuity | beep, end to end | beeps |
| Extension shorts | beep, adjacent conductors | **no** beep |
| Breadboard rail break | beep, rail end to end | beeps (else bridge it) |
| Rail voltage | DC volts across rails, no load | ~5V, red positive |
| Cap polarity | before fitting — confirm which rail is + | long leg to + |
| PIR output | DC volts, OUT to GND, VCC+GND only | ~0V idle, ~3V on motion |
| LED resistors | resistance, out of circuit | 470Ω (or whatever you removed) |
| Shared ground | beep, blue rail to Pi pin 14 | beeps |

⚠️ **Never measure resistance on a powered circuit** — power down first, and
take the component out of the board if you want a trustworthy reading.
