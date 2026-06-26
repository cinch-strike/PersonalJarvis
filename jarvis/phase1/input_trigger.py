"""
Recording-trigger backends for Jarvis.
──────────────────────────────────────
Abstracts *what makes Jarvis start/stop recording* so it can vary by platform.

  push_to_talk  Hold SPACE to record, release to process, ESC to quit.
                (Phase 1 behaviour. Uses pynput. Needs a physical keyboard, so
                 it's the Mac default — not usable on a headless Pi.)
  wake_word     Say "Jarvis" to wake, speak your question, and it processes when
                you stop talking. (Phase 2, Porcupine + silence detection.)

Select via JARVIS_INPUT_MODE (default "push_to_talk").

Two kinds of trigger:
  • `manages_audio = False` (push_to_talk): the main loop owns the mic stream and
    streams frames via its own callback; the trigger only flips record state.
  • `manages_audio = True` (wake_word): the trigger owns the mic stream end to
    end (it must read audio to detect the wake word), captures the utterance,
    and hands the frames to `process_utterance(frames)`.

Heavy/optional deps (pynput, pvporcupine, sounddevice, numpy) are imported
lazily inside `run()` so this module stays importable anywhere — tests,
`--check`, and headless boxes that don't have every backend installed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional


class InputError(RuntimeError):
    """Raised when an input trigger can't be used (missing dep, key, or mode)."""


