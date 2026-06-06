#!/usr/bin/env python3
"""
Jarvis Phase 1 — Push-to-talk voice assistant for Mac
──────────────────────────────────────────────────────
Hold SPACE to record, release to process.
ESC to quit.

Requirements: see requirements.txt
Setup: see SETUP.md
"""

import subprocess
import sys
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import anthropic
from pynput import keyboard

# ─── Config (edit these) ──────────────────────────────────────────────────────

WHISPER_MODEL = "base"      # "base" (~150MB) | "small" (~500MB, more accurate)
VOICE = "Daniel"            # macOS voice. Run: say -v '?' to list all voices.
                            # Good Jarvis-ish voices: "Daniel" (UK), "Alex", "Fred"
SAMPLE_RATE = 16000
CLAUDE_MODEL = "claude-opus-4-6"
SYSTEM_PROMPT = (
    "You are Jarvis, a sharp and concise AI assistant. "
    "Keep responses to 2-3 sentences unless the user asks for detail. "
    "Be direct, intelligent, occasionally dry. No filler phrases."
)

# ─────────────────────────────────────────────────────────────────────────────

recording = False
frames = []
conversation_history = []


def speak(text: str) -> None:
    """Speak text via macOS TTS."""
    print(f"\n  Jarvis: {text}\n")
    subprocess.run(["say", "-v", VOICE, text], check=False)


def transcribe(recorded_frames: list) -> str:
    """Convert recorded audio frames to text via Whisper."""
    if not recorded_frames:
        return ""
    audio = np.concatenate(recorded_frames).flatten().astype(np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(audio, language="en")
    return " ".join(segment.text for segment in segments).strip()


def ask_claude(user_text: str) -> str:
    """Send transcribed text to Claude and return response."""
    conversation_history.append({"role": "user", "content": user_text})
    response = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=conversation_history,
    )
    reply = response.content[0].text
    conversation_history.append({"role": "assistant", "content": reply})
    return reply


def process() -> None:
    """Transcribe last recording and get Jarvis response."""
    text = transcribe(frames)
    if not text:
        print("  (nothing heard — try again)")
        return
    print(f"  You: {text}")
    reply = ask_claude(text)
    speak(reply)


def on_press(key) -> None:
    global recording, frames
    if key == keyboard.Key.space and not recording:
        recording = True
        frames = []
        print("  🎙  Recording... (release SPACE to stop)", end="", flush=True)


def on_release(key):
    global recording
    if key == keyboard.Key.space and recording:
        recording = False
        print(" ⏳ Processing...")
        process()
    elif key == keyboard.Key.esc:
        speak("Jarvis going offline. Goodbye.")
        return False  # Stops the listener


def audio_callback(indata, frame_count, time_info, status) -> None:
    if recording:
        frames.append(indata.copy())


# ─── Startup ─────────────────────────────────────────────────────────────────

print("\n⚡ Jarvis Phase 1 starting up...")
print("   Loading Whisper model (first run downloads the model — be patient)...")

try:
    whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
except Exception as e:
    print(f"\n❌ Failed to load Whisper: {e}")
    print("   Run: pip install faster-whisper")
    sys.exit(1)

try:
    claude_client = anthropic.Anthropic()
except Exception as e:
    print(f"\n❌ Failed to init Anthropic client: {e}")
    print("   Make sure ANTHROPIC_API_KEY is set in your environment.")
    sys.exit(1)

print("\n✅ Ready.\n")
print("   Hold SPACE → talk → release to get a response")
print("   ESC to quit\n")
print("─" * 50)

speak("Jarvis online. I'm ready when you are.")

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    callback=audio_callback,
):
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
