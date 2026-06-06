# Jarvis Phase 1 — Setup Guide

## What this does
Push-to-talk voice loop on your Mac:
- Hold SPACE → speak → release
- Whisper transcribes your speech locally
- Claude responds
- macOS speaks the response back

No extra hardware needed — uses your Mac's built-in mic and speakers.

---

## Prerequisites

### 1. Homebrew packages
```bash
brew install ffmpeg portaudio
```
`ffmpeg` is required by Whisper. `portaudio` is required by sounddevice.

### 2. Python dependencies
```bash
cd jarvis/phase1
pip install -r requirements.txt
```

> If you get permission errors, add `--break-system-packages` or use a venv:
> ```bash
> python3 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
> ```

### 3. Anthropic API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
Add this to your `~/.zshrc` so it persists:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

### 4. Accessibility permission (required for global hotkey)
The SPACE hotkey works across all apps via macOS Accessibility API.

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your Terminal app (Terminal.app or iTerm2)
3. Toggle it ON

You'll be prompted automatically on first run if you haven't done this.

---

## Run it

```bash
python3 jarvis.py
```

First run will download the Whisper model (~150MB for "base"). This only happens once.

---

## Customisation

Open `jarvis.py` and edit the Config section at the top:

| Setting | Default | Options |
|---------|---------|---------|
| `WHISPER_MODEL` | `"base"` | `"tiny"` (fastest), `"base"`, `"small"` (most accurate on Mac) |
| `VOICE` | `"Alex"` | Run `say -v '?'` in Terminal to list all voices. Try `"Daniel"` for UK accent. |
| `SYSTEM_PROMPT` | Jarvis persona | Edit to change personality, add context about your projects, etc. |

---

## Troubleshooting

**"No module named whisper"** → Run `pip install openai-whisper`

**"ANTHROPIC_API_KEY not set"** → See step 3 above

**Space key not working in other apps** → Check Accessibility permission (step 4)

**Audio not recording** → Check System Settings → Privacy → Microphone → allow Terminal

**Whisper is slow** → Switch to `WHISPER_MODEL = "tiny"` for faster (less accurate) transcription

---

## What's next (Phase 2)
- Move to Raspberry Pi 5 as always-on hub
- Add ReSpeaker mic array for far-field pickup
- Add wake word ("Hey Jarvis") via Porcupine
- Dedicated speaker in 3D printed dock
