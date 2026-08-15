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

### As-built wiring (this rig)

| PIR pin (L→R) | Wire colour | Pi pin |
|---|---|---|
| VCC | 🟠 orange | 2 (5V) |
| OUT | 🟤 brown | 11 (GPIO17) |
| GND | 🔴 red | 6 (GND) |

⚠️ Note **red is GND here**, not power — counterintuitive if you re-trace it later.

### Servo jaw — planned wiring (not yet fitted)

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
