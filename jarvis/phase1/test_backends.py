"""
Tests for platform backend selection — no hardware, no mic, no model load.

Run: .venv/bin/python -m unittest test_backends -v
"""

import unittest
from unittest import mock

import tts
import input_trigger
import llm
import doctor
import tools


def _which_all(_binary):
    """Pretend every binary exists (returns a fake path)."""
    return "/usr/bin/" + _binary


def _which_none(_binary):
    """Pretend no binary exists."""
    return None


class TestTTSSelection(unittest.TestCase):
    def test_darwin_selects_say(self):
        # Mock `which` so the test is OS-independent (no `say` binary on Linux CI).
        with mock.patch("shutil.which", side_effect=_which_all):
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

    def test_elevenlabs_selected_with_piper_fallback(self):
        env = {"JARVIS_ELEVENLABS_KEY": "k", "JARVIS_ELEVENLABS_VOICE": "v",
               "JARVIS_PIPER_MODEL": "/voices/x.onnx"}
        with mock.patch("shutil.which", side_effect=_which_all), \
             mock.patch.dict("os.environ", env):
            backend = tts.select_tts_backend(system="Linux")
        self.assertIsInstance(backend, tts.FallbackTTS)
        self.assertEqual([b.name for b in backend.backends], ["elevenlabs", "piper"])

    def test_no_elevenlabs_key_stays_on_piper(self):
        env = {"JARVIS_PIPER_MODEL": "/voices/x.onnx"}
        with mock.patch("shutil.which", side_effect=_which_all), \
             mock.patch.dict("os.environ", env, clear=True):
            backend = tts.select_tts_backend(system="Linux")
        self.assertIsInstance(backend, tts.PiperTTS)

    def test_fallback_uses_second_when_first_fails(self):
        class Boom:
            name = "boom"
            def speak(self, text): raise RuntimeError("network down")

        spoken = []

        class Local:
            name = "local"
            def speak(self, text): spoken.append(text)

        tts.FallbackTTS([Boom(), Local()]).speak("hello")
        self.assertEqual(spoken, ["hello"])   # prop still talks

    def test_fallback_raises_only_when_all_fail(self):
        class Boom:
            name = "boom"
            def speak(self, text): raise RuntimeError("nope")

        with self.assertRaises(tts.TTSError):
            tts.FallbackTTS([Boom(), Boom()]).speak("hello")

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

    def test_wake_word_selectable_and_manages_audio(self):
        trigger = input_trigger.select_input_trigger(
            "wake_word", self._noop, self._noop, self._noop
        )
        self.assertIsInstance(trigger, input_trigger.WakeWordTrigger)
        self.assertTrue(trigger.manages_audio)

    def test_push_to_talk_does_not_manage_audio(self):
        trigger = input_trigger.select_input_trigger(
            "push_to_talk", self._noop, self._noop, self._noop
        )
        self.assertFalse(trigger.manages_audio)

    def test_wake_word_run_without_deps_or_key_raises(self):
        # No pvporcupine / no access key / no callback → clear InputError, not a
        # cryptic crash. (CI has none of these, so the import path triggers it.)
        trigger = input_trigger.select_input_trigger(
            "wake_word", self._noop, self._noop, self._noop
        )
        with self.assertRaises(input_trigger.InputError):
            trigger.run()

    def test_wake_config_passed_through(self):
        trigger = input_trigger.select_input_trigger(
            "wake_word", self._noop, self._noop, self._noop,
            wake_config={"engine": "openwakeword", "oww_model": "alexa", "silence_ms": 750},
        )
        self.assertEqual(trigger.engine, "openwakeword")
        self.assertEqual(trigger.oww_model, "alexa")
        self.assertEqual(trigger.silence_ms, 750)

    def test_motion_selectable_and_manages_audio(self):
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop
        )
        self.assertIsInstance(trigger, input_trigger.MotionTrigger)
        self.assertTrue(trigger.manages_audio)

    def test_motion_config_passed_through(self):
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop,
            motion_config={"sensor_pin": 22, "cooldown_s": 5, "barker_lines": ["boo"]},
        )
        self.assertEqual(trigger.sensor_pin, 22)
        self.assertEqual(trigger.cooldown_s, 5)
        self.assertEqual(trigger.barker_lines, ["boo"])

    def test_motion_barker_avoids_immediate_repeat(self):
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop,
            motion_config={"barker_lines": ["a", "b"]},
        )
        first = trigger._next_barker()
        self.assertNotEqual(trigger._next_barker(), first)

    def test_motion_barker_single_line_repeats_ok(self):
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop,
            motion_config={"barker_lines": ["only"]},
        )
        self.assertEqual(trigger._next_barker(), "only")
        self.assertEqual(trigger._next_barker(), "only")

    def test_motion_no_barkers_returns_none(self):
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop,
            motion_config={"barker_lines": []},
        )
        self.assertIsNone(trigger._next_barker())

    def test_motion_run_without_gpio_raises(self):
        # No gpiozero on a Mac / CI → clear InputError, not a cryptic crash.
        trigger = input_trigger.select_input_trigger(
            "motion", self._noop, self._noop, self._noop,
            process_utterance=lambda f: None,
        )
        with self.assertRaises(input_trigger.InputError):
            trigger.run()

    def test_unknown_wake_engine_raises(self):
        trigger = input_trigger.select_input_trigger(
            "wake_word", self._noop, self._noop, self._noop,
            process_utterance=lambda f: None,
            wake_config={"engine": "bogus"},
        )
        with self.assertRaises(input_trigger.InputError):
            trigger.run()  # _make_engine rejects the unknown engine

    def test_unknown_mode_raises(self):
        with self.assertRaises(input_trigger.InputError):
            input_trigger.select_input_trigger(
                "telepathy", self._noop, self._noop, self._noop
            )


