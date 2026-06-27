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
| 2 | Always-on Raspberry Pi hub | 🟢 Running on the Pi: wake word ("hey jarvis", openWakeWord 0.4.0) → Whisper → Claude → **natural piper voice (alan)** out the Pebble. Audio in/out both working. Remaining polish: transcription tuning + 24/7 autostart. |
| 3 | Persistent memory (SQLite + DynamoDB) | ✅ Done — unit-tested; live DynamoDB write verified from the Pi (`put-item`) |
| 3.5 | Offline/local LLM via Ollama | 🔧 Software ready (llm.py: claude/ollama/auto). Pi confirms `auto` reachable. Ollama not yet installed on Pi |
| 4+ | Life admin, vision, portable, wearable, home | 📋 Planned — see ROADMAP.md |

---

## Codebase — `jarvis/phase1/`

| File | Purpose |
|------|---------|
| `jarvis.py` | Main voice loop. Hold SPACE to record, ESC to quit. Guarded `__main__` (safe to import). Flags: `--check`, `--doctor`. |
| `config.py` | **All config in one place**, read from env vars with Mac-default fallbacks. |
| `tts.py` | TTS abstraction: macOS `say` / Linux `piper` (→ `espeak-ng` fallback). |
| `input_trigger.py` | Recording-trigger abstraction: `push_to_talk` (pynput) + `wake_word` (Porcupine + silence detection). |
| `llm.py` | LLM abstraction: `claude` (online) / `ollama` (offline) / `auto` fallback. |
| `doctor.py` | Read-only environment readiness probe (`jarvis.py --doctor`). |
| `memory.py` | SQLite memory module. Stores sessions + conversation turns. *(unchanged)* |
| `aws_sync.py` | Pushes unsynced SQLite rows to DynamoDB on shutdown. *(unchanged)* |
| `requirements-common.txt` | Cross-platform deps (faster-whisper, sounddevice, numpy, anthropic, boto3). |
| `requirements-mac.txt` | Mac extras (pynput); `say` is built in. `requirements.txt` aliases this. |
| `requirements-pi.txt` | Pi/Linux notes (apt: espeak-ng, alsa-utils, piper). |
| `test_backends.py` | Unit tests for TTS/input/LLM selection + doctor (mocks `platform.system()`). |
| `test_memory.py` | Unit tests for SQLite memory (temp-DB round-trips). |
| `test_aws_sync.py` | Unit tests for DynamoDB sync (faked table; graceful-failure contract). |

### Platform portability (Phase 2 prep)
TTS and the recording trigger are chosen at startup by OS, overridable via env.
Mac defaults reproduce Phase 1 exactly. Configure via these env vars (all optional):

