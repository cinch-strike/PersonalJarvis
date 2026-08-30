# Halloween Build — the Talking Skull 💀

> **Weekend plan (hardware has arrived) — see `WEEKEND-PLAN` section at the
> bottom for the ordered step-by-step.**


A standalone party centrepiece: a 3D-printed skull that **notices guests, calls
out to them, and holds a conversation** in character. No wake word — people just
walk up and talk.

It is Jarvis with a costume: same mic → Whisper → Claude → piper → speaker
pipeline, with a new input trigger (`motion`) and a new persona (`skull`).

## How it runs

```
presence detected (LD2410/PIR)
   → speaks a barker line ("I sense a living soul...")
   → listens (VAD: records until the guest stops talking)
   → Whisper → Claude (skull persona) → piper → speaker
   → up to N follow-up turns, so it's a real back-and-forth
   → cooldown (ignore presence) → re-arm for the next guest
```

## Shopping list

**Required (the only new part):**

| Part | Where | ~NZD | Notes |
|---|---|---|---|
| **HLK-LD2410C** 24GHz mmWave presence sensor | AliExpress / Amazon | $10–20 | Best option: detects a *standing* person, not just movement. 2–3 wk shipping from AliExpress. |
| *or* **Duinotech PIR module** `XC4444` | Jaycar NZ | $8.20 | Available today, click & collect. Motion-only (misses someone standing still) but works fine — start here if you don't want to wait. |
| Female-female jumper wires | Jaycar / Mindkits | ~$5 | 3 wires needed |

**⚠️ Do NOT buy** consumer smart-home sensors (e.g. Eve Motion Matter, $95.90 at
Jaycar). They speak Matter/Thread to a phone hub — there is no wire to the Pi's
GPIO and no way for our code to read them. We need a bare 3-pin module.

**Optional (jaw animation, phase 3):**

