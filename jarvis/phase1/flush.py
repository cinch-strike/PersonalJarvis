"""
Toilet-flush detection.
─────────────────────────
The prop lives in a bathroom, so a flush is a comedy cue: reacting the moment
someone flushes is far funnier than generic toilet humour.

No second microphone listener and no extra model. A flush is loud, so the
existing VAD already captures it as if it were speech — Whisper then returns
garbage (it hallucinates "Thank you." on non-speech audio). So we classify the
buffer we *already have*, before it reaches Whisper, and branch if it looks like
plumbing rather than a person.

Three signals, all cheap, all computed from the same buffer:

    duration    a flush runs for seconds; a word doesn't
    sustained   speech is full of gaps, a flush is continuous
    flatness    spectral flatness — noise is broadband, voices are harmonic

Flatness is the one that actually separates them. A voice puts its energy into
a few harmonic peaks (flatness near 0); rushing water spreads energy across the
whole spectrum (flatness toward 1). Loudness alone would fire on a shout.

⚠️ The defaults are starting points, not gospel. Tiled bathrooms are acoustically
brutal and every cistern sounds different — run `--test-flush` in the real room
and set the thresholds from what you measure. See HALLOWEEN.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

# 30ms at 16kHz. Long enough for a stable spectrum, short enough that the gaps
# between spoken words still register as gaps.
_WINDOW_MS = 30


@dataclass
class Metrics:
    """What the buffer measured — printed by --test-flush for tuning."""
    duration_s: float
    rms: float
    flatness: float
    sustained: float

    def describe(self) -> str:
        return (f"duration={self.duration_s:.2f}s  rms={self.rms:.0f}  "
                f"flatness={self.flatness:.3f}  sustained={self.sustained:.2f}")


def _to_samples(frames) -> np.ndarray:
    """Flatten captured frames to a 1-D float array on the int16 scale."""
    if frames is None:
        return np.zeros(0, dtype=np.float32)
    if isinstance(frames, np.ndarray):
        return frames.flatten().astype(np.float32)
    if len(frames) == 0:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(frames).flatten().astype(np.float32)


def _spectral_flatness(window: np.ndarray) -> float:
    """Geometric mean / arithmetic mean of the power spectrum.

    ~0 for a pure tone or a voiced vowel, toward 1 for broadband noise. The
    floor stops log(0) turning the geometric mean into -inf on digital silence.
    """
    spectrum = np.abs(np.fft.rfft(window)) ** 2
    spectrum = spectrum[1:]                     # drop DC — it carries no timbre
    if spectrum.size == 0:
        return 0.0
    spectrum = np.maximum(spectrum, 1e-10)
    geometric = np.exp(np.mean(np.log(spectrum)))
    arithmetic = float(np.mean(spectrum))
    return float(geometric / arithmetic) if arithmetic > 0 else 0.0


def analyse(frames, rate: int, silence_rms: float = 500.0) -> Metrics:
    """Measure a captured buffer. Never raises on odd input."""
    samples = _to_samples(frames)
    if samples.size == 0:
        return Metrics(0.0, 0.0, 0.0, 0.0)

    duration = samples.size / float(rate)
    overall_rms = float(np.sqrt(np.mean(samples ** 2)))

    window_len = max(1, int(rate * _WINDOW_MS / 1000))
    usable = (samples.size // window_len) * window_len
    if usable < window_len:
        return Metrics(duration, overall_rms, 0.0, 0.0)

    windows = samples[:usable].reshape(-1, window_len)

    # Loud fraction: how much of the buffer is *continuously* above the noise
    # floor. Speech drops into the gaps between words; a flush doesn't.
    window_rms = np.sqrt(np.mean(windows ** 2, axis=1))
    sustained = float(np.mean(window_rms >= silence_rms))

    # Average flatness over the loud windows only — silence is broadband too,
    # so including quiet windows would flatter a pause into looking like noise.
    loud = windows[window_rms >= silence_rms]
    if loud.shape[0] == 0:
        return Metrics(duration, overall_rms, 0.0, sustained)
    flatness = float(np.mean([_spectral_flatness(w) for w in loud]))

    return Metrics(duration, overall_rms, flatness, sustained)


class FlushDetector:
    """Decides whether a captured buffer is plumbing rather than a person."""

    def __init__(
        self,
        enabled: bool = False,
        min_duration_s: float = 2.5,
        min_rms: float = 600.0,
        min_flatness: float = 0.15,
        min_sustained: float = 0.8,
        silence_rms: float = 500.0,
    ) -> None:
        self.enabled = enabled
        self.min_duration_s = min_duration_s
        self.min_rms = min_rms
        self.min_flatness = min_flatness
        self.min_sustained = min_sustained
        self.silence_rms = silence_rms

    def measure(self, frames, rate: int) -> Metrics:
        return analyse(frames, rate, self.silence_rms)

    def matches(self, frames, rate: int) -> bool:
        """True if the buffer looks like a flush.

        Any failure returns False so the audio falls through to normal
        transcription — a broken detector must never eat someone's question.
        """
        if not self.enabled:
            return False
        try:
            m = self.measure(frames, rate)
        except Exception:  # noqa: BLE001 — never break the conversation path
            return False
        return (
            m.duration_s >= self.min_duration_s
            and m.rms >= self.min_rms
            and m.flatness >= self.min_flatness
            and m.sustained >= self.min_sustained
        )

    def explain(self, frames, rate: int) -> str:
        """Per-check pass/fail, for --test-flush."""
        m = self.measure(frames, rate)
        checks = [
            ("duration", m.duration_s, self.min_duration_s),
            ("rms", m.rms, self.min_rms),
            ("flatness", m.flatness, self.min_flatness),
            ("sustained", m.sustained, self.min_sustained),
        ]
        lines = [f"   {m.describe()}", ""]
        for name, got, want in checks:
            mark = "✅" if got >= want else "❌"
            lines.append(f"   {mark} {name:<10} {got:>8.3f}  (needs ≥ {want})")
        return "\n".join(lines)


def build_detector() -> FlushDetector:
    """Construct from config."""
    import config

    return FlushDetector(
        enabled=config.FLUSH_ENABLED,
        min_duration_s=config.FLUSH_MIN_S,
        min_rms=config.FLUSH_RMS,
        min_flatness=config.FLUSH_FLATNESS,
        min_sustained=config.FLUSH_SUSTAINED,
        silence_rms=config.VAD_SILENCE,
    )


def self_test(record_seconds: float = 12.0) -> int:
    """Record once and print what it measured — `jarvis.py --test-flush`.

    The tuning tool: run it while flushing, then again while talking, and set
    the thresholds somewhere between the two.
    """
    import config

    try:
        import sounddevice as sd
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Cannot open audio: {e}\n")
        return 1

    detector = build_detector()
    detector.enabled = True          # --test-flush always measures

    print(f"\n🚽 Flush test — recording {record_seconds:.0f}s from "
          f"{config.AUDIO_INPUT or 'default device'}")
    print("   Flush the toilet now (then run it again and just talk).\n")

    try:
        recording = sd.rec(
            int(record_seconds * config.SAMPLE_RATE),
            samplerate=config.SAMPLE_RATE,
            channels=config.AUDIO_CHANNELS,
            dtype="int16",
            device=config.AUDIO_INPUT or None,
        )
        sd.wait()
    except Exception as e:  # noqa: BLE001
        print(f"   ❌ Recording failed: {e}")
        print("      Is the service holding the mic? sudo systemctl stop jarvis\n")
        return 1

    print(detector.explain(recording, config.SAMPLE_RATE))
    verdict = "FLUSH" if detector.matches(recording, config.SAMPLE_RATE) else "not a flush"
    print(f"\n   → verdict: {verdict}")
    print("   Tune with JARVIS_FLUSH_MIN_S / _RMS / _FLATNESS / _SUSTAINED.\n")
    return 0
