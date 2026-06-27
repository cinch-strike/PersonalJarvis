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
