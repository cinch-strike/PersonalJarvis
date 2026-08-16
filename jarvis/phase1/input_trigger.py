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

import time
from abc import ABC, abstractmethod
from typing import Callable, List, Optional


class InputError(RuntimeError):
    """Raised when an input trigger can't be used (missing dep, key, or mode)."""


class AudioStreamError(InputError):
    """The mic stopped delivering real-time audio — the device has dropped out.

    Seen in the field: after days of uptime the ReSpeaker's USB audio stream
    died, and sounddevice kept returning empty buffers instead of erroring. The
    process stayed alive (so systemd saw it as healthy) while every capture
    produced "nothing heard". Raising this lets the prop restart itself instead
    of silently doing nothing all night.
    """


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


class AudioCaptureTrigger(InputTrigger):
    """Base for triggers that own the mic stream and capture spoken replies.

    Shares the "record until the speaker goes quiet" (RMS/VAD) capture and the
    feedback-safe processing handoff between wake_word and motion.
    """

    manages_audio = True

    def __init__(
        self,
        on_record_start: Callable[[], None],
        on_record_stop: Callable[[], None],
        on_quit: Callable[[], None],
        *,
        process_utterance: Optional[Callable[[List], None]] = None,
        device: Optional[object] = None,
        channels: int = 1,
        silence_threshold: float = 500.0,
        silence_ms: int = 1000,
        max_utterance_s: int = 15,
        max_dead_captures: int = 3,
    ) -> None:
        super().__init__(on_record_start, on_record_stop, on_quit)
        self.process_utterance = process_utterance
        self.device = device
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_ms = silence_ms
        self.max_utterance_s = max_utterance_s
        self.max_dead_captures = max_dead_captures
        self._dead_streak = 0

    @staticmethod
    def _mono(block):
        return block[:, 0] if block.ndim > 1 else block

    def _check_stream_alive(self, frames: int, frame_length: int,
                            rate: int, elapsed: float) -> None:
        """Flag a stream that returns audio faster than real time.

        A working mic can't hand over a second of audio in a millisecond — reads
        block until the samples exist. If they come back instantly the device has
        stopped producing and we're reading empty buffers. Tolerate a couple of
        blips, then raise so the caller can restart.
        """
        if frames < 10:
            return                      # too short to judge
        expected = frames * frame_length / rate
        if elapsed >= expected * 0.3:
            self._dead_streak = 0       # healthy
            return
        self._dead_streak += 1
        print(f"  ⚠️  Mic returned {expected:.1f}s of audio in {elapsed:.3f}s "
              f"— stream looks dead ({self._dead_streak}/{self.max_dead_captures})")
        if self._dead_streak >= self.max_dead_captures:
            raise AudioStreamError(
                "microphone stopped delivering audio "
                f"({self._dead_streak} dead captures in a row) — restarting"
            )

    def _capture_utterance(self, stream, frame_length: int, rate: int) -> List:
        """Record from `stream` until the speaker pauses (or the cap is hit)."""
        import numpy as np

        silence_frames = max(1, int(self.silence_ms / 1000 * rate / frame_length))
        max_frames = int(self.max_utterance_s * rate / frame_length)
        captured: List = []
        silence_run = 0
        speech_started = False
        started = time.monotonic()
        for _ in range(max_frames):
            block, _ = stream.read(frame_length)
            samples = self._mono(block)
            captured.append(samples.copy())
            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
            if rms >= self.silence_threshold:
                speech_started = True
                silence_run = 0
            elif speech_started:
                silence_run += 1
                if silence_run >= silence_frames:
                    break
        self._check_stream_alive(
            len(captured), frame_length, rate, time.monotonic() - started
        )
        return captured

    def _process_and_drain(self, stream, captured: List) -> None:
        """Hand frames to the pipeline with the mic paused, then flush the backlog.

        Pausing keeps our own TTS out of the stream; the drain clears anything
        that still slipped in, so the prop can't hear and answer itself.
        """
        stream.stop()
        try:
            self.process_utterance(captured)
        finally:
            stream.start()
        try:
            pending = stream.read_available
            if pending:
                stream.read(pending)
        except Exception:
            pass


