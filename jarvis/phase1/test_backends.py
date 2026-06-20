"""
Tests for platform backend selection — no hardware, no mic, no model load.

Run: .venv/bin/python -m unittest test_backends -v
"""

import unittest
from unittest import mock

import tts
import input_trigger


def _which_all(_binary):
    """Pretend every binary exists (returns a fake path)."""
    return "/usr/bin/" + _binary


def _which_none(_binary):
    """Pretend no binary exists."""
    return None


class TestTTSSelection(unittest.TestCase):
    def test_darwin_selects_say(self):
        backend = tts.select_tts_backend("Daniel", system="Darwin")
        self.assertIsInstance(backend, tts.MacSayTTS)
        self.assertEqual(backend.name, "say")
        self.assertEqual(backend.voice, "Daniel")

    def test_linux_prefers_piper_when_ready(self):
        with mock.patch("shutil.which", side_effect=_which_all), mock.patch.dict(
            "os.environ", {"JARVIS_PIPER_MODEL": "/voices/en.onnx"}
        ):
            backend = tts.select_tts_backend(system="Linux")
        self.assertIsInstance(backend, tts.PiperTTS)

    def test_linux_falls_back_to_espeak_without_piper(self):
        # piper binary missing, espeak-ng present.
        def which(binary):
            return None if binary == "piper" else "/usr/bin/" + binary

        with mock.patch("shutil.which", side_effect=which):
            backend = tts.select_tts_backend(system="Linux")
        self.assertIsInstance(backend, tts.EspeakTTS)

    def test_linux_falls_back_to_espeak_without_piper_model(self):
        # piper binary present but no model configured → espeak fallback.
        with mock.patch("shutil.which", side_effect=_which_all), mock.patch.dict(
            "os.environ", {}, clear=True
        ):
            backend = tts.select_tts_backend(system="Linux")
        self.assertIsInstance(backend, tts.EspeakTTS)

    def test_linux_no_backend_raises_clear_error(self):
        with mock.patch("shutil.which", side_effect=_which_none):
            with self.assertRaises(tts.TTSError):
                tts.select_tts_backend(system="Linux")

    def test_override_beats_os_detection(self):
        with mock.patch("shutil.which", side_effect=_which_all):
            backend = tts.select_tts_backend(system="Darwin", override="espeak")
        self.assertIsInstance(backend, tts.EspeakTTS)

    def test_unknown_override_raises(self):
        with self.assertRaises(tts.TTSError):
            tts.select_tts_backend(override="festival")

    def test_unsupported_platform_raises(self):
        with self.assertRaises(tts.TTSError):
            tts.select_tts_backend(system="Plan9")

    def test_missing_binary_message_is_actionable(self):
        with mock.patch("shutil.which", side_effect=_which_none):
            with self.assertRaises(tts.TTSError) as ctx:
                tts.MacSayTTS("Daniel")
        self.assertIn("say", str(ctx.exception))


class TestInputSelection(unittest.TestCase):
    def _noop(self):
        pass

    def test_push_to_talk_default(self):
        trigger = input_trigger.select_input_trigger(
            "push_to_talk", self._noop, self._noop, self._noop
        )
        self.assertIsInstance(trigger, input_trigger.PushToTalkTrigger)
        self.assertEqual(trigger.name, "push_to_talk")

    def test_wake_word_selectable_but_not_implemented(self):
        trigger = input_trigger.select_input_trigger(
            "wake_word", self._noop, self._noop, self._noop
        )
        self.assertIsInstance(trigger, input_trigger.WakeWordTrigger)
        with self.assertRaises(input_trigger.InputError):
            trigger.run()  # stub: not implemented until Phase 2

    def test_unknown_mode_raises(self):
        with self.assertRaises(input_trigger.InputError):
            input_trigger.select_input_trigger(
                "telepathy", self._noop, self._noop, self._noop
            )


if __name__ == "__main__":
    unittest.main()
