"""
Centralised configuration for Jarvis.
─────────────────────────────────────
All environment-specific knobs live here so the Mac (Phase 1) vs Pi (Phase 2)
differences are in one place. Every setting reads an env var with a sensible
default, so the defaults reproduce Phase 1 behaviour exactly on a Mac.

Env vars:
  JARVIS_WHISPER_MODEL   Whisper model size. Default "base".
  JARVIS_VOICE           macOS `say` voice. Default "Daniel".
  JARVIS_SAMPLE_RATE     Mic sample rate (Hz). Default 16000.
  JARVIS_CLAUDE_MODEL    Claude model id. Default "claude-opus-4-8".
  JARVIS_TTS_BACKEND     Force a TTS backend (say|piper|espeak). Default auto.
  JARVIS_INPUT_MODE      Recording trigger (push_to_talk|wake_word).
                         Default "push_to_talk".
  JARVIS_PIPER_MODEL     Path to a piper .onnx voice (Linux/piper only).
  JARVIS_PIPER_RATE      piper playback sample rate. Default 22050.
  JARVIS_LLM_BACKEND     LLM selection (auto|claude|ollama). Default "auto"
                         (Claude when reachable, else Ollama offline).
  JARVIS_OLLAMA_MODEL    Ollama model tag. Default "llama3.1".
  JARVIS_OLLAMA_HOST     Ollama server URL. Default "http://localhost:11434".
  JARVIS_ENABLE_TOOLS    Enable Claude tools (datetime/weather/web search).
                         Default true.
  JARVIS_TAVILY_KEY      Optional Tavily key for better web search (else keyless
                         DuckDuckGo).
  JARVIS_WAKE_ENGINE     Wake engine (auto|porcupine|openwakeword). Default
                         "auto" = Porcupine if a key is set, else openWakeWord.
  JARVIS_PORCUPINE_KEY   Picovoice access key (Porcupine only; now needs
                         commercial approval — openWakeWord needs no key).
  JARVIS_WAKE_KEYWORD    Porcupine built-in keyword. Default "jarvis".
  JARVIS_OWW_MODEL       openWakeWord model name. Default "hey_jarvis".
  JARVIS_OWW_THRESHOLD   openWakeWord detection threshold 0-1. Default 0.5.
  JARVIS_AUDIO_DEVICE    sounddevice input device (index or name). Default
                         system default. Set to the ReSpeaker if needed.
  JARVIS_AUDIO_CHANNELS  Capture channels. Default 1.
  JARVIS_AUDIO_OUTPUT    ALSA playback device for TTS (Linux), e.g. "plughw:3,0".
                         Default: espeak/piper use the system default output.
  JARVIS_VAD_SILENCE     RMS energy below which a frame counts as silence.
                         Default 500. Lower if it cuts you off; raise if it
                         never stops.
  JARVIS_VAD_SILENCE_MS  Trailing silence (ms) that ends a question. Default 1000.
  JARVIS_MAX_UTTERANCE_S Hard cap on a single question (s). Default 15.
"""

import os

WHISPER_MODEL = os.environ.get("JARVIS_WHISPER_MODEL", "base")
VOICE = os.environ.get("JARVIS_VOICE", "Daniel")
SAMPLE_RATE = int(os.environ.get("JARVIS_SAMPLE_RATE", "16000"))

# Claude model. Default is the current model (claude-opus-4-8); override via env.
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "claude-opus-4-8")

# Backend selection (consumed by tts.py / input.py). None means auto-detect.
TTS_BACKEND = os.environ.get("JARVIS_TTS_BACKEND") or None
INPUT_MODE = os.environ.get("JARVIS_INPUT_MODE", "push_to_talk")

# LLM backend (consumed by llm.py). "auto" = Claude online, fall back to Ollama.
LLM_BACKEND = os.environ.get("JARVIS_LLM_BACKEND", "auto")
OLLAMA_MODEL = os.environ.get("JARVIS_OLLAMA_MODEL", "llama3.1")
OLLAMA_HOST = os.environ.get("JARVIS_OLLAMA_HOST", "http://localhost:11434")

# How many tokens Jarvis may generate per reply.
MAX_TOKENS = int(os.environ.get("JARVIS_MAX_TOKENS", "600"))

# Tools (Claude function-calling): live date/time, weather, web search.
ENABLE_TOOLS = os.environ.get("JARVIS_ENABLE_TOOLS", "true").lower() in (
    "1", "true", "yes", "on"
)
# Optional: better web search than keyless DuckDuckGo (free key: tavily.com).
TAVILY_KEY = os.environ.get("JARVIS_TAVILY_KEY", "")


def _audio_device():
    """Input device: an int index if numeric, else a name string, else None."""
    raw = os.environ.get("JARVIS_AUDIO_DEVICE")
    if not raw:
        return None
    return int(raw) if raw.isdigit() else raw


# Wake-word (consumed by input_trigger.WakeWordTrigger) + audio capture.
# Engine: "auto" → Porcupine if a key is set, else keyless openWakeWord.
WAKE_ENGINE = os.environ.get("JARVIS_WAKE_ENGINE", "auto")
PORCUPINE_KEY = os.environ.get("JARVIS_PORCUPINE_KEY", "")
WAKE_KEYWORD = os.environ.get("JARVIS_WAKE_KEYWORD", "jarvis")   # Porcupine keyword
OWW_MODEL = os.environ.get("JARVIS_OWW_MODEL", "hey_jarvis")     # openWakeWord model
OWW_THRESHOLD = float(os.environ.get("JARVIS_OWW_THRESHOLD", "0.5"))
AUDIO_DEVICE = _audio_device()
AUDIO_CHANNELS = int(os.environ.get("JARVIS_AUDIO_CHANNELS", "1"))
# ALSA playback device for TTS (Linux). e.g. "plughw:3,0" for a USB speaker.
AUDIO_OUTPUT = os.environ.get("JARVIS_AUDIO_OUTPUT") or None
VAD_SILENCE = float(os.environ.get("JARVIS_VAD_SILENCE", "500"))
VAD_SILENCE_MS = int(os.environ.get("JARVIS_VAD_SILENCE_MS", "1000"))
MAX_UTTERANCE_S = int(os.environ.get("JARVIS_MAX_UTTERANCE_S", "15"))

SYSTEM_PROMPT = (
    "You are Jarvis, a sharp and concise AI assistant. "
    "Keep responses to 2-3 sentences unless the user asks for detail. "
    "Be direct, intelligent, occasionally dry. No filler phrases."
)
