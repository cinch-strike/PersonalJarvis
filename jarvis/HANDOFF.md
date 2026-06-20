# Jarvis — Project Handoff & Context

*Read this at the start of any new Cowork or Claude Code session to get up to speed instantly.*

---

## What Is This?

Jarvis is Donnie's personal AI voice assistant, inspired by Iron Man. Built in phases — starting simple on Mac, evolving to always-on Pi hub, then portable, wearable, and whole-home.

**GitHub:** https://github.com/cinch-strike/PersonalJarvis.git  
**Owner:** Donnie Banez — donnie@cinch-strike.io  
**Working style:** Cowork for planning/architecture, Claude Code in VS Code for coding

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Push-to-talk voice loop on Mac | ✅ Done |
| 2 | Always-on Raspberry Pi hub | ⏳ Hardware arrived — not yet set up |
| 3 | Persistent memory (SQLite + DynamoDB) | ✅ Done — not yet end-to-end tested |
| 3.5 | Offline/local LLM via Ollama | 📋 Planned |
| 4+ | Life admin, vision, portable, wearable, home | 📋 Planned — see ROADMAP.md |

---

## Codebase — `jarvis/phase1/`

| File | Purpose |
|------|---------|
| `jarvis.py` | Main voice loop. Hold SPACE to record, ESC to quit. |
| `memory.py` | SQLite memory module. Stores sessions + conversation turns. |
| `aws_sync.py` | Pushes unsynced SQLite rows to DynamoDB on shutdown. Fails gracefully. |
| `requirements.txt` | faster-whisper, sounddevice, numpy, anthropic, pynput, boto3 |

### Key config in `jarvis.py`
- `WHISPER_MODEL = "base"` — local STT, no internet needed
- `VOICE = "Daniel"` — macOS TTS voice
- `CLAUDE_MODEL = "claude-opus-4-6"` — upgrade as new models release
- Python **3.11** only — 3.14 has compatibility issues with faster-whisper

### Running Jarvis
```bash
cd jarvis/phase1
source .venv/bin/activate
python3 jarvis.py
```

---

## AWS Setup

| Setting | Value |
|---------|-------|
| DynamoDB table | `jarvis-memory` |
| Region | `ap-southeast-2` (Sydney) |
| AWS profile | `jarvis` |
| IAM user | `jarvis-local` |
| IAM policy | `JarvisMemoryPolicy` (scoped to jarvis-memory table only) |
| AWS account | 336094385396 (cs-nexus-admin) |

**On a new machine:** run `aws configure --profile jarvis` and enter the `jarvis-local` access key + secret. Region: `ap-southeast-2`, output: `json`.

The `jarvis-local` IAM access keys were generated during setup — Donnie has them saved. If lost, generate new ones: AWS Console → IAM → Users → jarvis-local → Security credentials → Create access key.

---

## Hardware Status

| Item | Status |
|------|--------|
| Raspberry Pi 5 8GB | ✅ Arrived |
| Pi 5 Active Cooler | ✅ Arrived |
| SanDisk 64GB microSD | ✅ Arrived |
| ReSpeaker Mic Array v2.0 | ✅ Arrived |
| Creative Pebble V3 Speaker | ✅ Arrived |
| Pi 5 Official 27W USB-C PSU | ❓ Confirm with Donnie |
| USB cables + Cat6 | ❓ Confirm with Donnie |
| Hailo-8L AI HAT+ (optional) | Not yet ordered — for Phase 3.5 offline LLM |
| Bambu Lab P2S Combo 3D Printer | Not yet ordered |

---

## What's Next (immediate)

1. **End-to-end test on personal Mac** — run `python3 jarvis.py`, have a conversation, ESC, verify DynamoDB has the turns
2. **Set up Pi** — flash microSD with Raspberry Pi OS, configure, clone repo, install deps
3. **Phase 2** — move Jarvis off Mac onto Pi with ReSpeaker + speaker + wake word
4. **Phase 3.5** — install Ollama on Pi, wire up Claude-online / Ollama-offline fallback

---

## Conventions & Notes

- Never paste API keys or AWS secrets in chat — terminal only
- `.venv/` is gitignored — recreate on each machine with `python3.11 -m venv .venv`
- `jarvis_memory.db` is gitignored — local SQLite file, not committed
- Whisper model downloads on first run (~150MB for "base") — normal to appear frozen
- macOS accessibility permission required for pynput keyboard listener
- Donnie is in New Zealand — use NZD for hardware, ap-southeast-2 for AWS

---

*Last updated: June 2026*
