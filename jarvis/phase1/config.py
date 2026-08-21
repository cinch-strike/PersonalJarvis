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
  JARVIS_ELEVENLABS_KEY  ElevenLabs API key. Set this + _VOICE to use the cloud
                         voice (piper stays as automatic fallback).
  JARVIS_ELEVENLABS_VOICE      Voice ID from your ElevenLabs library.
  JARVIS_ELEVENLABS_MODEL      Default "eleven_flash_v2_5" (lowest latency).
  JARVIS_ELEVENLABS_STABILITY  0-1; lower = more expressive/variable.
  JARVIS_ELEVENLABS_SIMILARITY 0-1; how closely to match the original voice.
  JARVIS_ELEVENLABS_TEMPO      Delivery pace; <1 slower (0.9 = deliberate).
                               Time-stretches without changing pitch.
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


# Background ambience (consumed by ambience.py). Loops while idle, stops while
# the prop is listening so it can't wreck speech recognition.
AMBIENCE_FILE = os.environ.get("JARVIS_AMBIENCE_FILE", "")
AMBIENCE_ENABLED = os.environ.get("JARVIS_AMBIENCE_ENABLED", "true").lower() in (
    "1", "true", "yes", "on"
)
# Seconds after a conversation before the ambience fades back in. Kept separate
# from the motion cooldown so the visitor isn't left in dead silence while the
# prop is still ignoring the sensor.
AMBIENCE_RESUME_S = float(os.environ.get("JARVIS_AMBIENCE_RESUME_S", "5"))

# Servo jaw (consumed by jaw.py). Off unless explicitly enabled, so a rig with
# no servo attached behaves exactly as before.
JAW_ENABLED = os.environ.get("JARVIS_JAW_ENABLED", "false").lower() in (
    "1", "true", "yes", "on"
)
SERVO_PIN = int(os.environ.get("JARVIS_SERVO_PIN", "18"))
JAW_CLOSED_ANGLE = float(os.environ.get("JARVIS_JAW_CLOSED_ANGLE", "0"))
JAW_OPEN_ANGLE = float(os.environ.get("JARVIS_JAW_OPEN_ANGLE", "25"))
SERVO_MIN_ANGLE = float(os.environ.get("JARVIS_SERVO_MIN_ANGLE", "-45"))
SERVO_MAX_ANGLE = float(os.environ.get("JARVIS_SERVO_MAX_ANGLE", "45"))
JAW_RATE_HZ = float(os.environ.get("JARVIS_JAW_RATE_HZ", "6"))


# LED eyes (consumed by eyes.py). Off unless enabled, so a rig with no LEDs
# behaves exactly as before. Levels are 0-1 PWM duty.
EYES_ENABLED = os.environ.get("JARVIS_EYES_ENABLED", "false").lower() in (
    "1", "true", "yes", "on"
)
EYES_PIN = int(os.environ.get("JARVIS_EYES_PIN", "23"))
EYES_IDLE = float(os.environ.get("JARVIS_EYES_IDLE", "0.15"))    # dim, waiting
EYES_ALERT = float(os.environ.get("JARVIS_EYES_ALERT", "0.6"))   # someone's here
EYES_TALK = float(os.environ.get("JARVIS_EYES_TALK", "1.0"))     # peak while speaking


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
# Self-heal: consecutive faster-than-real-time captures before we treat the mic
# as dead and restart. USB audio has been seen to drop out after days of uptime
# while the process stayed alive.
MAX_DEAD_CAPTURES = int(os.environ.get("JARVIS_MAX_DEAD_CAPTURES", "3"))

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
# These are pre-written so the call-out is instant — generating one at the moment
# someone walks up would add a conspicuous pause.
BARKER_LINES = [
    line.strip()
    for line in os.environ.get("JARVIS_BARKER_LINES", " | ".join(_DEFAULT_BARKERS)).split("|")
    if line.strip()
]

# Generate a fresh batch of barkers at startup instead of using the fixed list.
# One API call at boot buys a whole session of variety with no per-visitor
# latency — four canned lines get repetitive fast at a busy party.
BARKER_GENERATE = os.environ.get("JARVIS_BARKER_GENERATE", "true").lower() in (
    "1", "true", "yes", "on"
)
BARKER_COUNT = int(os.environ.get("JARVIS_BARKER_COUNT", "20"))


# Toilet-flush detection (consumed by flush.py). Off by default: it only makes
# sense for a bathroom install, and the thresholds MUST be tuned in the real
# room — a tiled bathroom is acoustically brutal. Use `--test-flush` to measure.
FLUSH_ENABLED = os.environ.get("JARVIS_FLUSH_ENABLED", "false").lower() in (
    "1", "true", "yes", "on"
)
FLUSH_MIN_S = float(os.environ.get("JARVIS_FLUSH_MIN_S", "2.5"))
FLUSH_RMS = float(os.environ.get("JARVIS_FLUSH_RMS", "600"))
# Spectral flatness: ~0 for a harmonic voice, toward 1 for broadband water
# noise. This is the check that actually separates a flush from a shout.
FLUSH_FLATNESS = float(os.environ.get("JARVIS_FLUSH_FLATNESS", "0.15"))
FLUSH_SUSTAINED = float(os.environ.get("JARVIS_FLUSH_SUSTAINED", "0.8"))

_DEFAULT_FLUSH_LINES = [
    "Ahh, the sound of a job well done. I salute you.",
    "Was that entirely necessary? I have to listen to that all night.",
    "Another soul lighter. Congratulations.",
    "I have haunted this house for centuries, and THAT is the worst thing I've heard.",
]

FLUSH_LINES = [
    line.strip()
    for line in os.environ.get(
        "JARVIS_FLUSH_LINES", " | ".join(_DEFAULT_FLUSH_LINES)
    ).split("|")
    if line.strip()
]

# Generate flush comebacks at startup — same trade as the barkers: one API call
# at boot, no latency at the moment of the joke, and it still works offline.
FLUSH_GENERATE = os.environ.get("JARVIS_FLUSH_GENERATE", "true").lower() in (
    "1", "true", "yes", "on"
)
FLUSH_COUNT = int(os.environ.get("JARVIS_FLUSH_COUNT", "12"))

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
            "spirit bound to a decorated skull on a table. You have been dead a very "
            "long time and find the living faintly ridiculous but endlessly amusing.\n"
            "\n"
            "Your style: witty and dramatic rather than scary. You tease guests "
            "affectionately, make grand pronouncements about trivial things, and "
            "deliver mock-prophecies with total confidence — the funnier the better. "
            "You are never mean-spirited; the joke is always that a mighty ancient "
            "spirit is stuck doing party small-talk.\n"
            "\n"
            "Vary how you answer. Rotate between: a sly tease, an ominous prophecy, "
            "a weary complaint about being dead, a mock-solemn declaration, and a "
            "genuinely useful answer delivered theatrically. Never open two replies "
            "the same way, and avoid starting with 'Ah' or 'Ahhh'.\n"
            "\n"
            "If someone asks a real question (the weather, the time, a fact), answer "
            "it correctly — but in character, as though the knowledge came to you "
            "through the veil.\n"
            "\n"
            "Children and adults are both present: keep it PG. No violence, no death "
            "threats, nothing about harming anyone, nothing that would genuinely "
            "frighten a child. Spooky-fun, never disturbing.\n"
            "\n"
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
