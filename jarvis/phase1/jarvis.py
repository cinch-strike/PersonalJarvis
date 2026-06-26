#!/usr/bin/env python3
"""
Jarvis Phase 1 — voice assistant
────────────────────────────────
Default (push-to-talk): hold SPACE to record, release to process, ESC to quit.

Platform-portable: TTS and the recording trigger are selected at startup from
the OS / env (see config.py). Phase 1 on a Mac behaves exactly as before.

  python jarvis.py            run normally
  python jarvis.py --check    print selected backends without opening the mic
  python jarvis.py --doctor   full environment readiness probe (no mic/model)

Requirements: see requirements-*.txt
Setup: see SETUP.md
"""

import platform
import sys

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

import memory
import aws_sync
import tts
import input_trigger
import llm
import config

# ─── Runtime state ────────────────────────────────────────────────────────────

recording = False
frames = []
conversation_history = []
session_id = None       # set in startup via memory.start_session()
system_prompt = None    # base persona + recalled memory
whisper_model = None
llm_backend = None
tts_backend = None


def build_system_prompt() -> str:
    """Base persona + any recalled memory from prior sessions."""
    recent = memory.load_recent_turns(n=20)
    if not recent:
        return config.SYSTEM_PROMPT
    lines = [f"{turn['role']}: {turn['content']}" for turn in recent]
    recalled = "\n".join(lines)
    return (
        f"{config.SYSTEM_PROMPT}\n\n"
        "Here is the most recent prior conversation for context "
        "(use it to stay consistent; do not repeat it back verbatim):\n"
        f"{recalled}"
    )


def speak(text: str) -> None:
    """Speak text via the active, platform-selected TTS backend."""
    print(f"\n  Jarvis: {text}\n")
    tts_backend.speak(text)