class WakeWordTrigger(AudioCaptureTrigger):
    """Say the wake word to start; record until you stop talking; repeat.

    Owns the mic stream because it must read audio continuously to detect the
    wake word. Detection is delegated to a pluggable WakeEngine (Porcupine or
    openWakeWord); a simple RMS-energy silence detector decides when the spoken
    question has ended. Quit with Ctrl+C.
    """

    name = "wake_word"

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
        super().__init__(
            on_record_start,
            on_record_stop,
            on_quit,
            process_utterance=process_utterance,
            device=device,
            channels=channels,
            silence_threshold=silence_threshold,
            silence_ms=silence_ms,
            max_utterance_s=max_utterance_s,
        )
        self.engine = engine
        self.access_key = access_key
        self.keyword = keyword
        self.oww_model = oww_model
        self.oww_threshold = oww_threshold

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
            import sounddevice as sd
        except ImportError as e:
            self._engine.close()
            raise InputError(f"wake_word needs sounddevice + numpy: {e}") from e

        engine = self._engine
        rate = engine.sample_rate
        frame_length = engine.frame_length
        label = self._label()

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
                    if not engine.process(self._mono(block)):
                        continue

                    # Wake word heard → capture the question until silence.
                    self.on_record_start()
                    print("  🎙  Yes? Listening...", flush=True)
                    captured = self._capture_utterance(stream, frame_length, rate)
                    print("  ⏳ Processing...")
                    self._process_and_drain(stream, captured)
                    engine.reset()
                    print(f'\n  👂 Listening for "{label}"...\n')
        except KeyboardInterrupt:
            print("\n  (wake-word listener stopped)")
            self.on_quit()
        finally:
            engine.close()


