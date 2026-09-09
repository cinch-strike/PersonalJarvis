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


def run() -> int:
    """Exercise every device. 0 if nothing is missing or dead, 1 otherwise."""
    print(f"\n🔧 {config.NAME} self test  (persona: {config.PERSONA})\n")
    results = [_check_speaker(), _check_mic(), _check_gpio()]
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
