# Jarvis

A personal AI voice assistant, built in phases — from a push-to-talk loop on a
Mac to an always-on, memory-keeping, offline-capable home hub.

[![CI](https://github.com/cinch-strike/PersonalJarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/cinch-strike/PersonalJarvis/actions/workflows/ci.yml)

> **New session / new machine?** Read [`jarvis/HANDOFF.md`](jarvis/HANDOFF.md)
> first — it's the living source of truth for status, config, and setup.

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Push-to-talk voice loop on Mac | ✅ Done |
| 2 | Always-on Raspberry Pi 5 hub + wake word | ⏳ Hardware in hand — software portability done |
| 3 | Persistent memory (SQLite + DynamoDB) | ✅ Done + unit-tested |
| 3.5 | Offline LLM via Ollama | 🔧 Software ready — needs Ollama on the Pi |
| 4+ | Life admin, vision, portable, wearable, home | 📋 Planned — see [ROADMAP](jarvis/ROADMAP.md) |

## How it works

Hold **SPACE** to record, release to process, **ESC** to quit. Audio is
transcribed locally with Whisper, answered by an LLM, and spoken back. Every
turn is saved to SQLite and synced to DynamoDB so memory survives across
machines.

The code is **platform-portable**: TTS, the recording trigger, and the LLM are
each chosen at startup by OS/env, so the same code runs on a Mac or a Pi.

| Concern | Mac default | Pi / alternative | Selected by |
|---------|-------------|------------------|-------------|
| TTS | macOS `say` | `piper` → `espeak-ng` | `JARVIS_TTS_BACKEND` |
| Input | `push_to_talk` (pynput) | `wake_word` (Phase 2 stub) | `JARVIS_INPUT_MODE` |
| LLM | Claude (cloud) | Ollama (offline) | `JARVIS_LLM_BACKEND` |

Full env-var reference is in [`jarvis/HANDOFF.md`](jarvis/HANDOFF.md).

## Layout

```
jarvis/
├── HANDOFF.md            # start here — status, config, setup
├── ROADMAP.md            # the long-term vision
├── PI_SETUP_DAY1.md      # beginner Raspberry Pi bring-up guide
└── phase1/
    ├── jarvis.py         # main loop (--check / --doctor flags)
    ├── config.py         # all env-var config in one place
    ├── tts.py            # TTS backends
    ├── input_trigger.py  # recording-trigger backends
    ├── llm.py            # LLM backends (claude/ollama/auto)
    ├── doctor.py         # environment readiness probe
    ├── memory.py         # SQLite sessions + turns
    ├── aws_sync.py       # DynamoDB sync (fails gracefully)
    └── test_*.py         # unit tests (no hardware needed)
```

## Quickstart (Mac)

```bash
cd jarvis/phase1
python3.11 -m venv .venv                       # Python 3.11 (3.14 breaks faster-whisper)
.venv/bin/python -m pip install -r requirements-common.txt -r requirements-mac.txt
export ANTHROPIC_API_KEY=sk-...                # required for Claude
.venv/bin/python jarvis.py --doctor            # verify environment, no mic needed
.venv/bin/python jarvis.py                      # run it
```

On a Raspberry Pi, swap the install line for `requirements-pi.txt` and see
[`jarvis/PI_SETUP_DAY1.md`](jarvis/PI_SETUP_DAY1.md).

## Common commands

From the repo root (uses the phase1 venv):

```bash
make doctor   # full environment readiness probe (no mic/model/LLM call)
make check    # print which backends are selected for this OS
make test     # run the full unit-test suite
make run      # start Jarvis
```

Or call the script directly: `python jarvis.py --doctor` / `--check`.

## Testing

Pure-software unit tests — no mic, model download, or AWS account required:

```bash
cd jarvis/phase1
python -m unittest discover -p 'test_*.py'
```

CI runs the same suite on every push (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
