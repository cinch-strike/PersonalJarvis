"""
Recording-trigger backends for Jarvis.
──────────────────────────────────────
Abstracts *what makes Jarvis start/stop recording* so it can vary by platform
without touching the audio loop. The trigger never owns the mic stream — it
just calls back into the main loop to start recording, stop & process, or quit.

  push_to_talk  Hold SPACE to record, release to process, ESC to quit.
                (Phase 1 behaviour, unchanged. Uses pynput.)
  wake_word     Stub for Phase 2 (Porcupine). Interface only — not implemented.

Select via JARVIS_INPUT_MODE (default "push_to_talk").

pynput is imported lazily inside the push-to-talk trigger so this module stays
importable on headless / non-pynput environments (e.g. for the wake_word stub
or --check runs).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class InputError(RuntimeError):
    """Raised when an input trigger can't be used or isn't implemented yet."""


class InputTrigger(ABC):
    """A pluggable recording trigger.

    Args:
        on_record_start: called when recording should begin.
        on_record_stop:  called when recording should end (and be processed).
        on_quit:         called once when the user asks to exit.
    """

    name: str = "base"

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

    def run(self) -> None:
        from pynput import keyboard  # lazy: only needed for this backend

        recording = False

        def on_press(key) -> None:
            nonlocal recording
            if key == keyboard.Key.space and not recording:
                recording = True
                self.on_record_start()

        def on_release(key):
            nonlocal recording
            if key == keyboard.Key.space and recording:
                recording = False
                self.on_record_stop()
            elif key == keyboard.Key.esc:
                self.on_quit()
                return False  # stops the listener

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()


class WakeWordTrigger(InputTrigger):
    """Phase 2 stub. Wake-word detection (Porcupine) lands later."""

    name = "wake_word"

    def run(self) -> None:
        raise InputError(
            "The 'wake_word' input trigger is not implemented yet — it arrives "
            "in Phase 2 (Porcupine). Use JARVIS_INPUT_MODE=push_to_talk for now."
        )


_TRIGGERS = {
    PushToTalkTrigger.name: PushToTalkTrigger,
    WakeWordTrigger.name: WakeWordTrigger,
}


def select_input_trigger(
    mode: str,
    on_record_start: Callable[[], None],
    on_record_stop: Callable[[], None],
    on_quit: Callable[[], None],
) -> InputTrigger:
    """Instantiate the input trigger named by `mode`.

    Raises InputError with an actionable message for an unknown mode.
    """
    key = (mode or "").strip().lower()
    cls = _TRIGGERS.get(key)
    if cls is None:
        valid = ", ".join(sorted(_TRIGGERS))
        raise InputError(f"Unknown JARVIS_INPUT_MODE '{mode}'. Valid values: {valid}.")
    return cls(on_record_start, on_record_stop, on_quit)