class _Stub(llm.LLMBackend):
    """Configurable test double for FallbackLLM behaviour."""

    def __init__(self, name, available=True, reply=None, fail=False):
        self.name = name
        self._available = available
        self._reply = reply
        self._fail = fail
        self.calls = 0

    def available(self):
        return self._available

    def generate(self, system, messages, max_tokens, tools=None):
        self.calls += 1
        if self._fail:
            raise llm.LLMError(f"{self.name} boom")
        return self._reply


class TestLLMSelection(unittest.TestCase):
    def test_select_claude(self):
        self.assertIsInstance(llm.select_llm_backend("claude"), llm.ClaudeBackend)

    def test_select_ollama(self):
        self.assertIsInstance(llm.select_llm_backend("ollama"), llm.OllamaBackend)

    def test_select_auto_is_fallback_claude_then_ollama(self):
        backend = llm.select_llm_backend("auto")
        self.assertIsInstance(backend, llm.FallbackLLM)
        self.assertEqual(
            [b.name for b in backend.backends], ["claude", "ollama"]
        )

    def test_unknown_mode_raises(self):
        with self.assertRaises(llm.LLMError):
            llm.select_llm_backend("gpt")

    def test_claude_available_tracks_api_key(self):
        backend = llm.ClaudeBackend()
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "x"}):
            self.assertTrue(backend.available())
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(backend.available())


class TestFallbackLLM(unittest.TestCase):
    def test_uses_first_available(self):
        primary = _Stub("claude", available=True, reply="hi from claude")
        secondary = _Stub("ollama", available=True, reply="hi from ollama")
        fb = llm.FallbackLLM([primary, secondary])
        self.assertEqual(fb.generate("sys", [], 10), "hi from claude")
        self.assertEqual(secondary.calls, 0)  # never reached

    def test_skips_unavailable_primary(self):
        primary = _Stub("claude", available=False)
        secondary = _Stub("ollama", available=True, reply="offline reply")
        fb = llm.FallbackLLM([primary, secondary])
        self.assertEqual(fb.generate("sys", [], 10), "offline reply")
        self.assertEqual(primary.calls, 0)

    def test_falls_back_when_primary_errors(self):
        primary = _Stub("claude", available=True, fail=True)
        secondary = _Stub("ollama", available=True, reply="rescued")
        fb = llm.FallbackLLM([primary, secondary])
        self.assertEqual(fb.generate("sys", [], 10), "rescued")
        self.assertEqual(primary.calls, 1)

    def test_all_fail_raises(self):
        primary = _Stub("claude", available=True, fail=True)
        secondary = _Stub("ollama", available=False)
        fb = llm.FallbackLLM([primary, secondary])
        with self.assertRaises(llm.LLMError):
            fb.generate("sys", [], 10)

    def test_empty_raises(self):
        with self.assertRaises(llm.LLMError):
            llm.FallbackLLM([])


