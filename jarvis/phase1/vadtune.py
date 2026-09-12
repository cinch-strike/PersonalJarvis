"""
Measure the room so the silence threshold can be set, not guessed.
──────────────────────────────────────────────────────────────────
`JARVIS_VAD_SILENCE` is the loudness below which a moment counts as silence.
Vlad uses it to decide you have stopped talking, since there is no button.

⚠️ BOTH mistakes look identical from outside, which is why guessing fails:

  · Threshold BELOW the room's noise floor → every frame reads as speech, the
    silence counter never advances, and it records until the hard cap.
  · Threshold ABOVE your speaking voice → `speech_started` in
    input_trigger._capture_utterance never becomes True, so the silence counter
    is never even consulted, and it records until the hard cap.

Same symptom, opposite fixes: a 15-second gap between "🎙 Listening" and
"⏳ Processing" tells you nothing about which way to move. Hence this tool.

It takes two readings — the room with you quiet, then you talking normally —
and puts the threshold between them. Numbers are computed exactly as
input_trigger does (RMS over `FRAME_LENGTH` samples of channel 0) so they are
directly comparable to JARVIS_VAD_SILENCE.

⚠️ Run it WHERE THE PROP WILL STAND, with the door however it will be on the
night. A tiled bathroom and a workbench are different rooms acoustically, and
the threshold belongs to the room, not to the prop.

  python jarvis.py --test-vad
"""

from __future__ import annotations

import time

import config

# Matches the motion trigger's capture frame — 1280 samples at 16kHz = 80ms.
FRAME_LENGTH = 1280
PHASE_S = 5.0


def _rms_profile(sd, np, rate, frames):
    """RMS per frame, computed the same way the live VAD computes it.

    ⚠️ Opens the stream HERE rather than taking a long-lived one. An earlier
    version started the stream once and prompted between phases — and the stream
    went on buffering through the prompt, so the read returned the stale silence
    from while the user was reading the screen instead of what they then said.
    Speech measured quieter than the room, which is impossible and sent us
    looking at the microphone for an evening.
    """
    out = []
    stream = sd.InputStream(
        samplerate=rate, channels=config.AUDIO_CHANNELS,
        device=config.AUDIO_DEVICE, dtype="int16", blocksize=FRAME_LENGTH,
    )
    stream.start()
    try:
        for _ in range(frames):
            block, _ = stream.read(FRAME_LENGTH)
            samples = block[:, 0] if block.ndim > 1 else block
            out.append(float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))))
    finally:
        stream.stop()
        stream.close()
    return out


def _pct(values, p, np):
    return float(np.percentile(values, p)) if values else 0.0


def run() -> int:
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Audio libraries unavailable: {e}\n")
        return 1

    rate = config.SAMPLE_RATE
    frames = int(PHASE_S * rate / FRAME_LENGTH)

    print(f"\n🎚  VAD tuning  (device {config.AUDIO_DEVICE!r}, {rate}Hz)")
    print(f"   Current JARVIS_VAD_SILENCE = {config.VAD_SILENCE}")
    print("   ⚠️  Run this where the prop will actually stand.\n")

    try:
        input(f"   1/2 — STAY QUIET. Press Enter, then say nothing for {PHASE_S:g}s... ")
        print("       ● recording...", flush=True)
        room = _rms_profile(sd, np, rate, frames)
        print("       done\n")

        input(f"   2/2 — TALK. Press Enter, then talk for the whole {PHASE_S:g}s... ")
        print("       ● recording — TALK NOW", flush=True)
        speech = _rms_profile(sd, np, rate, frames)
        print("       done\n")
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Could not read the microphone: {e}")
        print("   Is the service holding it? sudo systemctl stop jarvis\n")
        return 1

    room_p50, room_p95, room_max = (_pct(room, p, np) for p in (50, 95, 100))
    sp_p50, sp_p90, sp_max = (_pct(speech, p, np) for p in (50, 90, 100))

    print("   ─────────────────────────────────────────────")
    print(f"   Room     median {room_p50:7.0f}   95th {room_p95:7.0f}   peak {room_max:7.0f}")
    print(f"   Speaking median {sp_p50:7.0f}   90th {sp_p90:7.0f}   peak {sp_max:7.0f}")
    print("   ─────────────────────────────────────────────\n")

    # ⚠️ Compare against the LOUD end of speech, not the median. Speech has gaps
    # between words, so the median frame lands in a pause and reads barely above
    # the room — the first version of this reported a real 7x margin as 1.1x and
    # suggested a threshold one unit above the noise floor, which would never
    # have detected silence at all.
    voiced = sp_p90
    if voiced <= room_p95:
        print("   ❌ Your voice is not louder than the room.")
        print("      No threshold can separate them. Move the mic closer to where")
        print("      guests stand, quieten the room, or turn the ambience down.\n")
        return 1

    # Geometric mean sits proportionally between the two, which suits a
    # measure that spans orders of magnitude better than a plain average.
    suggested = int((room_p95 * voiced) ** 0.5)
    margin = voiced / room_p95 if room_p95 else float("inf")
    if margin < 2.5:
        print(f"   ⚠️  Only {margin:.1f}x between room and voice — that is tight.")
        print("      Expect it to be twitchy: it will sometimes cut people off and")
        print("      sometimes run to the 15s cap. Worth moving the mic closer to")
        print("      where guests stand before accepting this.\n")
    print(f"   ✅ Suggested:  JARVIS_VAD_SILENCE={suggested}")
    print(f"      (clear of the room at {room_p95:.0f}, well under voiced speech at {voiced:.0f})\n")
    print("      Set it in ~/.config/jarvis/jarvis.env, then confirm the gap")
    print("      between '🎙 Listening' and '⏳ Processing' is about a second,")
    print("      not 15. If it cuts you off mid-sentence, lower it.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
