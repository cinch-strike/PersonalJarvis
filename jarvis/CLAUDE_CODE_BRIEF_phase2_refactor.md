# Claude Code Brief — Jarvis Phase 2 Prep: Platform Portability Refactor

Paste this whole file (or point Claude Code at it) to start the remote-friendly software work.

---

## Project context

Jarvis is a personal voice assistant. **Phase 1** is a working push-to-talk loop on macOS (`jarvis/phase1/`). The next milestone, **Phase 2**, moves Jarvis onto a Raspberry Pi 5 (Linux) with a ReSpeaker mic, a USB speaker, and a wake word. All Phase 2 hardware is now in hand but not yet set up.

**The problem this task solves:** the current code is macOS-only in two places, so it won't run on the Pi as-is:
- **TTS** is hardcoded to the macOS `say` command (`jarvis.py`, `speak()`, ~line 62).
- **Input** is hardcoded to a `pynput` SPACE-key push-to-talk listener.

This task makes the code **platform-portable without changing Phase 1 behaviour on the Mac.** No Pi or hardware is required to do or test this — it's pure software and fully doable remotely.

## Codebase (`jarvis/phase1/`)

- `jarvis.py` — main loop. Config block up top, then `speak()`, `transcribe()`, `ask_claude()`, `process()`, key handlers, startup/shutdown.
- `memory.py` — SQLite memory (sessions + turns). **Do not change.**
- `aws_sync.py` — pushes unsynced rows to DynamoDB on shutdown. **Do not change.**
- `requirements.txt` — faster-whisper, sounddevice, numpy, anthropic, pynput, boto3.

## Goals (in priority order)

1. **Abstract TTS behind an interface** with two backends selected automatically by OS:
   - macOS → existing `say -v <VOICE>` behaviour (unchanged).
   - Linux/Pi → `piper` (preferred, natural voice) with a fallback to `espeak-ng` if piper isn't installed.
   - Pick the backend at startup via `platform.system()`; allow an explicit override via a config/env var (`JARVIS_TTS_BACKEND`).
   - If the chosen backend binary is missing, fail with a clear, actionable message — don't crash cryptically.

2. **Abstract the input trigger** so the recording trigger is pluggable:
   - `push_to_talk` (current pynput SPACE behaviour) — keep as the default.
   - Leave a clean seam / stub for a future `wake_word` trigger (Porcupine, Phase 2) — interface only, no implementation yet.
   - Select via config/env var (`JARVIS_INPUT_MODE`), default `push_to_talk`.

3. **Move config to a single place.** Extract the config block into a small `config.py` (or a clearly-marked section) that reads env vars with sensible defaults, so the Mac vs Pi differences live in one spot. Keep `SYSTEM_PROMPT` and persona behaviour identical.

4. **Fix the stale model string.** `CLAUDE_MODEL` is currently `"claude-opus-4-6"`. Make it configurable via env var (`JARVIS_CLAUDE_MODEL`) with a current default — confirm the current model string with me before hardcoding one.

5. **Split requirements** so Linux-only deps (e.g. piper) aren't forced on Mac and vice versa — e.g. `requirements-common.txt` + `requirements-mac.txt` + `requirements-pi.txt`, or environment markers. Keep it simple.

## Hard constraints

- **Phase 1 on the Mac must behave exactly as before** — same push-to-talk UX, same Daniel voice, same memory/sync. This is a refactor, not a feature change.
- **Do not touch** `memory.py` or `aws_sync.py` logic.
- **Do not run `jarvis.py`** — it's an interactive mic/keyboard app and needs hardware + macOS accessibility permissions I'm not at the machine for. Verify your work with imports, unit tests, and a `--dry-run`/mockable path instead.
- Use `.venv/bin/python` and `.venv/bin/python -m pip` explicitly for all commands (avoids the pip/python env split we hit earlier).
- Keep everything in `jarvis/phase1/` for now; we'll promote to a shared module when Phase 2 lands.

## How to verify (no hardware)

- Add a small test or `--check` flag that imports everything and instantiates the selected TTS + input backends **without** opening the mic stream, and prints which backends were chosen for the current OS.
- Unit-test the backend-selection logic by mocking `platform.system()` for both `"Darwin"` and `"Linux"`.
- Run `.venv/bin/python -c 'import jarvis'`-style import checks (guard the `__main__` runtime so importing doesn't start the audio loop — you'll likely need to wrap the startup/loop in `if __name__ == "__main__":`).

## Deliverables

1. Refactored `jarvis.py` with TTS + input abstractions and a guarded `__main__`.
2. `config.py` (or equivalent) centralising env-var config.
3. Split requirements files.
4. Tests for backend selection + a `--check` dry-run path.
5. A short note in `HANDOFF.md` describing the new env vars and how to pick backends.

Start with #1 (TTS abstraction) since it's the smallest self-contained piece, show me the diff, and we'll iterate from there.