def transcribe(recorded_frames: list) -> str:
    """Convert recorded audio frames to text via Whisper."""
    if not recorded_frames:
        return ""
    audio = np.concatenate(recorded_frames).flatten().astype(np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(audio, language="en")
    return " ".join(segment.text for segment in segments).strip()


def ask_llm(user_text: str) -> str:
    """Send transcribed text to the active LLM backend and return its response."""
    conversation_history.append({"role": "user", "content": user_text})
    memory.save_turn(session_id, "user", user_text)
    reply = llm_backend.generate(
        system=system_prompt,
        messages=conversation_history,
        max_tokens=config.MAX_TOKENS,
    )
    conversation_history.append({"role": "assistant", "content": reply})
    memory.save_turn(session_id, "assistant", reply)
    return reply


def handle_utterance(captured: list) -> None:
    """Transcribe a captured recording, get a reply, and speak it.

    Used directly by audio-managing triggers (wake_word), and by push_to_talk
    via process() below.
    """
    text = transcribe(captured)
    if not text:
        print("  (nothing heard — try again)")
        return
    print(f"  You: {text}")
    reply = ask_llm(text)
    speak(reply)


def process() -> None:
    """Process the frames the main audio callback collected (push_to_talk)."""
    handle_utterance(frames)


# ─── Input-trigger callbacks ──────────────────────────────────────────────────
# push_to_talk uses these to flip record state; the audio callback streams
# frames while `recording` is True. (The trigger itself prints the UI hints.)

def start_recording() -> None:
    global recording, frames
    recording = True
    frames = []


def stop_recording() -> None:
    global recording
    recording = False
    process()


def on_quit() -> None:
    speak("Jarvis going offline. Goodbye.")


def audio_callback(indata, frame_count, time_info, status) -> None:
    if recording:
        frames.append(indata.copy())


# ─── Dry-run check (no mic, no model load) ────────────────────────────────────

def check() -> int:
    """Report the backends selected for this environment without opening audio."""
    print(f"\n🔎 Jarvis --check  (platform: {platform.system()})\n")
    ok = True

    try:
        backend = tts.select_tts_backend(
            config.VOICE, override=config.TTS_BACKEND, output_device=config.AUDIO_OUTPUT
        )
        print(f"   TTS backend : {backend.name}")
    except tts.TTSError as e:
        ok = False
        print(f"   TTS backend : UNAVAILABLE — {e}")

    try:
        trigger = input_trigger.select_input_trigger(
            config.INPUT_MODE, start_recording, stop_recording, on_quit
        )
        print(f"   Input mode  : {trigger.name}")
    except input_trigger.InputError as e:
        ok = False
        print(f"   Input mode  : UNAVAILABLE — {e}")

    try:
        backend = llm.select_llm_backend(config.LLM_BACKEND)
        status = "ready" if backend.available() else "NOT reachable now"
        print(f"   LLM backend : {backend.name} ({status})")
    except llm.LLMError as e:
        ok = False
        print(f"   LLM backend : UNAVAILABLE — {e}")

    print(f"   Claude model: {config.CLAUDE_MODEL}")
    print(f"   Whisper     : {config.WHISPER_MODEL}")
    print(f"\n   {'✅ All selected backends instantiated.' if ok else '❌ One or more backends unavailable.'}\n")
    return 0 if ok else 1


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    global whisper_model, llm_backend, tts_backend, session_id, system_prompt

    print("\n⚡ Jarvis Phase 1 starting up...")
    print("   Loading Whisper model (first run downloads the model — be patient)...")

    try:
        whisper_model = WhisperModel(
            config.WHISPER_MODEL, device="cpu", compute_type="int8"
        )
    except Exception as e:
        print(f"\n❌ Failed to load Whisper: {e}")
        print("   Run: pip install faster-whisper")
        return 1

    try:
        llm_backend = llm.select_llm_backend(config.LLM_BACKEND)
        if not llm_backend.available():
            print(f"\n❌ No usable LLM backend ({llm_backend.name}).")
            print("   Set ANTHROPIC_API_KEY, or run Ollama and set "
                  "JARVIS_LLM_BACKEND=ollama.")
            return 1
        print(f"   LLM backend: {llm_backend.name}")
    except llm.LLMError as e:
        print(f"\n❌ LLM unavailable: {e}")
        return 1

    try:
        tts_backend = tts.select_tts_backend(
            config.VOICE, override=config.TTS_BACKEND, output_device=config.AUDIO_OUTPUT
        )
        print(f"   TTS backend: {tts_backend.name}")
    except tts.TTSError as e:
        print(f"\n❌ TTS unavailable: {e}")
        return 1

    try:
        trigger = input_trigger.select_input_trigger(
            config.INPUT_MODE,
            start_recording,
            stop_recording,
            on_quit,
            process_utterance=handle_utterance,
            wake_config={
                "engine": config.WAKE_ENGINE,
                "access_key": config.PORCUPINE_KEY,
                "keyword": config.WAKE_KEYWORD,
                "oww_model": config.OWW_MODEL,
                "oww_threshold": config.OWW_THRESHOLD,
                "device": config.AUDIO_DEVICE,
                "channels": config.AUDIO_CHANNELS,
                "silence_threshold": config.VAD_SILENCE,
                "silence_ms": config.VAD_SILENCE_MS,
                "max_utterance_s": config.MAX_UTTERANCE_S,
            },
        )
        print(f"   Input mode: {trigger.name}")
    except input_trigger.InputError as e:
        print(f"\n❌ Input mode unavailable: {e}")
        return 1

    # Open a memory session and fold any recalled history into the system prompt.
    session_id = memory.start_session()
    system_prompt = build_system_prompt()
    print(f"   Memory session #{session_id} started.")

    print("\n✅ Ready.\n")
    if trigger.name == "wake_word":
        print(f'   Say "{config.WAKE_KEYWORD}" → ask your question → it answers')
        print("   Ctrl+C to quit\n")
    else:
        print("   Hold SPACE → talk → release to get a response")
        print("   ESC to quit\n")
    print("─" * 50)

    speak("Jarvis online. I'm ready when you are.")

    # Audio-managing triggers (wake_word) open their own stream; push_to_talk
    # relies on this shared stream + audio_callback.
    if trigger.manages_audio:
        trigger.run()
    else:
        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=audio_callback,
        ):
            trigger.run()

    # ─── Shutdown ─────────────────────────────────────────────────────────────
    # Reached after the trigger returns (ESC for push_to_talk, Ctrl+C for
    # wake_word). Close the session and push memory to the cloud — both are
    # best-effort and must not crash on the way out.
    print("\n   Shutting down...")
    try:
        memory.close_session(session_id)
    except Exception as e:
        print(f"   (warning: could not close memory session: {e})")

    try:
        aws_sync.sync_to_dynamodb()
    except Exception as e:
        print(f"   (warning: cloud sync skipped: {e})")

    print("   Goodbye.\n")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--doctor" in args:
        import doctor
        sys.exit(doctor.run())
    if "--check" in args:
        sys.exit(check())
    sys.exit(main())
