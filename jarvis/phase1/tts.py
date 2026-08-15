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
import re
import shutil
import subprocess
from abc import ABC, abstractmethod

# Roleplay personas love stage directions ("*grins toothily*") and markdown
# emphasis. TTS reads the punctuation literally ("asterisk grins toothily
# asterisk"), which shatters the illusion — strip it before speaking.
_STAGE_DIRECTIONS = re.compile(r"\*[^*]*\*|_[^_]{1,80}_")
_STRAY_MARKUP = re.compile(r"[*_`#]")
_WHITESPACE = re.compile(r"\s+")


def clean_for_speech(text: str) -> str:
    """Strip stage directions and markdown so TTS doesn't read symbols aloud.

    Whole `*...*` / `_..._` spans are removed (they're actions, not speech), then
    any stray markup characters. Falls back to the original text if stripping
    would leave nothing to say.
    """
    if not text:
        return text
    spoken = _STAGE_DIRECTIONS.sub(" ", text)
    spoken = _STRAY_MARKUP.sub("", spoken)
    spoken = _WHITESPACE.sub(" ", spoken).strip()
    return spoken or _STRAY_MARKUP.sub("", text).strip()


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

    def __init__(
        self,
        model: str | None = None,
        rate: int = 22050,
        output_device: str | None = None,
        length_scale: float | None = None,
        noise_scale: float | None = None,
        sentence_silence: float | None = None,
    ) -> None:
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
        self.output_device = output_device
        # Delivery controls — slower + more variation reads as menacing, which
        # is what the Halloween prop wants. See JARVIS_PIPER_* env vars.
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.sentence_silence = sentence_silence

    def _piper_cmd(self) -> list:
        cmd = [self._bin, "--model", self.model, "--output-raw"]
        if self.length_scale is not None:
            cmd += ["--length_scale", str(self.length_scale)]
        if self.noise_scale is not None:
            cmd += ["--noise_scale", str(self.noise_scale)]
        if self.sentence_silence is not None:
            cmd += ["--sentence_silence", str(self.sentence_silence)]
        return cmd

    def speak(self, text: str) -> None:
        aplay_cmd = [self._aplay, "-q", "-r", str(self.rate), "-f", "S16_LE", "-t", "raw"]
        if self.output_device:
            aplay_cmd += ["-D", self.output_device]
        aplay_cmd.append("-")

        pitch = os.environ.get("JARVIS_PIPER_PITCH")
        use_pitch = bool(pitch) and shutil.which("sox") is not None

        if not use_pitch:
            # No pitch shift: stream piper straight to aplay (lowest latency).
            piper = subprocess.Popen(
                self._piper_cmd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            aplay = subprocess.Popen(aplay_cmd, stdin=piper.stdout)
            if piper.stdout:
                piper.stdout.close()
            if piper.stdin:
                piper.stdin.write(text.encode("utf-8"))
                piper.stdin.close()
            piper.wait()
            aplay.wait()
            return

        # Pitch shift: render fully, THEN process, THEN play. sox's pitch effect
        # needs to buffer before it stabilises, so streaming through it live let
        # the first chunk out unprocessed — the voice audibly changed mid-
        # sentence. Replies are a sentence or two, so buffering costs little.
        audio = subprocess.run(
            self._piper_cmd(), input=text.encode("utf-8"), capture_output=True
        ).stdout
        shifted = subprocess.run(
            ["sox", "-q", "-t", "raw", "-r", str(self.rate), "-e", "signed",
             "-b", "16", "-c", "1", "-", "-t", "raw", "-",
             "pitch", str(float(pitch) * 100)],
            input=audio, capture_output=True,
        ).stdout or audio          # if sox fails, play the unshifted audio
        subprocess.run(aplay_cmd, input=shifted)


class ElevenLabsTTS(TTSBackend):
    """ElevenLabs cloud TTS — the most human-sounding option.

    Requests MP3 (supported on every plan) and decodes with ffmpeg, which is
    already installed for Whisper. Network failures raise TTSError so a
    FallbackTTS wrapper can drop to piper rather than leaving the prop silent.
    """

    name = "elevenlabs"
    API = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(
        self,
        api_key: str = "",
        voice_id: str = "",
        model_id: str = "eleven_flash_v2_5",
        stability: float | None = None,
        similarity: float | None = None,
        tempo: float | None = None,
        output_device: str | None = None,
        timeout: int = 15,
    ) -> None:
        if not api_key:
            raise TTSError(
                "elevenlabs needs an API key — set JARVIS_ELEVENLABS_KEY "
                "(get one at elevenlabs.io)."
            )
        if not voice_id:
            raise TTSError(
                "elevenlabs needs a voice — set JARVIS_ELEVENLABS_VOICE to a "
                "voice ID from your ElevenLabs voice library."
            )
        self._ffmpeg = self._require(
            "ffmpeg", "Install it: sudo apt install ffmpeg"
        )
        self._aplay = self._require(
            "aplay", "Install ALSA utils: sudo apt install alsa-utils"
        )
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity = similarity
        # <1 slows delivery. Uses sox `tempo`, which time-stretches WITHOUT
        # changing pitch — so it stays natural, unlike a pitch shift.
        self.tempo = tempo
        self.output_device = output_device
        self.timeout = timeout

    def _fetch_mp3(self, text: str) -> bytes:
        import json
        import urllib.error
        import urllib.request

        payload: dict = {"text": text, "model_id": self.model_id}
        settings = {}
        if self.stability is not None:
            settings["stability"] = self.stability
        if self.similarity is not None:
            settings["similarity_boost"] = self.similarity
        if settings:
            payload["voice_settings"] = settings

        req = urllib.request.Request(
            f"{self.API}/{self.voice_id}?output_format=mp3_22050_32",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            raise TTSError(f"ElevenLabs HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise TTSError(f"ElevenLabs request failed: {e}") from e

    def speak(self, text: str) -> None:
        mp3 = self._fetch_mp3(text)
        aplay_cmd = [self._aplay, "-q"]
        if self.output_device:
            aplay_cmd += ["-D", self.output_device]
        aplay_cmd.append("-")

        # Decode MP3 → WAV. Buffered rather than streamed so the optional tempo
        # stage gets a complete file (streaming through sox effects lets the
        # first chunk out unprocessed — the bug that made piper change voice
        # mid-sentence).
        wav = subprocess.run(
            [self._ffmpeg, "-loglevel", "quiet", "-i", "pipe:0", "-f", "wav", "pipe:1"],
            input=mp3, capture_output=True,
        ).stdout
        if not wav:
            raise TTSError("ffmpeg produced no audio from the ElevenLabs response")

        if self.tempo and shutil.which("sox"):
            stretched = subprocess.run(
                ["sox", "-q", "-t", "wav", "-", "-t", "wav", "-", "tempo", str(self.tempo)],
                input=wav, capture_output=True,
            ).stdout
            wav = stretched or wav      # if sox fails, play it un-stretched

        subprocess.run(aplay_cmd, input=wav)


class FallbackTTS(TTSBackend):
    """Try each backend in turn, per call.

    Lets the prop use a cloud voice while guaranteeing it still speaks if the
    network drops mid-party — a silent skull is worse than a robotic one.
    """

    def __init__(self, backends: list) -> None:
        if not backends:
            raise TTSError("FallbackTTS needs at least one backend.")
        self.backends = backends
        self.name = "→".join(b.name for b in backends)

    def speak(self, text: str) -> None:
        errors = []
        for backend in self.backends:
            try:
                backend.speak(text)
                return
            except Exception as e:  # noqa: BLE001 — try the next voice
                errors.append(f"{backend.name}: {e}")
                print(f"  ⚠️  TTS {backend.name} failed ({e}); trying next")
        raise TTSError("all TTS backends failed:\n   " + "\n   ".join(errors))


class EspeakTTS(TTSBackend):
    """Linux `espeak-ng` — robotic but dependency-light and reliable.

    If `output_device` is set, render to WAV and pipe through `aplay -D <dev>`
    so audio lands on a specific ALSA device (e.g. a USB speaker). Otherwise
    let espeak-ng play to the system default.
    """

    name = "espeak"

    def __init__(self, output_device: str | None = None) -> None:
        self._bin = self._require(
            "espeak-ng", "Install it: sudo apt install espeak-ng"
        )
        self.output_device = output_device
        self._aplay = None
        if output_device:
            self._aplay = self._require(
                "aplay", "Install ALSA utils: sudo apt install alsa-utils"
            )

    def speak(self, text: str) -> None:
        if not self.output_device:
            subprocess.run([self._bin, text], check=False)
            return
        espeak = subprocess.Popen(
            [self._bin, "--stdout", text], stdout=subprocess.PIPE
        )
        aplay = subprocess.Popen(
            [self._aplay, "-q", "-D", self.output_device], stdin=espeak.stdout
        )
        if espeak.stdout:
            espeak.stdout.close()  # let espeak get SIGPIPE if aplay exits
        aplay.wait()
        espeak.wait()


def _piper_delivery() -> dict:
    """Voice-delivery knobs read from the environment (see JARVIS_PIPER_*)."""

    def _f(name):
        raw = os.environ.get(name)
        return float(raw) if raw else None

    return {
        "length_scale": _f("JARVIS_PIPER_LENGTH_SCALE"),
        "noise_scale": _f("JARVIS_PIPER_NOISE_SCALE"),
        "sentence_silence": _f("JARVIS_PIPER_SENTENCE_SILENCE"),
    }


# Map explicit override values → the backend they select.
_OVERRIDE_ALIASES = {
    "say": "say",
    "macos": "say",
    "darwin": "say",
    "piper": "piper",
    "espeak": "espeak",
    "espeak-ng": "espeak",
    "elevenlabs": "elevenlabs",
    "11labs": "elevenlabs",
}


def _elevenlabs_from_env(output_device):
    """Build the ElevenLabs backend from env, or None if not configured."""

    def _f(name):
        raw = os.environ.get(name)
        return float(raw) if raw else None

    key = os.environ.get("JARVIS_ELEVENLABS_KEY", "")
    voice = os.environ.get("JARVIS_ELEVENLABS_VOICE", "")
    if not (key and voice):
        return None
    return ElevenLabsTTS(
        api_key=key,
        voice_id=voice,
        model_id=os.environ.get("JARVIS_ELEVENLABS_MODEL", "eleven_flash_v2_5"),
        stability=_f("JARVIS_ELEVENLABS_STABILITY"),
        similarity=_f("JARVIS_ELEVENLABS_SIMILARITY"),
        tempo=_f("JARVIS_ELEVENLABS_TEMPO"),
        output_device=output_device,
    )


def select_tts_backend(
    voice: str = "Daniel",
    *,
    system: str | None = None,
    override: str | None = None,
    output_device: str | None = None,
) -> TTSBackend:
    """Pick and instantiate the TTS backend for this environment.

    Order of precedence:
      1. `override` arg / JARVIS_TTS_BACKEND env var (explicit).
      2. OS auto-detect: Darwin → say; Linux → piper, falling back to espeak.

    `output_device` (an ALSA device like "plughw:3,0") routes Linux playback to
    a specific speaker; ignored by the macOS `say` backend.

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
        if choice == "elevenlabs":
            eleven = _elevenlabs_from_env(output_device)
            if eleven is None:
                raise TTSError(
                    "JARVIS_TTS_BACKEND=elevenlabs but JARVIS_ELEVENLABS_KEY "
                    "and/or JARVIS_ELEVENLABS_VOICE are not set."
                )
            # Even when explicitly chosen, keep a local voice behind it — a
            # network blip mustn't silence the prop.
            try:
                return FallbackTTS([eleven, PiperTTS(output_device=output_device,
                                                     **_piper_delivery())])
            except TTSError:
                return eleven
        if choice == "piper":
            return PiperTTS(output_device=output_device, **_piper_delivery())
        return EspeakTTS(output_device=output_device)

    if system == "Darwin":
        return MacSayTTS(voice)

    if system == "Linux":
        # ElevenLabs if configured (best quality), always with a local voice
        # behind it. Otherwise piper, then espeak-ng.
        eleven = _elevenlabs_from_env(output_device)
        try:
            local = PiperTTS(output_device=output_device, **_piper_delivery())
            return FallbackTTS([eleven, local]) if eleven else local
        except TTSError as piper_err:
            if eleven is not None:
                return eleven
            try:
                return EspeakTTS(output_device=output_device)
            except TTSError as espeak_err:
                raise TTSError(
                    "No usable Linux TTS backend found.\n"
                    f"   piper: {piper_err}\n"
                    f"   espeak-ng: {espeak_err}"
                ) from espeak_err

    raise TTSError(
        f"Unsupported platform '{system}'. Set JARVIS_TTS_BACKEND explicitly."
    )
