# Halloween Build — the Talking Skull 💀

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

## Wiring (LD2410C or PIR — identical)

| Sensor pin | Pi 5 pin |
|---|---|
| VCC | 5V (pin 2) |
| GND | GND (pin 6) |
| OUT | GPIO 17 (pin 11) |

Any spare GPIO works — set `JARVIS_MOTION_PIN` to match.

## Running it

```bash
.venv/bin/python -m pip install gpiozero lgpio     # Pi 5 GPIO

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