| Env var | Default | Purpose |
|---------|---------|---------|
| `JARVIS_TTS_BACKEND` | auto (Darwin→`say`, Linux→`piper`/`espeak`) | Force a TTS backend: `say` \| `piper` \| `espeak` |
| `JARVIS_INPUT_MODE` | `push_to_talk` | Recording trigger: `push_to_talk` (Mac) \| `wake_word` (Pi) |
| `JARVIS_WAKE_ENGINE` | `auto` | `auto` (Porcupine if key set, else openWakeWord) \| `porcupine` \| `openwakeword` |
| `JARVIS_OWW_MODEL` | `hey_jarvis` | openWakeWord model (keyless engine) |
| `JARVIS_OWW_THRESHOLD` | `0.5` | openWakeWord detection threshold (0–1); raise to reduce false wakes |
| `JARVIS_PORCUPINE_KEY` | — | Picovoice key (Porcupine only — now needs commercial approval) |
| `JARVIS_WAKE_KEYWORD` | `jarvis` | Porcupine built-in keyword |
| `JARVIS_AUDIO_DEVICE` | system default | sounddevice input device (index or name) — set to the ReSpeaker if needed |
| `JARVIS_AUDIO_CHANNELS` | `1` | Capture channels (ReSpeaker = 6; ch0 used) |
| `JARVIS_AUDIO_OUTPUT` | system default | ALSA playback device for TTS, e.g. `plughw:3,0` (Pebble). `espeak`'s default output isn't the Pebble, so set this on the Pi |
| `JARVIS_VAD_SILENCE` | `500` | RMS below this = silence. Lower if it cuts you off; raise if it never stops |
| `JARVIS_VAD_SILENCE_MS` | `1000` | Trailing silence (ms) that ends a question |
| `JARVIS_MAX_UTTERANCE_S` | `15` | Hard cap per question (s) |
| `JARVIS_CLAUDE_MODEL` | `claude-opus-4-8` | Claude model id |
| `JARVIS_VOICE` | `Daniel` | macOS `say` voice |
| `JARVIS_WHISPER_MODEL` | `base` | Whisper model size |
| `JARVIS_SAMPLE_RATE` | `16000` | Mic sample rate (Hz) |
| `JARVIS_PIPER_MODEL` | — | Path to piper `.onnx` voice (Linux/piper only) |
| `JARVIS_PIPER_RATE` | `22050` | piper playback sample rate |
| `JARVIS_LLM_BACKEND` | `auto` | LLM: `auto` (Claude→Ollama fallback) \| `claude` \| `ollama` |
| `JARVIS_OLLAMA_MODEL` | `llama3.1` | Ollama model tag (offline) |
| `JARVIS_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `JARVIS_MAX_TOKENS` | `600` | Max tokens per reply |

**On the Pi:** `sudo apt install espeak-ng alsa-utils`, install the piper binary +
a voice model, then `export JARVIS_PIPER_MODEL=/path/to/voice.onnx`. If piper or its
model is missing, Jarvis auto-falls back to `espeak-ng`. For the Pi, set
`JARVIS_INPUT_MODE=wake_word` (keyless via `openwakeword` by default) — see
"What's Next" for the run steps.

- Python **3.11–3.13** work (Pi confirmed on 3.13.5 with faster-whisper 1.2.1) — avoid **3.14+** (faster-whisper issues)

### Running Jarvis
```bash
cd jarvis/phase1
source .venv/bin/activate
python3 jarvis.py            # run normally
python3 jarvis.py --check    # print selected backends, no mic/model — verify a new box
python3 jarvis.py --doctor   # full readiness probe: Python, backends, API key, SQLite, AWS
python3 -m unittest discover -p 'test_*.py'   # full test suite (backends, memory, sync, doctor)
```

### Repo tooling (added this session)
- **Root `README.md`** — project overview, portability matrix, quickstart.
- **Root `Makefile`** — `make doctor | check | test | run | install | clean` (run from repo root).
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — runs the full 44-test suite on every push/PR to `main`. Currently green.
- All tests are pure software (no mic/model/AWS needed) so they run anywhere.

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

> **Policy is `PutItem`-only by design** — `ListTables`/`DescribeTable`/reads are denied. Jarvis only writes (`PutItem`), so that's all the policy grants. Verify connectivity with a real `put-item`, **not** `list-tables` (which will fail with AccessDenied). `jarvis.py --doctor` knows this — it checks that credentials resolve and does **not** probe the table. A harmless test row sits at `session_id=0` in `jarvis-memory` from the Pi connectivity test.

---

## Hardware Status

| Item | Status |
|------|--------|
| Raspberry Pi 5 8GB | ✅ Arrived |
| Pi 5 Active Cooler | ✅ Arrived |
| SanDisk 64GB microSD | ✅ Arrived |
| ReSpeaker Mic Array v2.0 | ✅ Arrived |
| Creative Pebble V3 Speaker | ✅ Arrived |
| Pi 5 Official 27W USB-C PSU | ✅ Arrived |
| USB cables + Cat6 | ✅ Arrived (but all USB cables tried are **charge-only** — see below) |
| USB-A→Micro-B **data** cable (Vention CTIBH, PB Tech VNT1231) | 🛒 Ordered — needed to connect the ReSpeaker |
| Jackson PT1055 10-outlet surge powerboard | 🛒 Ordered — proper Pi power |
| Hailo-8L AI HAT+ (optional) | Not yet ordered — for Phase 3.5 offline LLM |
| Bambu Lab P2S Combo 3D Printer | Not yet ordered |

---

## Pi Bring-Up Status (Day 1) — see `PI_SETUP_DAY1.md` for the full guide

**8 of 9 steps done.** The Pi (`jarvis@jarvis.local`, on WiFi for now) has a known-good base: OS flashed, SSH, updated, deps, code cloned, venv, credentials. Confirmed:
- **Python 3.13.5** — faster-whisper 1.2.1 imports fine (`core ok`). The old "3.11 only" worry is moot.
- **AWS** — verified by a real `put-item` write to `jarvis-memory` (the policy denies list/describe by design).
- **`jarvis.py --doctor` on the Pi: all green** — Python ✅, TTS `espeak` ✅, input `push_to_talk` ✅, LLM `auto(claude→ollama)` reachable ✅, Anthropic key ✅, SQLite ✅, AWS ✅.

**🟨 Blocked: Step 5 (audio).** Every USB cable on hand is charge-only (nothing in `dmesg`/`lsusb` when the ReSpeaker is plugged in). A real **USB-A→Micro-B data cable** is ordered (Vention CTIBH). When it arrives: plug in → `lsusb` (XMOS/Seeed should appear) → `arecord -l` → record/playback test. That also doubles as the final ReSpeaker board check. The ReSpeaker board is **unconfirmed** until then.
> Note: `--doctor` green ≠ audio proven. Doctor checks backend *selection*, not actual mic capture / speaker playback — that's the blocked Step 5.

---

## What's Next (immediate)

**First talking Jarvis on the Pi — wake-word run (keyless openWakeWord):**
> Porcupine's free key now requires Picovoice *commercial-use approval* (Donnie hit this gate), so the default engine is **openWakeWord** — no account, no key, offline.
```bash
cd ~/PersonalJarvis && git pull
cd jarvis/phase1
.venv/bin/python -m pip install openwakeword
export JARVIS_INPUT_MODE=wake_word
export JARVIS_AUDIO_DEVICE=0        # ReSpeaker 4 Mic Array (confirmed via query_devices)
export JARVIS_AUDIO_CHANNELS=6      # ReSpeaker exposes 6ch; ch0 (processed) is used
.venv/bin/python jarvis.py --doctor   # expect Wake word ✅ (openWakeWord ready)
.venv/bin/python jarvis.py            # say "hey jarvis", ask, it answers. Ctrl+C to quit.
```
> **openWakeWord version reality:** on the Pi's Python 3.13, pip installs **0.4.0** (newer needs `tflite-runtime`, which has no 3.13 wheel). 0.4.0 bundles its models (incl. `hey_jarvis`) — no download needed. The engine handles this automatically.

**Make the env vars permanent** (otherwise a new SSH session starts back in push_to_talk):
```bash
cat >> ~/.bashrc <<'EOF'
export JARVIS_INPUT_MODE=wake_word
export JARVIS_AUDIO_DEVICE=0          # ReSpeaker (capture)
export JARVIS_AUDIO_CHANNELS=6
export JARVIS_AUDIO_OUTPUT=plughw:3,0 # Pebble speaker (TTS playback)
EOF
source ~/.bashrc
```

**To resume in a new session:** `ssh jarvis@jarvis.local`, then `cd ~/PersonalJarvis/jarvis/phase1 && .venv/bin/python jarvis.py`.

**Status:** confirmed up to the `👂 Listening for "hey_jarvis"` state. **Not yet verified:** an actual "hey jarvis" + question round-trip (wake detection → Whisper → Claude → speak). That's the next test.

**Feedback loop (fixed):** early on, Jarvis heard its own voice from the Pebble and replied to itself. Fixed in `input_trigger.py` (mic stream is paused via `stream.stop()/start()` around transcribe/think/speak, then drained + detector reset) and `tts.py` (piper now waits for `aplay` to finish). If self-triggering ever recurs it's live acoustic echo — lower Pebble volume, move mic from speaker, or raise `JARVIS_OWW_THRESHOLD`.

**Tuning (once testing the live loop):**
- Wake word not triggering / too touchy → adjust `JARVIS_OWW_THRESHOLD` (lower = easier, more false wakes; default 0.5).
- Cuts you off mid-sentence → lower `JARVIS_VAD_SILENCE`; never stops → raise it.
- Wrong/quiet mic → confirm `JARVIS_AUDIO_DEVICE` index from `query_devices()`.
- The `onnxruntime ... GpuDevices / CUDAExecutionProvider` warnings are harmless (CPU inference).

**Then (optional, any order):**
- **Natural voice — DONE (piper + alan).** Installed on the Pi:
  - Binary: `~/piper/` (from rhasspy/piper `2023.11.14-2` `piper_linux_aarch64.tar.gz`).
  - Voice: `~/piper-voices/en_GB-alan-medium.onnx` (+ `.onnx.json`) — calm British male.
  - `~/.bashrc` sets `PATH=$HOME/piper:$PATH` + `JARVIS_PIPER_MODEL=…alan-medium.onnx`; Jarvis then auto-selects piper over espeak. Playback still via `JARVIS_AUDIO_OUTPUT=plughw:3,0`.
  - Swap voices: download another from rhasspy/piper-voices on HF and repoint `JARVIS_PIPER_MODEL`. (The macOS prebuilt piper binary is broken — missing dylibs — but Linux/Pi is fine.)
- **Phase 3.5 offline** — install Ollama (`ollama pull llama3.1`); `JARVIS_LLM_BACKEND` already supports auto-fallback.
- **Auto-start 24/7 (systemd)** — see `phase1/jarvis.service.example`. Setup:
  ```bash
  # 1. env file (captures your CURRENT shell vars, incl. the API key)
  mkdir -p ~/.config/jarvis
  cat > ~/.config/jarvis/jarvis.env <<EOF
  ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
  JARVIS_INPUT_MODE=wake_word
  JARVIS_AUDIO_DEVICE=0
  JARVIS_AUDIO_CHANNELS=6
  JARVIS_AUDIO_OUTPUT=plughw:3,0
  JARVIS_PIPER_MODEL=$JARVIS_PIPER_MODEL
  PATH=$HOME/piper:/usr/local/bin:/usr/bin:/bin
  EOF
  chmod 600 ~/.config/jarvis/jarvis.env
  # 2. install + enable the service
  sudo cp ~/PersonalJarvis/jarvis/phase1/jarvis.service.example /etc/systemd/system/jarvis.service
  sudo systemctl daemon-reload && sudo systemctl enable --now jarvis
  journalctl -u jarvis -f          # watch it boot
  ```
  Stop the manual `python jarvis.py` first (two instances would fight over the mic). Manage with `sudo systemctl {status,restart,stop} jarvis`.

> **Before running anything on the Pi:** `cd ~/PersonalJarvis && git pull`, then `cd jarvis/phase1 && .venv/bin/python jarvis.py --doctor`.

---

## Conventions & Notes

- Never paste API keys or AWS secrets in chat — terminal only
- `.venv/` is gitignored — recreate on each machine with `python3 -m venv .venv` (Python 3.11–3.13)
- `jarvis_memory.db` is gitignored — local SQLite file, not committed
- Whisper model downloads on first run (~150MB for "base") — normal to appear frozen
- macOS accessibility permission required for pynput keyboard listener
- Donnie is in New Zealand — use NZD for hardware, ap-southeast-2 for AWS

---

*Last updated: 22 June 2026 — Phase 2 software portability complete (TTS/input/LLM abstractions, `--doctor`, tests, CI); Pi base built 8/9, audio blocked on USB data cable.*
