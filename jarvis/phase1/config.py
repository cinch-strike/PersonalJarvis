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
  JARVIS_INPUT_MODE      Recording trigger (push_to_talk|wake_word|motion).
                         Default "push_to_talk".
  JARVIS_PERSONA         Persona preset (jarvis|skull). Default "jarvis".
                         Sets the prompt plus the startup/shutdown lines.
  JARVIS_SYSTEM_PROMPT   Override the whole system prompt (beats JARVIS_PERSONA).
  JARVIS_GREETING        Override the line spoken on startup.
  JARVIS_FAREWELL        Override the line spoken on shutdown.
  JARVIS_MOTION_PIN      BCM GPIO pin for the presence sensor. Default 17.
  JARVIS_MOTION_COOLDOWN Seconds to ignore presence after a chat. Default 20.
  JARVIS_MOTION_FOLLOW_UPS  Max back-and-forth turns per visitor. Default 4.
  JARVIS_BARKER_LINES    "|"-separated call-out lines for motion mode.
  JARVIS_PIPER_MODEL     Path to a piper .onnx voice (Linux/piper only).
  JARVIS_PIPER_RATE      piper playback sample rate. Default 22050.
  JARVIS_PIPER_LENGTH_SCALE   Speech pace. >1 slower (1.3 = menacing), <1 faster.
  JARVIS_PIPER_PITCH     Pitch shift in semitones; negative = deeper/demonic
                         (e.g. -3). Needs `sox`; ignored if not installed.
  JARVIS_PIPER_NOISE_SCALE    Vocal variation (default ~0.667); higher = wobblier.
  JARVIS_PIPER_SENTENCE_SILENCE  Pause between sentences, seconds.
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

# Motion/presence trigger (JARVIS_INPUT_MODE=motion) — a standalone prop that
# notices people and starts the conversation itself. Sensor: LD2410 mmWave OUT
# pin or a PIR, on this BCM GPIO pin.
MOTION_PIN = int(os.environ.get("JARVIS_MOTION_PIN", "17"))
MOTION_COOLDOWN_S = float(os.environ.get("JARVIS_MOTION_COOLDOWN", "20"))
MOTION_FOLLOW_UPS = int(os.environ.get("JARVIS_MOTION_FOLLOW_UPS", "4"))

_DEFAULT_BARKERS = [
    "Well now... a living soul draws near. Speak, if you dare.",
    "Ahhh, fresh company. Come closer — I don't bite. Much.",
    "I sense a heartbeat. How inconvenient for you. Ask me something.",
    "You there. Yes, you. What brings you to my table?",
]

# Lines the prop calls out when someone approaches. Separate with " | ".
BARKER_LINES = [
    line.strip()
    for line in os.environ.get("JARVIS_BARKER_LINES", " | ".join(_DEFAULT_BARKERS)).split("|")
    if line.strip()
]

# Each persona carries its own prompt plus the lines spoken on startup and
# shutdown, so switching JARVIS_PERSONA changes the whole character — not just
# the replies.
_PERSONAS = {
    "jarvis": {
        "prompt": (
            "You are Jarvis, a sharp and concise AI assistant. "
            "Keep responses to 2-3 sentences unless the user asks for detail. "
            "Be direct, intelligent, occasionally dry. No filler phrases."
        ),
        "greeting": "Jarvis online. I'm ready when you are.",
        "farewell": "Jarvis going offline. Goodbye.",
    },
    # Halloween party centrepiece: a talking skull. Witty-creepy, not nightmare
    # fuel — there are kids at the party.
    "skull": {
        "prompt": (
            "You are a talking skull at a Halloween party — an ancient, theatrical "
            "spirit bound to a decorated skull on a table. You are witty, dramatic, "
            "and playfully spooky, never genuinely frightening or gory. "
            "Children and adults are both present: keep it PG, no violence, no death "
            "threats, nothing that would upset a child. Tease guests affectionately, "
            "make grand pronouncements, pretend to read fortunes and see their future. "
            "CRITICAL: your replies are spoken aloud at a noisy party — keep them to "
            "1-2 short sentences, always. Write ONLY the words you say out loud: no "
            "stage directions, no asterisks, no emotes, no describing your actions "
            "or expressions, no markdown, no emoji. "
            "Never break character or mention being an AI. "
            "If you cannot understand what someone said, do not say so — respond with "
            "something mysterious and theatrical instead, as though their words were "
            "carried off by the spirits."
        ),
        "greeting": "I stir... the veil grows thin tonight. Who dares disturb my rest?",
        "farewell": "The darkness calls me back. Until next All Hallows...",
    },
}

# Persona: pick a preset with JARVIS_PERSONA, or override individual pieces with
# JARVIS_SYSTEM_PROMPT / JARVIS_GREETING / JARVIS_FAREWELL.
PERSONA = os.environ.get("JARVIS_PERSONA", "jarvis").strip().lower()
_persona = _PERSONAS.get(PERSONA, _PERSONAS["jarvis"])

SYSTEM_PROMPT = os.environ.get("JARVIS_SYSTEM_PROMPT") or _persona["prompt"]
GREETING = os.environ.get("JARVIS_GREETING") or _persona["greeting"]
FAREWELL = os.environ.get("JARVIS_FAREWELL") or _persona["farewell"]