class MotionTrigger(AudioCaptureTrigger):
    """Presence-triggered barker: it notices you, calls out, then converses.

    Built for a standalone prop (e.g. a Halloween skull) where guests shouldn't
    need to know a wake word. Flow per visitor:

        presence detected → speak a barker line → listen → reply
        → keep conversing while they keep talking → cooldown → re-arm

    Sensor: any digital sensor whose pin reads HIGH on detection — an LD2410
    mmWave module's OUT pin (detects a *standing* person, not just movement) or
    a PIR like the HC-SR501. Read via gpiozero, which works on the Pi 5.
    """

    name = "motion"

    def __init__(
        self,
        on_record_start: Callable[[], None],
        on_record_stop: Callable[[], None],
        on_quit: Callable[[], None],
        *,
        process_utterance: Optional[Callable[[List], None]] = None,
        speak: Optional[Callable[[str], None]] = None,
        ambience: Optional[object] = None,
        eyes: Optional[object] = None,
        barker_lines: Optional[List[str]] = None,
        sensor_pin: int = 17,
        cooldown_s: float = 20.0,
        ambience_resume_s: float = 5.0,
        follow_up_turns: int = 4,
        device: Optional[object] = None,
        channels: int = 1,
        sample_rate: int = 16000,
        frame_length: int = 1024,
        silence_threshold: float = 500.0,
        silence_ms: int = 1000,
        max_utterance_s: int = 15,
        max_dead_captures: int = 3,
    ) -> None:
        super().__init__(
            on_record_start,
            on_record_stop,
            on_quit,
            process_utterance=process_utterance,
            device=device,
            channels=channels,
            silence_threshold=silence_threshold,
            silence_ms=silence_ms,
            max_utterance_s=max_utterance_s,
            max_dead_captures=max_dead_captures,
        )
        self.speak = speak
        self.ambience = ambience
        self.eyes = eyes
        self.barker_lines = list(barker_lines or [])
        self.sensor_pin = sensor_pin
        self.cooldown_s = cooldown_s
        # Ambience comes back part-way through the cooldown rather than at the
        # end of it, so the visitor doesn't walk away into dead silence.
        self.ambience_resume_s = ambience_resume_s
        self.follow_up_turns = follow_up_turns
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self._last_barker: Optional[str] = None

    def _next_barker(self) -> Optional[str]:
        """Pick a barker line, avoiding an immediate repeat of the last one."""
        import random

        if not self.barker_lines:
            return None
        choices = [b for b in self.barker_lines if b != self._last_barker] or self.barker_lines
        line = random.choice(choices)
        self._last_barker = line
        return line

    def _make_sensor(self):
        try:
            from gpiozero import MotionSensor
        except ImportError as e:
            raise InputError(
                "motion mode needs gpiozero (Pi): "
                ".venv/bin/python -m pip install gpiozero lgpio"
            ) from e
        try:
            # MotionSensor works with any sensor that drives the pin HIGH on
            # detection — PIR or an LD2410's OUT pin.
            return MotionSensor(self.sensor_pin)
        except Exception as e:
            raise InputError(
                f"could not open presence sensor on GPIO {self.sensor_pin}: {e}"
            ) from e

    def run(self) -> None:
        if self.process_utterance is None:
            raise InputError("motion trigger was given no process_utterance callback.")
        try:
            import sounddevice as sd
        except ImportError as e:
            raise InputError(f"motion mode needs sounddevice + numpy: {e}") from e

        import time

        sensor = self._make_sensor()
        rate, frame_length = self.sample_rate, self.frame_length

        print(f"\n  👁  Watching for visitors (GPIO {self.sensor_pin})...  (Ctrl+C to quit)\n")
        try:
            with sd.InputStream(
                samplerate=rate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            ) as stream:
                while True:
                    # Idle until someone is actually there. Mic is stopped so we
                    # don't buffer the whole party while waiting; the ambience
                    # loop plays to draw people over.
                    stream.stop()
                    if self.ambience is not None:
                        self.ambience.start()
                    sensor.wait_for_motion()
                    # Kill the music BEFORE we speak or listen — it would
                    # otherwise bleed into the mic and wreck transcription.
                    if self.ambience is not None:
                        self.ambience.stop()
                    # Eyes brighten the moment it notices you — the change is
                    # what reads as "it saw me", more than the brightness itself.
                    if self.eyes is not None:
                        self.eyes.alert()
                    print("  👻 Someone's there!")
                    stream.start()

                    # Call out to them, then converse until they stop replying.
                    line = self._next_barker()
                    if line and self.speak:
                        self.speak(line)
                    for _ in range(max(1, self.follow_up_turns)):
                        self.on_record_start()
                        print("  🎙  Listening...", flush=True)
                        captured = self._capture_utterance(stream, frame_length, rate)
                        if not captured:
                            break
                        print("  ⏳ Processing...")
                        self._process_and_drain(stream, captured)

                    print(f"  😴 Cooling down {self.cooldown_s:.0f}s...\n")
                    if self.eyes is not None:
                        self.eyes.idle()     # dim back down as they walk away
                    resume_at = max(0.0, min(self.ambience_resume_s, self.cooldown_s))
                    time.sleep(resume_at)
                    if self.ambience is not None:
                        self.ambience.start()
                    time.sleep(self.cooldown_s - resume_at)
                    print(f"  👁  Watching for visitors...\n")
        except KeyboardInterrupt:
            print("\n  (motion listener stopped)")
            self.on_quit()
        finally:
            if self.ambience is not None:
                self.ambience.stop()
            try:
                sensor.close()
            except Exception:
                pass


_TRIGGERS = {
    PushToTalkTrigger.name: PushToTalkTrigger,
    WakeWordTrigger.name: WakeWordTrigger,
    MotionTrigger.name: MotionTrigger,
}


def select_input_trigger(
    mode: str,
    on_record_start: Callable[[], None],
    on_record_stop: Callable[[], None],
    on_quit: Callable[[], None],
    *,
    process_utterance: Optional[Callable[[List], None]] = None,
    speak: Optional[Callable[[str], None]] = None,
    ambience: Optional[object] = None,
    eyes: Optional[object] = None,
    wake_config: Optional[dict] = None,
    motion_config: Optional[dict] = None,
) -> InputTrigger:
    """Instantiate the input trigger named by `mode`.

    `process_utterance` / `speak` / `*_config` are only used by audio-managing
    triggers (wake_word, motion); push_to_talk ignores them.

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
    if cls is MotionTrigger:
        return MotionTrigger(
            on_record_start,
            on_record_stop,
            on_quit,
            process_utterance=process_utterance,
            speak=speak,
            ambience=ambience,
            eyes=eyes,
            **(motion_config or {}),
        )
    return cls(on_record_start, on_record_stop, on_quit)
