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

SYSTEM_PROMPT = (
    "You are Jarvis, a sharp and concise AI assistant. "
    "Keep responses to 2-3 sentences unless the user asks for detail. "
    "Be direct, intelligent, occasionally dry. No filler phrases."
)