| Part | ~NZD | Notes |
|---|---|---|
| SG90 micro servo (Jaycar) | ~$10 | Moves the jaw |
| Red 5mm LEDs + 330Ω resistors | ~$5 | Eye sockets |
| [ChatterPi](https://hackaday.io/project/181612-chatterpi) | free | Drives the servo from audio volume so the jaw syncs to speech |

**Printed:** skull with hinged jaw (plenty of free models on Printables/Thingiverse
— search "animatronic skull hinged jaw"), plus a base to hide the Pi + speaker.

## Status: WORKING ✅

Presence-triggered skull confirmed running on the Pi — walk up, it calls out,
you talk back, it answers in character. Built with the Jaycar XC4444 PIR.
Autostarts on boot via systemd, so it runs standalone with nobody logged in.

### Final party config (as tuned)

Set in **both** `~/.bashrc` (manual runs) and `~/.config/jarvis/jarvis.env`
(the systemd service) — keep them in sync or the prop behaves differently
depending on how it was started (this bit us once with the voice).

```bash
JARVIS_PERSONA=skull
JARVIS_INPUT_MODE=motion
JARVIS_MOTION_PIN=17
JARVIS_CLAUDE_MODEL=claude-haiku-4-5              # fastest — matters live
JARVIS_WHISPER_MODEL=tiny.en                      # English-only: faster + more accurate
JARVIS_VAD_SILENCE_MS=700                         # snappier end-of-speech
JARVIS_PIPER_MODEL=$HOME/piper-voices/en_GB-alan-medium.onnx
JARVIS_PIPER_LENGTH_SCALE=1.3                     # slower = menacing
JARVIS_PIPER_PITCH=-3                             # deeper (needs sox)
JARVIS_AUDIO_DEVICE=0                             # ReSpeaker
JARVIS_AUDIO_CHANNELS=6
JARVIS_AUDIO_OUTPUT=plughw:3,0                    # Pebble
```

Scarier still: raise `LENGTH_SCALE` toward 1.4–1.5 and `PITCH` to -5. Past
about -6 it stops sounding like a voice and starts sounding like an artefact.

### Tray layout (as planned — 440 × 450 deck)

**Left and right always mean YOURS, standing at the front where the guests do**
— not the skull's anatomical left/right, which is mirrored. This matches the
CAD: in `tray.scad`, `(0,0)` is the front-left corner, x increases to your
right, y increases toward the back, and the `FL`/`FR`/`BL`/`BR` engravings on
the panel undersides follow the same convention. All coordinates below are
`[x, y]` in mm from that front-left corner.

**Bores already printed into the deck** (`tray.scad`, `cable_holes`):

| Bore | Position | Used for |
|---|---|---|
| `[180, 37]` | front, left of centre | PIR |
| `[255, 37]` | front, right of centre | mic / ReSpeaker |
| `[397, 60]` | right lane, front | **Pi 5** |
| `[397, 300]` | right lane, back | **breadboard** |
| `[80, 365]` | back left | **powerboard + 5V PSU** (was drawn for the speakers) |
| `[225, 330]` `[350, 330]` | back centre | spare / powerboard cords |

Plus a 40mm extension-cord exit slot centred on the back edge.

```
                    BACK — extension cord enters here
     ┌────────────────────┤ EXIT ├───────────────────────┐
     │                                                   │
     │  ╔═══════════════════════╗       ╔══════════════╗ │
     │  ║  POWERBOARD  +  5V    ║       ║   SPEAKERS   ║ │
     │  ║       ○ [80,365]      ║       ║   stacked ×2 ║ │
     │  ╚═══════════════════════╝       ║  ○ [397,300] ║ │
     │            ○[225,330]    ○[350,330] ╚═══════════╝ │
     │                                                   │
     │          ·  ·  ·  ·  ·  ·  ·      ┌─────────────┐ │
     │       ·        ◉ ←DRILL      ·    │             │ │
     │     ·        ┌────────────┐   ·   │ BREADBOARD  │ │
     │    ·         │   SKULL    │    ·  │  aft — out  │ │
     │    ·         │   MOUNT    │    ·  │  of reach   │ │
     │    ·         │ plate 100² │    ·  │             │ │
     │    ·         │  220, 225  │    ·  └─────────────┘ │
     │     ·        └────────────┘   ·        ╎ short    │
     │       ·                      ·         ╎ jumpers  │
     │          ·  ·  ·  ·  ·  ·  ·      ┌─────────────┐ │
     │        skull envelope ⌀200        │    PI  5    │ │
     │                                   │ GPIO◄  ►USB │ │
     │     ●[180,37]        ●[255,37]    │  ○ [397,60] │ │
     │       PIR              MIC        └─────────────┘ │
     └───────────────────────────────────────────────────┘
    LEFT                FRONT (guests)               RIGHT

  ○ = bore already printed in the deck     ◉ = drill this one ≈[245,290]
```

**Why the pieces sit where they do:**

- **Pi forward, breadboard aft.** The breadboard is the most fragile item on the
  tray — loose jumpers and a 470µF cap standing proud — and the front edge is
  where guests (and kids) reach. The sealed board with no exposed pins goes at
  the front; the fragile one goes behind it.
- **Pi and breadboard adjacent, not split.** Their interconnects (GND to pin 14,
  LED GPIO from pin 16) stay short and above deck, hidden inside butted covers.
  Route them under the deck instead and you need ~400mm jumpers — standard
  Dupont are 200mm.
- **Powerboard back-left, speakers back-right.** Balances the mass; otherwise
  every heavy item sits on the right half. The speakers take over the
  `[397,300]` bore for their USB cable.
- **Pi orientation:** long axis front-to-back, **GPIO edge inboard** (all its
  clients — PIR, servo signal, LED, breadboard — are that way), **USB edge
  outboard**, **USB-C power on the back short edge**. The gap between the Pi and
  the tray edge becomes the USB cable channel.
- Pull the right lane inboard to about **x 345–411**, don't centre components on
  the x=397 bores — a bore only needs to be *somewhere under* its cover, and
  hard against the tray edge leaves no room for a cover wall or a plug's strain
  relief.

### Cable routing — under the deck, always

> **Every component's cables leave downward through a bore that sits inside its
> own cover's footprint. Nothing crosses the top of the deck.**

That is what the 30mm leg void is for, and it means no cover needs a cable slot
cut in its side — the wires are hidden before they leave the cover.

⚠️ **There is no cable path through the skull mount.** `part_anchor_fixed` in
`skull_mount.scad` is a solid plate, a solid 26mm post and the socket cup —
nothing is bored through it. The servo and LED wires run up the **outside** of
the 40mm post and into the skull's base opening.

**The skull umbilical:** breadboard → down through `[397,300]` (inside its own
cover) → across the void → **up through a new bore at ≈`[245,290]`** → ~70mm
across the deck behind the skull → up the back of the post → into the skull.

That bore has to be drilled; nothing near the mount exists. 13mm spade bit or
step drill through 6mm PLA. `[245,290]` sits ~15mm clear behind the anchor
plate's back edge (y=275), 25mm off the x=220 seam so it lands cleanly inside
the `BR` panel, and clear of the seam bosses at `[220,330]` and `[240,225]`.
It is directly behind the skull, so it is invisible from the front.

⚠️ **Put a disconnect at the foot of the post.** The mount is designed so the
skull lifts straight off the ball, and with only ~1° of jaw travel you *will* be
taking it off to re-run `--jog-jaw`. Hard-wire both ends and you cannot. Leave
enough slack to lift the skull 150mm and set it beside the tray still live, plus
a labelled 6-way connector for full removal.

⚠️ **A USB-A plug will not pass a 13mm bore** — the connector is 12 × 4.5mm but
the overmoulding is typically 15–18mm. Three cables are USB (ReSpeaker, Pebble,
USB-C power). Either ream that bore to ~20mm, or give the covers a small
**skirt gap** at the deck so fat plugs pass under the cover edge. The skirt gap
doubles as the Active Cooler's air intake, which is needed anyway.

### Mounting the components to the deck

- **Pi 5:** on a printed sled, 5–10mm clear of the deck — never flat (underside
  solder joints, no airflow). See `COWORK_BRIEF_pi_sled.md`. The Pi's four M2.5
  holes are 58 × 49mm and ⚠️ **not centred on the board** — inset 3.5mm from
  three edges but 23.5mm from the USB/Ethernet end.
- **No foam under anything.** It insulates where airflow is needed, creeps under
  load so the board goes wonky and stresses the USB connectors, and does not
  locate the board against a knock. There is no vibration source to isolate —
  the servo is up in the skull on its own mount.
- **Breadboard:** its own adhesive backing is fine. Wipe the deck with isopropyl
  first (layer lines already cut the contact area), dry-position it and check the
  cover clears *before* peeling — it will not come up cleanly off printed PLA.
- **PA3713 and the 470µF cap** are the loosest items in that cluster and the
  PA3713 carries the only real current. Fix it down rather than letting it float
  on its wires; it can share the breadboard's cover.

### ⚠️ Check before the skull goes back on

`part_anchor_fixed` has **no relief cut for the tray's seam bosses**, and two of
them — at `[220,240]` and `[240,225]` — fall inside the mount plate's 100 × 100
footprint and stand 8mm proud of the deck. If those seam bolts are fitted, the
plate is rocking on two bosses instead of sitting flat, which is bad for the one
genuinely load-bearing joint on the build. Look underneath and confirm.

### As-built wiring (this rig)

| PIR pin (L→R) | Wire colour | Pi pin |
|---|---|---|
| VCC | 🟠 orange | 2 (5V) |
| OUT | 🟤 brown | 11 (GPIO17) |
| GND | 🔴 red | 6 (GND) |

⚠️ Note **red is GND here**, not power — counterintuitive if you re-trace it later.

### Background ambience ✅

A forest/graveyard loop plays while the prop is idle and **cuts the instant the
PIR fires** — before the barker line and before listening. Music under a
conversation would wreck Whisper accuracy and risk the prop hearing itself, and
the sudden silence when the skull notices you is the better effect anyway.

Setup used:
```bash
# on the Mac
scp ~/Downloads/ambience-scary-jungle.mp3 jarvis@<pi-ip>:~/
# on the Pi — aplay needs WAV; volume 0.3 keeps it background level
mkdir -p ~/sounds
ffmpeg -i ~/ambience-scary-jungle.mp3 -filter:a "volume=0.3" ~/sounds/graveyard.wav
```
Then `JARVIS_AMBIENCE_FILE=/home/jarvis/sounds/graveyard.wav` in **both**
`~/.bashrc` and `~/.config/jarvis/jarvis.env`.

Notes:
- The code loops the file itself, so a short clip (30s–2min) is plenty. A
  long file wastes SD space *and* never plays past the start, because the
  ambience restarts from 0:00 after every visitor.
- Pick a section that starts and ends at a similar level so the loop isn't
  obvious. Avoid distinct one-off events (a bell, a scream) — they get
  irritating every cycle.
- Startup logs either `Ambience: <file>` or `(ambience off: <reason>)`.
- `JARVIS_AMBIENCE_ENABLED=false` turns it off without removing the file.

### Voice: ElevenLabs (primary) → piper/alan (fallback) ✅

Cloud voice for realism, with a local voice behind it so a network blip can't
silence the prop mid-party. `--doctor` shows `TTS backend: elevenlabs→piper`.

```
JARVIS_ELEVENLABS_KEY=sk_...              # keep in jarvis.env only, never in chat
JARVIS_ELEVENLABS_VOICE=Tj9l48J9AJbry5yCP5eW
JARVIS_ELEVENLABS_TEMPO=1.15              # >1 faster; time-stretch, pitch preserved
```

**Cost:** a party is roughly 40k characters — pennies. Voice *quality* is the
thing to optimise, not price.

**Gotchas hit:**
- **Library voices need the Creator tier** (~$22/mo). The free tier only allows
  premade voices (Adam/Antoni/Arnold). Error is explicit:
  `"You need to be on the creator tier or above to use this voice."`
  Cancel after Halloween if it's a one-off.
- **Duplicate env lines break it.** Adding the key more than once made the shell
  variable contain a newline → `curl: (43) bad argument`, HTTP `000`. Check with
  `grep -c ELEVENLABS ~/.config/jarvis/jarvis.env` (should be 3).
- **Test tempo cheaply:** fetch the audio once with curl, then re-stretch it
  locally with `sox tempo` at several values — one generation, many auditions.
- For manual runs, load the service config instead of duplicating the key:
  `set -a; source ~/.config/jarvis/jarvis.env; set +a`

**Internet dependency:** Claude (the brain) *requires* it — no internet means no
replies at all. ElevenLabs degrades gracefully to alan. Party is at home on
reliable WiFi, so this is a non-issue here; it would matter at another venue.

### Piper voice settings (fallback, as tuned)

Alan at `JARVIS_PIPER_LENGTH_SCALE=1.2` — slightly slower, **no pitch shift**.
Pitch-shifting via sox was tried at -3 semitones and sounded artificial: it
moves the formants, so the voice reads as *processed* rather than deep. Slowing
alone gives "menacing but human", which is scarier. TTS laughs ("ha ha ha") were
also tried and sound comical — skip them; a recorded laugh WAV would be the way
if ever wanted.

### Servo jaw — WIRED AND WORKING ✅

Runs from its **own 5V supply**, not the Pi — a stalled jaw pulls ~700mA and
would otherwise risk browning out the Pi (which means SD corruption, not just a
twitchy jaw).

```
   5V adaptor ──→ PA3713 (DC socket + screw terminals)
                     │
      + screw ───────┴──→ breadboard RED rail ──┬── servo red
      − screw ────────────→ breadboard BLUE rail ┼── servo brown
                                                 ├── capacitor (470µF, long leg
                                                 │   red / striped leg blue)
                                                 └── black wire ──→ Pi pin 14 (GND)

   servo orange ─────────────────────────────────────→ Pi pin 12 (GPIO18)
```

⚠️ **Nothing from the red rail touches a Pi pin** — the Pi supplies only the
signal (pin 12) and the shared ground (pin 14).

⚠️ **The ground link is mandatory.** With a separate supply it matters *more*,
not less: the servo reads position from pulse timing measured against ground,
so without a shared reference it twitches randomly or ignores the Pi entirely.

**Use male-to-male jumpers** (Jaycar `WC6024`) — the first attempt used
hand-stripped stranded wire pushed into the rails, which was flimsy and
vibration-sensitive. A solid pin also clamps far better in the screw terminals
than stranded wire.

`JARVIS_JAW_ENABLED=true` and `JARVIS_SERVO_PIN=18` live in `jarvis.env`, so the
jaw works on boot without manual exports.

### LED eyes — reserved, not yet fitted

GPIO 23 (pin 16) → 330Ω → LED long leg; LED short leg → blue `−` rail. Both eyes
share one GPIO (two red LEDs ≈ 8mA, under the ~16mA per-pin limit).
⚠️ Resistors are **not optional** — an LED straight off a GPIO can destroy both.

### Original servo wiring plan (superseded by the above)

Code is written and pushed (`jaw.py`, `jarvis.py --test-jaw`), disabled until
`JARVIS_JAW_ENABLED=true`. Waiting on male-to-female jumpers (Jaycar `WC6028`).

All three servo wires land on the **outer** row, avoiding the PIR's pins:

| SG90 wire | Pi pin | Note |
|---|---|---|
| 🔴 red (power) | **4** (5V) | *not* pin 2 — PIR has that |
| 🟠 orange (signal) | **12** (GPIO18) | hardware-PWM capable |
| 🟤 brown (ground) | **14** (GND) | |

**Power decision:** fine off the Pi for a bare no-load bench test. For the final
build with a real jaw, prefer a separate 5V supply — a stalled SG90 pulls
~650–700mA continuously and can brown out the Pi (which risks SD corruption,
not just a twitchy jaw). If powering separately, **tie the supply ground to a Pi
GND pin** or the signal has no reference. A 470–1000µF cap across the servo's
power leads absorbs inrush spikes and makes Pi-power much safer.

Bench test (no skull needed):
```bash
sudo systemctl stop jarvis
export JARVIS_JAW_ENABLED=true
.venv/bin/python jarvis.py --test-jaw      # closed → open → closed → flap 5s
```
Then tune `JARVIS_JAW_CLOSED_ANGLE` / `JARVIS_JAW_OPEN_ANGLE` / `JARVIS_JAW_RATE_HZ`.

### Self-heal watchdog

**Failure seen in the field:** after ~5 days of uptime the ReSpeaker's USB audio
stream died. `sounddevice` kept returning empty buffers instead of erroring, so
the process stayed alive — systemd reported `active (running)` — while every
visitor got "nothing heard". A silently dead prop.

**Detection:** a working mic *cannot* return a second of audio in a millisecond;
reads block until samples exist. So a capture that comes back far faster than
real time means the device has stopped producing. After
`JARVIS_MAX_DEAD_CAPTURES` (default 3) consecutive such captures, Jarvis exits
non-zero and systemd restarts it with a fresh audio device. A single blip resets
the counter, so it won't restart over one hiccup.

Requires `Restart=on-failure` in the unit file (see `jarvis.service.example`).
To confirm it recovered, look for restarts in `journalctl -u jarvis`.

**Symptom to recognise:** log lines where `🎙 Listening` → `⏳ Processing` →
`(nothing heard)` all share the same timestamp. Real capture takes 1–15s.

### Gotchas that cost time (read before debugging)

1. **The systemd service steals the mic.** After any reboot it auto-starts and
   holds the ReSpeaker, so a manual run dies with
   `PortAudioError: Invalid number of channels`, and `query_devices` shows the
   ReSpeaker as **`0 in`** instead of `6 in`. Fix: `sudo systemctl stop jarvis`.
   (`arecord -l` showing `Subdevices: 0/1` is the same symptom.)
2. **Changing your router breaks WiFi silently.** Credentials are set at flash
   time; the Pi only re-reads them on boot, so it can keep working until the
   next power cycle and *then* vanish. Recovery: plug in Ethernet, `nmcli device
   wifi list`, then
   `sudo nmcli device wifi connect "SSID" password "..."`. Don't re-flash.
3. **Exports don't persist** across SSH sessions — they live in `~/.bashrc`.
   `jarvis.py --doctor` shows the *active* persona/model, so use it to confirm
   what's really loaded before debugging anything else.
4. **macOS `ping -W` is milliseconds**, not seconds (Linux is seconds) — a
   `-W1` network sweep from a Mac silently fails on every host.

## Wiring (LD2410C or PIR — identical)

| Sensor pin | Pi 5 pin |
|---|---|
| VCC | 5V (pin 2) |
| GND | GND (pin 6) |
| OUT | GPIO 17 (pin 11) |

Any spare GPIO works — set `JARVIS_MOTION_PIN` to match.

The Jaycar XC4444 outputs **3V HIGH / 0V LOW** — safely under the Pi's 3.3V GPIO
limit and well above its ~1.8V HIGH threshold, so it connects **directly**: no
level shifter, no divider.

### PIR (XC4444) setup gotchas

- **Delay pot → minimum (~0.3s).** It sets how long OUT stays HIGH after a
  trigger. Our software cooldown handles pacing; a long hardware delay leaves the
  pin HIGH and can re-fire at an empty room.
- **Sensitivity pot → start mid-range** (~3–7m). Tune so it catches people *at
  the table*, not across the room.
- **Jumper (if present) → "H"** (repeat trigger) — better for presence.
- **Warm-up:** PIR self-calibrates for ~60s after power-up and may fire randomly.
  Expected, not a bug.
- PIR senses *movement*, not presence — someone standing perfectly still can drop
  out. Fine for a party; swap to LD2410 (no code change) if it bothers you.

## LED eyes

| | Pi 5 pin |
|---|---|
| GPIO 23 | pin 16 |
| GND | blue `−` rail (common with the Pi and the servo supply) |

Each LED gets **its own 470Ω resistor** (`yellow-violet-brown-gold`) between
GPIO 23 and its anode; cathodes go to the `−` rail. Two LEDs on one shared
resistor would not split current evenly — small differences between them mean
one hogs the current, runs brighter, and dims the other.

Both eyes share one GPIO. They'd always match anyway, and two red LEDs at ~4mA
each stay well under the Pi's ~16mA per-pin limit.

Three states, because the *change* is what reads as "it noticed you" far more
than raw brightness: dim while waiting, brighter the instant the PIR fires,
pulsing while speaking. Test with `python jarvis.py --test-eyes`.

## Calibrating the jaw

Use `python jarvis.py --jog-jaw` — arrow keys (or `w`/`s`) move the servo a
degree at a time, `m` marks a position, and it prints a suggested config on
exit. Measure against the *mounted* linkage; the numbers are meaningless
otherwise.

The servo stops driving a second after each move. This matters: a servo told to
**hold** a position hunts around its deadband, and a mounted jaw amplifies that
sub-degree jitter into obvious chatter that is easily mistaken for a linkage or
power fault. Between moves it should be silent.

### The leverage trap

```
jaw rotation = servo rotation × (horn radius ÷ distance from jaw hinge to cable)
```

On this build the whole jaw travel happens in **1° of servo rotation** — the
ratio is far too high. Consequences worth knowing:

- The flap's built-in variation (55–100% of span) falls below the servo's
  deadband, so the jaw reads as **binary open/closed** rather than varied.
- Servo dither becomes a large fraction of travel. Early on this looked like a
  loose mount or a failing supply; it was neither.
- There's no room to stop fractionally short of contact, so the teeth clack.
  (Which turned out to sound good — a clacking skull is on-theme.)

To improve it, get **more servo rotation per unit of jaw movement**: move the
cable *further from the jaw hinge*, or *closer to the horn's centre*. Aim for
15–30° of travel between open and closed.

⚠️ A **longer horn makes it worse**, not better — more cable pull per degree
means fewer degrees used. The instinct to fix this with a bigger horn is
backwards.

### MG90S vs SG90

Drop-in electrically (**brown = GND, red = 5V, orange = signal**) and the same
28mm screw spacing, but slightly taller and ~50% heavier. The measurements in
SERVO_MEASUREMENTS.md are from the SG90 — dry-fit before screwing anything down.

⚠️ Metal gears do **not** strip. The plastic SG90's gears were acting as a
mechanical fuse; with an MG90S, whatever gives will be your linkage or the
printed jaw instead. Bring travel limits up gradually and stop at the first
resistance.

## Running it

```bash
# Pi 5 GPIO. lgpio compiles from C source — install its build deps first or
# pip fails with "command 'swig' failed: No such file or directory".
sudo apt install -y swig python3-dev liblgpio-dev
.venv/bin/python -m pip install gpiozero lgpio

export JARVIS_INPUT_MODE=motion
export JARVIS_PERSONA=skull
export JARVIS_MOTION_PIN=17
export JARVIS_AUDIO_DEVICE=0
export JARVIS_AUDIO_CHANNELS=6
export JARVIS_AUDIO_OUTPUT=plughw:3,0
export JARVIS_CLAUDE_MODEL=claude-haiku-4-5      # fastest — matters at a party

.venv/bin/python jarvis.py --doctor    # expect: Motion sensor ✅
.venv/bin/python jarvis.py
```

## Tuning for a party

| Symptom | Fix |
|---|---|
| Talks over itself in a crowd | Raise `JARVIS_MOTION_COOLDOWN` (default 20s) |
| Too slow to reply | `JARVIS_CLAUDE_MODEL=claude-haiku-4-5` (biggest win) |
| Cuts guests off mid-sentence | Lower `JARVIS_VAD_SILENCE` |
| Mishears in party noise | Expected — the persona is told to answer mysteriously rather than admit it, so it never breaks character |
| Conversations drag on | Lower `JARVIS_MOTION_FOLLOW_UPS` (default 4) |

Custom call-out lines: `JARVIS_BARKER_LINES="Line one | Line two | Line three"`.

## Phases

1. **Persona + motion** — works on existing hardware today; skull optional.
2. **Print the skull**, mount Pi/mic/speaker in the base.
3. **Jaw servo + ChatterPi** for lip-sync.
4. **Red LED eyes**, fog machine, etc.

Each phase demos on its own — even stopping at (1) gives you a talking prop.

---

## WEEKEND-PLAN — wiring up the sensor

Do these in order. Each step is verifiable before moving on.

### 0. Where am I? (always start here)

```bash
ssh jarvis@jarvis.local
sudo systemctl stop jarvis            # free the mic (the service grabs it at boot)
cd ~/PersonalJarvis && git pull       # get the latest code
cd jarvis/phase1
.venv/bin/python jarvis.py --doctor   # shows persona, model, and every backend
```

`--doctor` is the "what's actually loaded?" answer — it prints the active
persona and its greeting, the Claude model, TTS/input mode, and what's missing.

### 1. Load the settings (they don't survive a new SSH session)

```bash
export JARVIS_PERSONA=skull
export JARVIS_CLAUDE_MODEL=claude-haiku-4-5
export JARVIS_AUDIO_DEVICE=0
export JARVIS_AUDIO_CHANNELS=6
export JARVIS_AUDIO_OUTPUT=plughw:3,0
export JARVIS_OWW_THRESHOLD=0.6
```

Re-run `--doctor`: **Persona** should say `skull`, **Claude model** `claude-haiku-4-5`.

### 2. Finish the GPIO install (blocked last time on a missing `swig`)

```bash
sudo apt install -y swig python3-dev liblgpio-dev
.venv/bin/python -m pip install lgpio
```

### 3. Power OFF, then wire the PIR

**Shut down before touching GPIO pins:** `sudo shutdown -h now`, wait for the LED
to stop, unplug power.

| XC4444 pin | Pi 5 pin |
|---|---|
| VCC | 5V — physical pin 2 |
| OUT | GPIO 17 — physical pin 11 |
| GND | GND — physical pin 6 |

Set the PIR's **delay pot to minimum**, sensitivity to mid (see gotchas above).
Power back up.

### 4. Test the sensor alone (before involving Jarvis)

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

Wave → `MOTION`. Ctrl+C to stop. **Don't continue until this works** — it isolates
wiring problems from software ones.

### 5. Run the prop in motion mode

```bash
export JARVIS_INPUT_MODE=motion
.venv/bin/python jarvis.py --doctor   # expect: Motion sensor ✅
.venv/bin/python jarvis.py
```

Walk up → it should call out → talk back to it → it answers → cooldown.

### 6. Tune (see the party table above)

Most likely knobs: `JARVIS_MOTION_COOLDOWN` (too chatty),
`JARVIS_MOTION_FOLLOW_UPS` (conversations drag), PIR sensitivity pot (triggers
from too far away).

### 7. Make it permanent (once happy)

Add the exports to `~/.config/jarvis/jarvis.env` and
`sudo systemctl restart jarvis` so it boots straight into party mode.

**Later / optional:** print the skull, mount the servo, add ChatterPi jaw sync,
red LED eyes.