class TestDoctor(unittest.TestCase):
    def test_anthropic_key_present(self):
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "x"}), mock.patch.object(
            doctor.config, "LLM_BACKEND", "auto"
        ):
            self.assertEqual(doctor.check_anthropic_key().status, doctor.OK)

    def test_anthropic_key_missing_auto_warns(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            doctor.config, "LLM_BACKEND", "auto"
        ):
            self.assertEqual(doctor.check_anthropic_key().status, doctor.WARN)

    def test_anthropic_key_missing_claude_fails(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            doctor.config, "LLM_BACKEND", "claude"
        ):
            self.assertEqual(doctor.check_anthropic_key().status, doctor.FAIL)

    def test_anthropic_key_na_for_ollama(self):
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            doctor.config, "LLM_BACKEND", "ollama"
        ):
            self.assertEqual(doctor.check_anthropic_key().status, doctor.OK)

    def test_sqlite_writable_ok(self):
        # The project dir is writable in the test environment.
        self.assertEqual(doctor.check_sqlite().status, doctor.OK)

    def test_motion_na_when_not_motion_mode(self):
        with mock.patch.object(doctor.config, "INPUT_MODE", "wake_word"):
            self.assertEqual(doctor.check_motion().status, doctor.OK)

    def test_wake_word_na_in_push_to_talk(self):
        with mock.patch.object(doctor.config, "INPUT_MODE", "push_to_talk"):
            self.assertEqual(doctor.check_wake_word().status, doctor.OK)

    def test_wake_word_porcupine_fails_without_key(self):
        # Force the porcupine engine with no key → deterministic FAIL.
        with mock.patch.object(doctor.config, "INPUT_MODE", "wake_word"), \
             mock.patch.object(doctor.config, "WAKE_ENGINE", "porcupine"), \
             mock.patch.object(doctor.config, "PORCUPINE_KEY", ""):
            self.assertEqual(doctor.check_wake_word().status, doctor.FAIL)

    def test_run_returns_int_and_does_not_raise(self):
        # Smoke test: full report runs end to end. AWS probe is network-tolerant.
        code = doctor.run()
        self.assertIn(code, (0, 1))


class TestCleanForSpeech(unittest.TestCase):
    def test_strips_stage_direction(self):
        self.assertEqual(
            tts.clean_for_speech("*grins toothily* Welcome, mortal."),
            "Welcome, mortal.",
        )

    def test_strips_trailing_stage_direction(self):
        self.assertEqual(
            tts.clean_for_speech("Come closer. *cackles*"), "Come closer."
        )

    def test_strips_multiple_and_collapses_space(self):
        self.assertEqual(
            tts.clean_for_speech("*sighs* Ah. *leans in* Your fate awaits."),
            "Ah. Your fate awaits.",
        )

    def test_strips_stray_markup(self):
        self.assertEqual(tts.clean_for_speech("**Boo!**"), "Boo!")

    def test_plain_text_untouched(self):
        text = "The veil grows thin tonight."
        self.assertEqual(tts.clean_for_speech(text), text)

    def test_all_stage_direction_falls_back_to_words(self):
        # Never return empty — better to say the words than go silent.
        self.assertEqual(tts.clean_for_speech("*cackles wildly*"), "cackles wildly")

    def test_empty_input_safe(self):
        self.assertEqual(tts.clean_for_speech(""), "")

    def test_underscores_in_normal_prose_kept(self):
        # A lone underscore (e.g. a filename) must not eat the sentence.
        self.assertIn("file", tts.clean_for_speech("The file_name is cursed."))