class InputTrigger(ABC):
    """A pluggable recording trigger.

    Args:
        on_record_start: called when recording begins (UI/state hook).
        on_record_stop:  called when recording ends and should be processed.
        on_quit:         called once when the user asks to exit.
    """

    name: str = "base"
    manages_audio: bool = False  # True → the trigger owns the mic stream itself

    def __init__(
        self,
        on_record_start: Callable[[], None],
        on_record_stop: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.on_record_start = on_record_start
        self.on_record_stop = on_record_stop
        self.on_quit = on_quit

    @abstractmethod
    def run(self) -> None:
        """Block, driving the trigger, until the user quits."""


class PushToTalkTrigger(InputTrigger):
    """Hold SPACE to record, release to process, ESC to quit (Phase 1)."""

    name = "push_to_talk"
    manages_audio = False  # main loop owns the InputStream + audio_callback

    def run(self) -> None:
        from pynput import keyboard  # lazy: only needed for this backend

        recording = False

        def on_press(key) -> None:
            nonlocal recording
            if key == keyboard.Key.space and not recording:
                recording = True
                self.on_record_start()
                print("  🎙  Recording... (release SPACE to stop)", end="", flush=True)

        def on_release(key):
            nonlocal recording
            if key == keyboard.Key.space and recording:
                recording = False
                print(" ⏳ Processing...")
                self.on_record_stop()
            elif key == keyboard.Key.esc:
                self.on_quit()
                return False  # stops the listener

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()


# ─── Wake-word engines ────────────────────────────────────────────────────────
# Each engine just answers "did the wake word fire in this audio frame?" and
# declares the sample rate + frame size it wants. The trigger below owns the mic
# stream, feeds the engine, and handles utterance capture/VAD — shared by both.

class WakeEngine(ABC):
    sample_rate: int = 16000
    frame_length: int = 512

    @abstractmethod
    def process(self, pcm) -> bool:
        """Return True if the wake word fired in this int16 mono frame."""

    def reset(self) -> None:
        """Clear internal detection state (e.g. after handling an utterance)."""

    def close(self) -> None:
        pass


class PorcupineEngine(WakeEngine):
    """Picovoice Porcupine. Light + accurate, but the free key now requires a
    commercial-use approval from Picovoice (console.picovoice.ai)."""

    def __init__(self, access_key: str, keyword: str = "jarvis") -> None:
        if not access_key:
            raise InputError(
                "porcupine engine needs a Picovoice access key in "
                "JARVIS_PORCUPINE_KEY (https://console.picovoice.ai)."
            )
        try:
            import pvporcupine
        except ImportError as e:
            raise InputError(
                "porcupine engine needs 'pvporcupine': "
                ".venv/bin/python -m pip install pvporcupine"
            ) from e
        try:
            self._p = pvporcupine.create(access_key=access_key, keywords=[keyword])
        except Exception as e:  # bad key, unknown keyword, etc.
            raise InputError(f"could not start Porcupine ({keyword!r}): {e}") from e
        self.sample_rate = self._p.sample_rate
        self.frame_length = self._p.frame_length

    def process(self, pcm) -> bool:
        return self._p.process(pcm) >= 0

    def close(self) -> None:
        try:
            self._p.delete()
        except Exception:
            pass


class OpenWakeWordEngine(WakeEngine):
    """openWakeWord — open-source, no account/key, runs offline. Ships a
    pretrained "hey_jarvis" model. Expects 16 kHz / 1280-sample (80 ms) frames."""

    sample_rate = 16000
    frame_length = 1280

    def __init__(self, model: str = "hey_jarvis", threshold: float = 0.5) -> None:
        try:
            import openwakeword
            from openwakeword.model import Model
        except ImportError as e:
            raise InputError(
                "openwakeword engine needs 'openwakeword': "
                ".venv/bin/python -m pip install openwakeword"
            ) from e
        self.threshold = threshold
        self.model_key = model
        # The API differs across versions, and Python 3.13 on the Pi only gets
        # the older 0.4.x (newer releases need tflite-runtime, which has no 3.13
        # wheel). Handle both:
        #   ≥0.5: utils.download_models() then Model(wakeword_models=[name])
        #   0.4.x: models are bundled — Model() loads them all (incl. hey_jarvis)
        utils = getattr(openwakeword, "utils", None)
        try:
            if utils is not None and hasattr(utils, "download_models"):
                try:
                    utils.download_models([model])
                except TypeError:
                    utils.download_models()
                self._model = Model(wakeword_models=[model])
            else:
                self._model = Model()
        except Exception as e:
            raise InputError(
                f"could not load openWakeWord model {model!r}: {e}"
            ) from e

    def process(self, pcm) -> bool:
        scores = self._model.predict(pcm)
        # Match by substring so it works whether the key is "hey_jarvis" or a
        # versioned "hey_jarvis_v0.1". With 0.4.x Model() all models are scored;
        # we only react to the one we want.
        return any(
            self.model_key in name and score >= self.threshold
            for name, score in scores.items()
        )

    def reset(self) -> None:
        # Clear the rolling prediction buffer so leftover frames (e.g. from our
        # own TTS) don't carry over into the next wake decision.
        try:
            self._model.reset()
        except Exception:
            pass


class WakeWordTrigger(InputTrigger):
    """Say the wake word to start; record until you stop talking; repeat.

    Owns the mic stream because it must read audio continuously to detect the
    wake word. Detection is delegated to a pluggable WakeEngine (Porcupine or
    openWakeWord); a simple RMS-energy silence detector decides when the spoken
    question has ended. Quit with Ctrl+C.
    """

    name = "wake_word"
    manages_audio = True

    def __init__(
        self,
        on_record_start: Callable[[], None],
        on_record_stop: Callable[[], None],
        on_quit: Callable[[], None],
        *,
        process_utterance: Optional[Callable[[List], None]] = None,
        engine: str = "auto",
        access_key: str = "",
        keyword: str = "jarvis",
        oww_model: str = "hey_jarvis",
        oww_threshold: float = 0.5,
        device: Optional[object] = None,
        channels: int = 1,
        silence_threshold: float = 500.0,
        silence_ms: int = 1000,
        max_utterance_s: int = 15,
    ) -> None:
        super().__init__(on_record_start, on_record_stop, on_quit)
        self.process_utterance = process_utterance
        self.engine = engine
        self.access_key = access_key
        self.keyword = keyword
        self.oww_model = oww_model
        self.oww_threshold = oww_threshold
        self.device = device
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_ms = silence_ms
        self.max_utterance_s = max_utterance_s

    def _make_engine(self) -> WakeEngine:
        choice = (self.engine or "auto").strip().lower()
        if choice == "auto":
            # Prefer Porcupine only if a key is present; otherwise go keyless.
            choice = "porcupine" if self.access_key else "openwakeword"
        if choice == "porcupine":
            return PorcupineEngine(self.access_key, self.keyword)
        if choice in ("openwakeword", "oww"):
            return OpenWakeWordEngine(self.oww_model, self.oww_threshold)
        raise InputError(
            f"Unknown JARVIS_WAKE_ENGINE '{self.engine}'. "
            "Valid values: auto, porcupine, openwakeword."
        )

    def _label(self) -> str:
        return self.keyword if isinstance(self._engine, PorcupineEngine) else self.oww_model

    def run(self) -> None:
        if self.process_utterance is None:
            raise InputError("wake_word trigger was given no process_utterance callback.")

        self._engine = self._make_engine()  # raises InputError with guidance
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as e:
            self._engine.close()
            raise InputError(f"wake_word needs sounddevice + numpy: {e}") from e

        engine = self._engine
        rate = engine.sample_rate
        frame_length = engine.frame_length
        silence_frames = max(1, int(self.silence_ms / 1000 * rate / frame_length))
        max_frames = int(self.max_utterance_s * rate / frame_length)
        label = self._label()

        def mono(block):
            return block[:, 0] if block.ndim > 1 else block

        print(f"\n  👂 Listening for \"{label}\"...  (Ctrl+C to quit)\n")
        try:
            with sd.InputStream(
                samplerate=rate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            ) as stream:
                while True:
                    block, _ = stream.read(frame_length)
                    if not engine.process(mono(block)):
                        continue

                    # Wake word heard → capture the question until silence.
                    self.on_record_start()
                    print("  🎙  Yes? Listening...", flush=True)
                    captured: List = []
                    silence_run = 0
                    speech_started = False
                    for _ in range(max_frames):
                        block, _ = stream.read(frame_length)
                        samples = mono(block)
                        captured.append(samples.copy())
                        rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                        if rms >= self.silence_threshold:
                            speech_started = True
                            silence_run = 0
                        elif speech_started:
                            silence_run += 1
                            if silence_run >= silence_frames:
                                break

                    print("  ⏳ Processing...")
                    # Pause the mic while we transcribe, think, and speak, so the
                    # stream never buffers Jarvis's own voice from the speaker.
                    stream.stop()
                    try:
                        self.process_utterance(captured)
                    finally:
                        stream.start()
                    # Belt-and-suspenders: discard any residual buffered audio and
                    # reset the detector so it can't hear/reply to itself (feedback).
                    try:
                        pending = stream.read_available
                        if pending:
                            stream.read(pending)
                    except Exception:
                        pass
                    engine.reset()
                    print(f'\n  👂 Listening for "{label}"...\n')
        except KeyboardInterrupt:
            print("\n  (wake-word listener stopped)")
            self.on_quit()
        finally:
            engine.close()


_TRIGGERS = {
    PushToTalkTrigger.name: PushToTalkTrigger,
    WakeWordTrigger.name: WakeWordTrigger,
}


def select_input_trigger(
    mode: str,
    on_record_start: Callable[[], None],
    on_record_stop: Callable[[], None],
    on_quit: Callable[[], None],
    *,
    process_utterance: Optional[Callable[[List], None]] = None,
    wake_config: Optional[dict] = None,
) -> InputTrigger:
    """Instantiate the input trigger named by `mode`.

    `process_utterance` and `wake_config` are only used by audio-managing
    triggers (wake_word); push_to_talk ignores them.

    Raises InputError with an actionable message for an unknown mode.
    """
    key = (mode or "").strip().lower()
    cls = _TRIGGERS.get(key)
    if cls is None:
        valid = ", ".join(sorted(_TRIGGERS))
        raise InputError(f"Unknown JARVIS_INPUT_MODE '{mode}'. Valid values: {valid}.")
    if cls is WakeWordTrigger:
        return WakeWordTrigger(
            on_record_start,
            on_record_stop,
            on_quit,
            process_utterance=process_utterance,
            **(wake_config or {}),
        )
    return cls(on_record_start, on_record_stop, on_quit)
