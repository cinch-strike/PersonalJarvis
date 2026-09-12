"""
Boot-time self test — does the hardware actually WORK, not just resolve?
───────────────────────────────────────────────────────────────────────
`--doctor` checks *selection*: which backends were chosen, whether a key is
set, whether a module imports. That is genuinely useful and it is not this.

The gap between the two bit us on 9 Sep 2026: `--doctor` reported all-green
while the prop was completely silent, because the Pebble had been knocked into
a mode where it still enumerated on USB and still accepted audio — ALSA
reported success the whole way down — and simply made no sound.

So this module *exercises* devices instead of inspecting config: it opens the
speaker and pushes a buffer at it, captures real audio off the mic and checks
the samples aren't dead, and opens the GPIO pins it can open safely.

⚠️ HONEST LIMITS — read before trusting a green run:
  · A speaker in the wrong input mode still passes. The Pi cannot hear itself.
  · A loose barrel plug on the servo supply is invisible without moving the
    servo, which this deliberately will not do.
  · The PIR is only opened, never triggered — nothing can wave at it at boot.
  So GREEN MEANS "nothing is missing or dead", NOT "the prop works". The
  pre-party checklist in HALLOWEEN.md is what actually catches those; it needs
  a human because only a human can hear a tone and see a jaw move.

Wired into jarvis.service as `ExecStartPre=-`, so the result is logged loudly
on every boot but a failure never stops the prop starting. A half-working prop
beats no prop on the night.

Run by hand:  python jarvis.py --selftest
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time

import config

# A capture that returns far faster than real time means the device stopped
# producing samples — a working mic BLOCKS until they exist. Same reasoning as
# the runtime watchdog in input_trigger.py, which is how we caught the
# ReSpeaker's USB stream dying silently after ~5 days of uptime.
CAPTURE_S = 1.0
MIN_ELAPSED_RATIO = 0.5


def _line(ok, label, detail):
    mark = "✅" if ok else "❌"
    print(f"   {mark} {label:<16} {detail}")
    return ok


def _card_name(device: str):
    """Pull the ALSA card out of a device string like plughw:CARD=V3,DEV=0."""
    m = re.search(r"CARD=([A-Za-z0-9_]+)", device or "")
    return m.group(1) if m else None


def force_volume():
    """Set the ALSA playback volume. Returns (ok, detail) and never raises.

    ⚠️ Called from BOTH the boot self test and the main process, on purpose.
    Setting it once at ExecStartPre is not enough: wireplumber starts after us,
    manages mixer state itself, and restores its own saved value — the self test
    was observed setting 100% and the card reading 61% a moment later. The
    second call, once the prop is actually running, lands after that.
    """
    if not config.OUTPUT_VOLUME:
        return True, "not managed (JARVIS_OUTPUT_VOLUME unset)"
    card = _card_name(config.AUDIO_OUTPUT or "")
    if not card:
        return False, "cannot find a CARD= name in JARVIS_AUDIO_OUTPUT"
    if shutil.which("amixer") is None:
        return False, "amixer not installed (apt install alsa-utils)"
    try:
        r = subprocess.run(["amixer", "-c", card, "sset", "PCM", config.OUTPUT_VOLUME],
                           capture_output=True, text=True, timeout=10)
    except Exception as e:  # noqa: BLE001
        return False, str(e)
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        return False, err[-1] if err else "amixer failed"
    now = re.search(r"\[(\d+%)\]", r.stdout)
    return True, f"card {card} set to {now.group(1) if now else config.OUTPUT_VOLUME}"


def _set_volume() -> bool:
    ok, detail = force_volume()
    return _line(ok, "Volume", detail)


def _check_speaker() -> bool:
    """Open the playback device and push silence at it.

    Silence, not a tone: this runs unattended at boot and nobody wants the prop
    beeping at 3am. That also means it can only prove the device OPENS.
    """
    dev = config.AUDIO_OUTPUT
    if not dev:
        return _line(True, "Speaker", "system default (no JARVIS_AUDIO_OUTPUT set)")
    if shutil.which("aplay") is None:
        return _line(False, "Speaker", "aplay not installed (apt install alsa-utils)")
    try:
        r = subprocess.run(
            ["aplay", "-D", dev, "-t", "raw", "-f", "S16_LE",
             "-r", "48000", "-c", "2", "-d", "1", "/dev/zero"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception as e:  # noqa: BLE001 — a self test must never crash the boot
        return _line(False, "Speaker", f"{dev} — {e}")
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        return _line(False, "Speaker", f"{dev} — {err[-1] if err else 'open failed'}")
    return _line(True, "Speaker", f"{dev} opened and accepted audio")


def _check_mic() -> bool:
    """Capture real audio and prove the samples are alive.

    Two failure modes, both silent in the field: the device vanishing, and the
    device staying open while returning empty buffers forever.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as e:  # noqa: BLE001
        return _line(False, "Mic", f"import failed — {e}")

    dev, rate = config.AUDIO_DEVICE, config.SAMPLE_RATE
    ch = config.AUDIO_CHANNELS
    try:
        start = time.monotonic()
        frames = sd.rec(int(CAPTURE_S * rate), samplerate=rate,
                        channels=ch, device=dev, dtype="int16")
        sd.wait()
        elapsed = time.monotonic() - start
    except Exception as e:  # noqa: BLE001
        return _line(False, "Mic", f"device {dev!r} — {e}")

    if elapsed < CAPTURE_S * MIN_ELAPSED_RATIO:
        return _line(False, "Mic",
                     f"returned {elapsed:.2f}s of audio in {elapsed:.2f}s — "
                     "device is not producing samples")
    peak = int(np.abs(frames).max()) if frames.size else 0
    if peak == 0:
        return _line(False, "Mic", "captured only silence — check the mic is live")
    return _line(True, "Mic", f"{dev!r} captured {ch}ch, peak {peak}")