class TestAudioWatchdog(unittest.TestCase):
    """A mic that returns audio faster than real time has dropped out."""

    def _trigger(self, **kw):
        return input_trigger.select_input_trigger(
            "motion", lambda: None, lambda: None, lambda: None,
            motion_config=kw,
        )

    def test_realtime_capture_is_healthy(self):
        t = self._trigger()
        # 100 frames of 1024 @16kHz = 6.4s of audio, delivered in 6.4s: fine.
        t._check_stream_alive(100, 1024, 16000, elapsed=6.4)
        self.assertEqual(t._dead_streak, 0)

    def test_instant_capture_counts_as_dead(self):
        t = self._trigger()
        t._check_stream_alive(100, 1024, 16000, elapsed=0.01)
        self.assertEqual(t._dead_streak, 1)

    def test_raises_after_consecutive_dead_captures(self):
        t = self._trigger(max_dead_captures=3)
        t._check_stream_alive(100, 1024, 16000, elapsed=0.01)
        t._check_stream_alive(100, 1024, 16000, elapsed=0.01)
        with self.assertRaises(input_trigger.AudioStreamError):
            t._check_stream_alive(100, 1024, 16000, elapsed=0.01)

    def test_healthy_capture_resets_the_streak(self):
        # One blip must not accumulate toward a restart hours later.
        t = self._trigger(max_dead_captures=3)
        t._check_stream_alive(100, 1024, 16000, elapsed=0.01)
        t._check_stream_alive(100, 1024, 16000, elapsed=6.4)
        self.assertEqual(t._dead_streak, 0)

    def test_short_capture_is_not_judged(self):
        # A couple of frames legitimately return fast; don't call that dead.
        t = self._trigger()
        t._check_stream_alive(3, 1024, 16000, elapsed=0.001)
        self.assertEqual(t._dead_streak, 0)

    def test_audio_stream_error_is_an_input_error(self):
        # jarvis.py catches it specifically; keep the hierarchy intact.
        self.assertTrue(
            issubclass(input_trigger.AudioStreamError, input_trigger.InputError)
        )


class TestAmbience(unittest.TestCase):
    """Ambience is decoration — it must never break the prop, and must go
    silent before the mic listens."""

    def test_no_file_is_disabled(self):
        import ambience
        a = ambience.Ambience(path="", enabled=True)
        self.assertFalse(a.available())
        a.start(); a.stop()      # must not raise

    def test_missing_file_reports_and_stays_quiet(self):
        import ambience
        a = ambience.Ambience(path="/no/such/file.wav", enabled=True)
        self.assertFalse(a.available())
        self.assertIn("not found", a.error)
        a.start(); a.stop()      # must not raise

    def test_explicitly_disabled(self):
        import ambience
        a = ambience.Ambience(path="/tmp/x.wav", enabled=False)
        self.assertFalse(a.available())

    def test_stop_is_idempotent(self):
        import ambience
        a = ambience.Ambience(path="", enabled=True)
        a.stop(); a.stop()       # must not raise or hang

    def test_resume_delay_is_configurable(self):
        t = input_trigger.select_input_trigger(
            "motion", lambda: None, lambda: None, lambda: None,
            motion_config={"ambience_resume_s": 8, "cooldown_s": 20},
        )
        self.assertEqual(t.ambience_resume_s, 8)

    def test_resume_delay_defaults_sensible(self):
        t = input_trigger.select_input_trigger(
            "motion", lambda: None, lambda: None, lambda: None
        )
        # Must come back before the cooldown ends, or it's pointless.
        self.assertLess(t.ambience_resume_s, t.cooldown_s)

    def test_device_included_in_play_command(self):
        import ambience
        a = ambience.Ambience(path="/tmp/x.wav", device="plughw:3,0")
        self.assertIn("-D", a._cmd())
        self.assertIn("plughw:3,0", a._cmd())


