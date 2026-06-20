"""
Text-to-speech backends for Jarvis.
─────────────────────────────────
Platform-portable TTS. The backend is chosen automatically from the OS at
startup, with an explicit override via the JARVIS_TTS_BACKEND env var.

  macOS (Darwin) → `say -v <VOICE>`            (Phase 1 behaviour, unchanged)
  Linux / Pi     → `piper` (preferred)         (natural neural voice)
                   → falls back to `espeak-ng`  (if piper isn't installed)

Backends only validate that their binary exists; they never open audio at
import time, so this module is safe to import in tests and --check runs.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod


class TTSError(RuntimeError):
    """Raised when a TTS backend can't be used (e.g. its binary is missing)."""


class TTSBackend(ABC):
    """A speakable backend. Subclasses must validate their binary in __init__."""

    name: str = "base"

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak the given text. Blocks until finished."""

    @staticmethod
    def _require(binary: str, hint: str) -> str:
        """Return the resolved path to `binary`, or raise an actionable error."""
        path = shutil.which(binary)
        if not path:
            raise TTSError(
                f"TTS backend needs '{binary}' but it was not found on PATH.\n"
                f"   → {hint}"
            )
        return path


class MacSayTTS(TTSBackend):
    """macOS `say` backend — identical to Phase 1 behaviour."""

    name = "say"

    def __init__(self, voice: str = "Daniel") -> None:
        self.voice = voice
        self._bin = self._require(
            "say", "This backend is macOS-only; run Jarvis on a Mac."
        )

    def speak(self, text: str) -> None:
        subprocess.run([self._bin, "-v", self.voice, text], check=False)


class PiperTTS(TTSBackend):
    """Linux `piper` neural TTS, piped to `aplay`. Needs a voice model (.onnx).

    Model path comes from JARVIS_PIPER_MODEL. Playback sample rate from
    JARVIS_PIPER_RATE (defaults to 22050, the rate of most piper voices).
    """

    name = "piper"

    def __init__(self, model: str | None = None, rate: int = 22050) -> None:
        self._bin = self._require(
            "piper",
            "Install piper: see https://github.com/rhasspy/piper "
            "(or set JARVIS_TTS_BACKEND=espeak to use the fallback).",
        )
        self._aplay = self._require(
            "aplay", "Install ALSA utils: sudo apt install alsa-utils"
        )
        self.model = model or os.environ.get("JARVIS_PIPER_MODEL", "")
        if not self.model:
            raise TTSError(
                "piper needs a voice model. Set JARVIS_PIPER_MODEL to a .onnx "
                "voice file (download from the piper voices repo)."
            )
        self.rate = rate

    def speak(self, text: str) -> None:
        piper = subprocess.Popen(
            [self._bin, "--model", self.model, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        subprocess.Popen(
            [self._aplay, "-r", str(self.rate), "-f", "S16_LE", "-t", "raw", "-"],
            stdin=piper.stdout,
        )
        if piper.stdin:
            piper.stdin.write(text.encode("utf-8"))
            piper.stdin.close()
        piper.wait()


class EspeakTTS(TTSBackend):
    """Linux `espeak-ng` fallback — robotic but dependency-light and reliable."""

    name = "espeak"

    def __init__(self) -> None:
        self._bin = self._require(
            "espeak-ng", "Install it: sudo apt install espeak-ng"
        )

    def speak(self, text: str) -> None:
        subprocess.run([self._bin, text], check=False)


# Map explicit override values → the backend they select.
_OVERRIDE_ALIASES = {
    "say": "say",
    "macos": "say",
    "darwin": "say",
    "piper": "piper",
    "espeak": "espeak",
    "espeak-ng": "espeak",
}


def select_tts_backend(
    voice: str = "Daniel",
    *,
    system: str | None = None,
    override: str | None = None,
) -> TTSBackend:
    """Pick and instantiate the TTS backend for this environment.

    Order of precedence:
      1. `override` arg / JARVIS_TTS_BACKEND env var (explicit).
      2. OS auto-detect: Darwin → say; Linux → piper, falling back to espeak.

    Raises TTSError with an actionable message if no backend can be used.
    """
    system = system or platform.system()
    override = override if override is not None else os.environ.get("JARVIS_TTS_BACKEND")

    if override:
        key = override.strip().lower()
        choice = _OVERRIDE_ALIASES.get(key)
        if choice is None:
            valid = ", ".join(sorted(set(_OVERRIDE_ALIASES)))
            raise TTSError(
                f"Unknown JARVIS_TTS_BACKEND '{override}'. Valid values: {valid}."
            )
        if choice == "say":
            return MacSayTTS(voice)
        if choice == "piper":
            return PiperTTS()
        return EspeakTTS()

    if system == "Darwin":
        return MacSayTTS(voice)

    if system == "Linux":
        # Prefer piper; fall back to espeak-ng if piper (or its model) is absent.
        try:
            return PiperTTS()
        except TTSError as piper_err:
            try:
                return EspeakTTS()
            except TTSError as espeak_err:
                raise TTSError(
                    "No usable Linux TTS backend found.\n"
                    f"   piper: {piper_err}\n"
                    f"   espeak-ng: {espeak_err}"
                ) from espeak_err

    raise TTSError(
        f"Unsupported platform '{system}'. Set JARVIS_TTS_BACKEND explicitly."
    )