def _check_gpio() -> bool:
    """Open the pins we can open without moving anything.

    ⚠️ GPIO 18 is deliberately NOT touched. Opening it as a servo attaches it,
    and attaching can snap the horn toward 0° (see jog.py) — which with the jaw
    linkage glued on breaks the linkage or the printed jaw. There is no safe
    unattended servo test, so we report it as unverified and mean it.
    """
    ok = True
    try:
        from gpiozero import MotionSensor, PWMLED
    except Exception as e:  # noqa: BLE001
        return _line(False, "GPIO", f"gpiozero unavailable — {e}")

    try:
        pir = MotionSensor(config.MOTION_PIN)
        pir.close()
        _line(True, "PIR", f"GPIO {config.MOTION_PIN} opened (cannot self-trigger)")
    except Exception as e:  # noqa: BLE001
        ok = _line(False, "PIR", f"GPIO {config.MOTION_PIN} — {e}")

    if config.EYES_ENABLED:
        try:
            led = PWMLED(config.EYES_PIN)
            led.value = 0
            led.close()
            _line(True, "Eyes", f"GPIO {config.EYES_PIN} opened (left dark)")
        except Exception as e:  # noqa: BLE001
            ok = _line(False, "Eyes", f"GPIO {config.EYES_PIN} — {e}")
    else:
        _line(True, "Eyes", "disabled (JARVIS_EYES_ENABLED)")

    _line(True, "Servo", f"GPIO {config.SERVO_PIN} NOT tested — would move the jaw")
    return ok


def _check_env() -> bool:
    """Same duplicate scan doctor does — repeated here because this is the one
    that runs unattended at every boot, and a conflicting duplicate is exactly
    the fault nobody is watching for."""
    dupes = config.duplicate_env_vars()
    if not dupes:
        return _line(True, "Env file", f"{config.ENV_FILE} — no duplicates")
    clashing = {k: v for k, v in dupes.items() if len(set(v)) > 1}
    if clashing:
        detail = "; ".join(
            f"{k} = {' vs '.join(sorted(set(v)))}" for k, v in sorted(clashing.items())
        )
        return _line(False, "Env file", f"CONFLICTING duplicates — {detail}")
    return _line(True, "Env file",
                 "duplicated but agreeing: " + ", ".join(sorted(dupes)))


def run() -> int:
    """Exercise every device. 0 if nothing is missing or dead, 1 otherwise."""
    print(f"\n🔧 {config.NAME} self test  (persona: {config.PERSONA})\n")
    results = [_check_env(), _set_volume(), _check_speaker(),
               _check_mic(), _check_gpio()]
    failed = results.count(False)
    if failed:
        print(f"\n   ❌ {failed} check(s) failed — see above.")
        print("      The prop will still start; fix before the night.\n")
        return 1
    print("\n   ✅ Nothing missing or dead.")
    print("      NOT proof the prop works — a speaker in the wrong input mode")
    print("      and a loose servo supply both pass this. Run the pre-party")
    print("      checklist in HALLOWEEN.md for the things only a human can check.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