class TestJaw(unittest.TestCase):
    """The jaw is decoration — it must never break speech, whatever goes wrong."""

    def test_disabled_jaw_is_noop(self):
        import jaw
        j = jaw.Jaw(enabled=False)
        j.start_talking(); j.stop_talking(); j.close()   # must not raise
        self.assertIsNone(j._servo)

    def test_missing_hardware_degrades_quietly(self):
        import jaw
        j = jaw.Jaw(enabled=True)     # no gpiozero/servo on a Mac or in CI
        j.start_talking(); j.stop_talking(); j.close()   # must not raise
        self.assertIsNotNone(j.error)

    def test_angles_are_clamped_to_servo_range(self):
        import jaw
        moved = []

        class FakeServo:
            angle = 0
            def __setattr__(self, k, v): moved.append(v)
            def detach(self): pass
            def close(self): pass

        j = jaw.Jaw(enabled=True, min_angle=-45, max_angle=45)
        j._servo = FakeServo()
        j._move_to(999)      # way past the mechanical limit
        j._move_to(-999)
        self.assertEqual(moved, [45, -45])

    def test_stop_talking_is_idempotent(self):
        import jaw
        j = jaw.Jaw(enabled=True)
        j.stop_talking(); j.stop_talking()   # must not raise or hang


class TestBarkerGeneration(unittest.TestCase):
    """Generated barkers must never stop the prop starting."""

    def _run(self, reply=None, boom=False):
        import barkers

        class FakeLLM:
            def generate(self, **kw):
                if boom:
                    raise RuntimeError("network down")
                return reply

        return barkers.build(FakeLLM())

    def test_parses_plain_lines(self):
        out = self._run("One line here.\nTwo line here.\nThree.\nFour.\nFive.")
        self.assertEqual(len(out), 5)

    def test_strips_numbering_and_quotes(self):
        out = self._run('1. "First."\n2) Second.\n- Third.\n• Fourth.\nFifth.')
        self.assertIn("First.", out)
        self.assertIn("Second.", out)
        self.assertIn("Third.", out)

    def test_dedupes(self):
        out = self._run("Same.\nSame.\nOther.\nThird.\nFourth.")
        self.assertEqual(len([x for x in out if x == "Same."]), 1)

    def test_falls_back_when_llm_fails(self):
        import config
        self.assertEqual(self._run(boom=True), config.BARKER_LINES)

    def test_falls_back_when_too_few_lines(self):
        import config
        self.assertEqual(self._run("Only one."), config.BARKER_LINES)

    def test_disabled_uses_configured_lines(self):
        import barkers, config
        with mock.patch.object(config, "BARKER_GENERATE", False):
            self.assertEqual(barkers.build(None), config.BARKER_LINES)

    def test_no_heavy_imports(self):
        """CI installs no audio/ML stack — barkers must stay light."""
        import barkers
        self.assertFalse(hasattr(barkers, "np"))
        self.assertFalse(hasattr(barkers, "sd"))


class TestJogControls(unittest.TestCase):
    """Key decoding and clamping — the parts that don't need a servo."""

    def _keys(self, data):
        import io, jog
        return jog.read_key(io.StringIO(data), timeout=0)

    def test_arrow_keys_decode(self):
        self.assertEqual(self._keys("\x1b[A"), "up")
        self.assertEqual(self._keys("\x1b[B"), "down")
        self.assertEqual(self._keys("\x1b[C"), "right")
        self.assertEqual(self._keys("\x1b[D"), "left")

    def test_plain_keys_pass_through(self):
        self.assertEqual(self._keys("m"), "m")
        self.assertEqual(self._keys("q"), "q")

    def test_clamps_to_servo_range(self):
        import jog
        self.assertEqual(jog.clamp(99, -45, 45), (45, True))
        self.assertEqual(jog.clamp(-99, -45, 45), (-45, True))
        self.assertEqual(jog.clamp(10, -45, 45), (10, False))

    def test_limit_is_reported(self):
        """Silently clamping would look like a dead servo mid-calibration."""
        import jog
        _, limited = jog.clamp(46, -45, 45)
        self.assertTrue(limited)

    def test_non_tty_refuses_rather_than_hangs(self):
        import jog
        with mock.patch("sys.stdin.isatty", return_value=False):
            self.assertEqual(jog.run(), 1)


