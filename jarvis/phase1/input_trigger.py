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


class WakeWordTrigger(InputTrigger):
    """Say the wake word to start; record until you stop talking; repeat.

    Owns the mic stream because it must read audio continuously to detect the
    wake word. Uses Porcupine for detection and a simple RMS-energy silence
    detector to decide when the spoken question has ended. Quit with Ctrl+C.
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
        access_key: str = "",
        keyword: str = "jarvis",
        device: Optional[object] = None,
        channels: int = 1,
        silence_threshold: float = 500.0,
        silence_ms: int = 1000,
        max_utterance_s: int = 15,
    ) -> None:
        super().__init__(on_record_start, on_record_stop, on_quit)
        self.process_utterance = process_utterance
        self.access_key = access_key
        self.keyword = keyword
        self.device = device
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_ms = silence_ms
        self.max_utterance_s = max_utterance_s

    def run(self) -> None:
        try:
            import pvporcupine
        except ImportError as e:
            raise InputError(
                "wake_word needs the 'pvporcupine' package — install it on the Pi:\n"
                "   .venv/bin/python -m pip install pvporcupine"
            ) from e
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as e:
            raise InputError(f"wake_word needs sounddevice + numpy: {e}") from e

        if not self.access_key:
            raise InputError(
                "wake_word needs a Picovoice access key. Get a free key at "
                "https://console.picovoice.ai and set JARVIS_PORCUPINE_KEY."
            )
        if self.process_utterance is None:
            raise InputError("wake_word trigger was given no process_utterance callback.")

        try:
            porcupine = pvporcupine.create(
                access_key=self.access_key, keywords=[self.keyword]
            )
        except Exception as e:  # bad key, unknown keyword, etc.
            raise InputError(f"could not start Porcupine ({self.keyword!r}): {e}") from e

        frame_length = porcupine.frame_length      # samples Porcupine wants per call
        rate = porcupine.sample_rate               # 16000
        silence_frames = max(1, int(self.silence_ms / 1000 * rate / frame_length))
        max_frames = int(self.max_utterance_s * rate / frame_length)

        def mono(block):
            return block[:, 0] if block.ndim > 1 else block

        print(f"\n  👂 Listening for \"{self.keyword}\"...  (Ctrl+C to quit)\n")
        try:
            with sd.InputStream(
                samplerate=rate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            ) as stream:
                while True:
                    block, _ = stream.read(frame_length)
                    if porcupine.process(mono(block)) < 0:
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
                    self.process_utterance(captured)
                    print(f'\n  👂 Listening for "{self.keyword}"...\n')
        except KeyboardInterrupt:
            print("\n  (wake-word listener stopped)")
            self.on_quit()
        finally:
            porcupine.delete()


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