class TestFlushDetection(unittest.TestCase):
    """A flush must be told apart from a voice — and never eat a question."""

    RATE = 16000

    def _noise(self, seconds=6.0, amplitude=3000):
        """Broadband noise ≈ rushing water."""
        import numpy as np
        rng = np.random.default_rng(0)
        n = int(self.RATE * seconds)
        return (rng.normal(0, amplitude, n)).astype("int16").reshape(-1, 1)

    def _voice(self, seconds=6.0, amplitude=3000):
        """Harmonic tone with gaps between 'words' ≈ speech."""
        import numpy as np
        n = int(self.RATE * seconds)
        t = np.arange(n) / self.RATE
        # 150Hz fundamental + harmonics: energy in peaks, not spread out.
        wave = sum(np.sin(2 * np.pi * 150 * k * t) / k for k in (1, 2, 3, 4))
        wave *= amplitude / 2
        # Silence every other 300ms — the gaps a real speaker leaves.
        gate = ((t * 1000 // 300) % 2 == 0).astype(float)
        return (wave * gate).astype("int16").reshape(-1, 1)

    def _detector(self, **kw):
        import flush
        kw.setdefault("enabled", True)
        return flush.FlushDetector(**kw)

    def test_noise_reads_as_flush(self):
        self.assertTrue(self._detector().matches(self._noise(), self.RATE))

    def test_speech_does_not_read_as_flush(self):
        self.assertFalse(self._detector().matches(self._voice(), self.RATE))

    def test_flatness_separates_them(self):
        """The discriminator the whole design leans on."""
        d = self._detector()
        noise = d.measure(self._noise(), self.RATE).flatness
        voice = d.measure(self._voice(), self.RATE).flatness
        self.assertGreater(noise, voice * 2)

    def test_short_burst_is_not_a_flush(self):
        """A door slam is broadband too — duration is what rules it out."""
        self.assertFalse(
            self._detector().matches(self._noise(seconds=0.4), self.RATE))

    def test_quiet_noise_is_not_a_flush(self):
        self.assertFalse(
            self._detector().matches(self._noise(amplitude=50), self.RATE))

    def test_disabled_never_matches(self):
        self.assertFalse(
            self._detector(enabled=False).matches(self._noise(), self.RATE))

    def test_empty_and_none_are_safe(self):
        d = self._detector()
        self.assertFalse(d.matches([], self.RATE))
        self.assertFalse(d.matches(None, self.RATE))

    def test_broken_input_falls_through_to_transcription(self):
        """Any failure must return False so the question still gets heard."""
        self.assertFalse(self._detector().matches(["not audio"], self.RATE))

    def test_explain_reports_every_check(self):
        out = self._detector().explain(self._noise(), self.RATE)
        for field in ("duration", "rms", "flatness", "sustained"):
            self.assertIn(field, out)


class TestFlushLines(unittest.TestCase):

    def test_generation_falls_back_on_failure(self):
        import barkers, config

        class Boom:
            def generate(self, **kw):
                raise RuntimeError("no network")

        self.assertEqual(barkers.build_flush_lines(Boom()), config.FLUSH_LINES)

    def test_disabled_uses_configured_lines(self):
        import barkers, config
        with mock.patch.object(config, "FLUSH_GENERATE", False):
            self.assertEqual(barkers.build_flush_lines(None), config.FLUSH_LINES)

    def test_defaults_exist_for_offline_use(self):
        import config
        self.assertGreaterEqual(len(config.FLUSH_LINES), 4)


class TestEyes(unittest.TestCase):
    """Eyes are decoration — they must never break speech."""

    def test_disabled_is_noop(self):
        import eyes
        e = eyes.Eyes(enabled=False)
        e.idle(); e.alert(); e.start_talking(); e.stop_talking(); e.close()
        self.assertIsNone(e._led)

    def test_missing_hardware_degrades_quietly(self):
        import eyes
        e = eyes.Eyes(enabled=True)      # no gpiozero/LEDs in CI
        e.idle(); e.alert(); e.start_talking(); e.stop_talking(); e.close()
        self.assertIsNotNone(e.error)

    def test_levels_clamped_to_pwm_range(self):
        import eyes
        e = eyes.Eyes(idle_level=-5, alert_level=0.5, talk_level=99)
        self.assertEqual(e.idle_level, 0.0)
        self.assertEqual(e.talk_level, 1.0)

    def test_set_clamps_out_of_range(self):
        import eyes
        applied = []

        class FakeLED:
            def __setattr__(self, k, v): applied.append(v)
            def off(self): pass
            def close(self): pass

        e = eyes.Eyes(enabled=True)
        e._led = FakeLED()
        e._set(5); e._set(-2)
        self.assertEqual(applied, [1.0, 0.0])

    def test_stop_talking_is_idempotent(self):
        import eyes
        e = eyes.Eyes(enabled=True)
        e.stop_talking(); e.stop_talking()


class TestPersonas(unittest.TestCase):
    """Every persona must supply a prompt + spoken greeting/farewell."""

    def test_all_personas_complete(self):
        import config
        for name, persona in config._PERSONAS.items():
            for field in ("prompt", "greeting", "farewell"):
                self.assertTrue(persona.get(field), f"{name} missing {field}")

    def test_skull_persona_differs_from_jarvis(self):
        import config
        self.assertNotEqual(
            config._PERSONAS["skull"]["greeting"],
            config._PERSONAS["jarvis"]["greeting"],
        )


class TestTools(unittest.TestCase):
    def test_datetime_tool_returns_string(self):
        out = tools.get_current_datetime()
        self.assertIn(str(datetime_now_year()), out)

    def test_registry_schemas_shape(self):
        reg = tools.ToolRegistry([tools._DATETIME_TOOL])
        schemas = reg.anthropic_schemas()
        self.assertEqual(schemas[0]["name"], "get_current_datetime")
        self.assertIn("input_schema", schemas[0])

    def test_registry_run_dispatches(self):
        reg = tools.ToolRegistry([tools._DATETIME_TOOL])
        self.assertIn("It is", reg.run("get_current_datetime", {}))

    def test_registry_unknown_tool_is_graceful(self):
        reg = tools.ToolRegistry([tools._DATETIME_TOOL])
        self.assertIn("Unknown tool", reg.run("nope", {}))

    def test_tool_errors_are_caught_not_raised(self):
        bad = tools.Tool("bad", "boom", {"type": "object", "properties": {}},
                         func=lambda: (_ for _ in ()).throw(RuntimeError("x")))
        reg = tools.ToolRegistry([bad])
        self.assertIn("errored", reg.run("bad", {}))

    def test_build_registry_disabled(self):
        with mock.patch.object(tools.config, "ENABLE_TOOLS", False):
            self.assertFalse(tools.build_registry())

    def test_build_registry_has_core_tools(self):
        with mock.patch.object(tools.config, "ENABLE_TOOLS", True):
            reg = tools.build_registry()
        self.assertIn("get_current_datetime", reg.names)
        self.assertIn("get_weather", reg.names)


def datetime_now_year():
    import datetime as _dt
    return _dt.datetime.now().year


# Minimal fakes for Claude's tool-use response objects.
class _Block:
    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input
        self.id = id


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class TestClaudeToolLoop(unittest.TestCase):
    def test_tool_use_then_final_answer(self):
        calls = {"n": 0}

        class FakeMessages:
            def create(self, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    return _Resp("tool_use", [
                        _Block("tool_use", name="get_weather",
                               input={"location": "Auckland"}, id="t1"),
                    ])
                # second call should include the tool_result we appended
                return _Resp("end_turn", [_Block("text", text="It's sunny.")])

        class FakeClient:
            messages = FakeMessages()

        backend = llm.ClaudeBackend()
        backend._client = FakeClient()

        reg = tools.ToolRegistry([
            tools.Tool("get_weather", "w",
                       {"type": "object", "properties": {}},
                       func=lambda location: f"Sunny in {location}")
        ])
        out = backend.generate("sys", [{"role": "user", "content": "weather?"}], 100, tools=reg)
        self.assertEqual(out, "It's sunny.")
        self.assertEqual(calls["n"], 2)  # one tool round + final

    def test_no_tools_plain_text(self):
        class FakeMessages:
            def create(self, **kwargs):
                assert "tools" not in kwargs  # none passed
                return _Resp("end_turn", [_Block("text", text="hello")])

        class FakeClient:
            messages = FakeMessages()

        backend = llm.ClaudeBackend()
        backend._client = FakeClient()
        self.assertEqual(
            backend.generate("sys", [{"role": "user", "content": "hi"}], 100), "hello"
        )


if __name__ == "__main__":
    unittest.main()
