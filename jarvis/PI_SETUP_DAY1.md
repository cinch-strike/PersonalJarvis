# Jarvis — Pi Setup Day 1 Battle Plan (Beginner Edition)

**First time with a Raspberry Pi? This is written for you.** Every step says what to do, what you'll see, and what "good" looks like. You're on a **Mac**, so all the laptop-side steps are Mac-specific.

**Goal for the day:** get the Raspberry Pi to a *known-good base* — booted, on the network, updated, audio working, code downloaded, dependencies installed, credentials in place. You will **not** have a talking Jarvis today (that needs the wake-word software Claude Code is still building). Today you build the foundation it runs on.

### ▶️ WHEN THE DATA CABLE ARRIVES — finish Step 5 (≈5 min)
1. Reconnect to the Pi: `ssh jarvis@jarvis.local`
2. Plug ReSpeaker into the Pi with the **new Vention data cable** (USB-A → Micro-B).
3. Power the Pebble (USB-C) and run a 3.5mm cable from the **ReSpeaker's green jack** → Pebble aux. *(Pi 5 has no headphone jack — audio in AND out both go through the ReSpeaker, so this all needs the data cable.)*
4. Confirm the Pi sees it: `lsusb` (look for XMOS/Seeed) then `arecord -l`.
5. Record + play back:
   ```bash
   arecord -d 5 -f cd test.wav    # talk for 5s
   aplay test.wav                 # should hear it through the Pebble
   ```
6. If you hear your voice → Day 1 fully done. Note the mic card name (`arecord -l`) + output (`aplay -l`) and bring them to chat for the Phase 2 config. If `lsusb` *still* shows nothing with the new data cable → it's the ReSpeaker board (warranty/replace).

---

### Progress — 8 of 9 done 🟩🟩🟩🟩🟩🟨🟩🟩🟩
✅ 0 Lay out · ✅ 1 Cooler · ✅ 2 Flash SD · ✅ 3 Boot+SSH · ✅ 4 Update · 🟨 5 Audio (BLOCKED — cable ordered) · ✅ 6 Deps · ✅ 7 Code · ✅ 8 Credentials
> *Note: Pi runs Python 3.13.5 — faster-whisper 1.2.1 installed and imported fine, so the 3.11 concern is moot. `core ok` confirmed.*
> *AWS verified by a real `put-item` write to `jarvis-memory` (ListTables/DescribeTable are denied by design — the policy only grants PutItem, which is all Jarvis uses). Cloud memory path works from the Pi. A harmless test row sits at `session_id=0`.*

> **⚠️ Step 5 is paused — waiting on a USB-A → Micro-B *data* cable.** All cables tried so far are charge-only (confirmed: nothing appears in `sudo dmesg -w` when the ReSpeaker is plugged in, and `lsusb` shows only root hubs). The board and Pi are both fine. **Data cable ordered:** Vention CTIBH (PB Tech VNT1231, USB 2.0, 480Mbps). When it arrives: plug in → `lsusb` (XMOS/Seeed device should appear) → `arecord -l` → record/playback test. This also doubles as the final board check.
> **Also ordered:** Jackson PT1055 10-outlet surge powerboard (1m lead) — proper power for the Pi, ends the daisy-chained extension cords.
> **To check on audio-test day:** a 3.5mm male-to-male cable connects the ReSpeaker's green output jack → Pebble aux input (the Pebble V3 usually ships with one).

**A few things to know before you start:**
- A Raspberry Pi is a tiny computer. It has no screen or keyboard of its own — we'll control it *from your Mac* over the network. This is called running "headless." It's normal and easier than plugging in a monitor.
- "Flashing" the SD card just means copying the Pi's operating system onto it, the same way you'd install macOS — except we do it from your Mac onto the card.
- **SSH** is how you type commands on the Pi from your Mac's Terminal. Think of it as a remote-control text window into the Pi.
- Take your time on Step 5 (audio). It's the fiddliest part. Everything else is mostly waiting for downloads.

Tick the boxes as you go. If anything doesn't match what's described here, **stop, copy the exact text on screen, and bring it to chat** — don't push past an error.

---

## Visual guides (open these — they have photos)
Bookmark these on your Mac before you start. When a step below references one, open it to see exactly what it looks like.

- **Pi 5 — official getting started (photos of the board, ports, SD slot):** https://www.raspberrypi.com/documentation/computers/getting-started.html
- **Active Cooler — how it clips on + which header it plugs into (photos):** https://www.raspberrypi.com/documentation/accessories/active-cooler.html
- **Raspberry Pi Imager — the flashing app (screenshots of each screen):** https://www.raspberrypi.com/documentation/computers/getting-started.html#install-using-imager
- **ReSpeaker Mic Array v2.0 — official wiki (board photo, the 3.5mm jack, LED ring):** https://wiki.seeedstudio.com/ReSpeaker_Mic_Array_v2.0/

### Where everything plugs into the Pi (text map)
The Pi 5 ports, looking at the board with the USB ports on the **right**:

```
                ┌─────────────────────────────────────┐
   [microSD]    │                                     │
  (underside)   │   RASPBERRY PI 5                    │  ┌──────────┐ USB 3 (blue)
                │                                     │  │  ●  ●    │ ← ReSpeaker mic (USB-A→A)
   ┌────────┐   │   ┌────┐                            │  ├──────────┤
   │  FAN   │←──┼── │cool│ Active Cooler fan cable    │  │  ●  ●    │ USB 2
   │ 4-pin  │   │   │ er │                            │  └──────────┘
   └────────┘   │   └────┘                            │
                │                                     │  ┌──────────┐
  USB-C  ───────┼──→ ● Power (PSU) — plug in LAST     │  │ Ethernet │ ← Cat6 to router
  (power)       │                                     │  └──────────┘
                └─────────────────────────────────────┘

  Speaker (Pebble): USB-C → any USB port for power;
                    audio cable → green 3.5mm jack on the ReSpeaker board.
```

Plug-in order on first boot: **everything else first, then the PSU last** (the Pi powers on the instant it gets power).

---

## Step 0 — Lay everything out (5 min) ✅ DONE
- [x] Put these on the desk: the Pi 5 board, the Active Cooler, the microSD card, your card reader, the ReSpeaker (round microphone board), the Pebble speaker, the power supply (PSU), the USB cables, and the Cat6 (blue network) cable.
- [x] Have your Mac open. We'll use two Mac apps today: **Raspberry Pi Imager** (to flash the card) and **Terminal** (to control the Pi). *(Imager installed ✓)*

---

## Step 1 — Put the cooler on the Pi (10 min) ✅ DONE
The Pi 5 gets hot and will slow itself down without a cooler, so this goes on first.
📷 *Photos of this exact process:* https://www.raspberrypi.com/documentation/accessories/active-cooler.html

- [x] Find the **Active Cooler** (small black heatsink with a fan).
- [x] Look at the Pi board: near the USB-C power socket there's a small **white 4-pin connector** labelled "FAN" or "PWM."
- [x] The cooler has two spring-loaded plastic push-pins. Line them up with the two holes on the Pi and **press each pin straight down until it clicks.** Firm but not forced.
- [x] Plug the cooler's small white cable into that 4-pin FAN connector. It only fits one way.
- [x] **Do not insert the SD card or plug in power yet.** We flash the card first.

---

## Step 2 — Flash the SD card on your Mac (15 min) ✅ DONE
This copies the Pi's operating system onto the microSD card.

- [x] Put the microSD into your card reader, and plug the reader into your Mac. (If your reader is a full-size SD slot, the microSD goes into its SD adapter first.)
- [x] On your Mac, open a browser and go to **raspberrypi.com/software**. Click **Download for macOS**. Open the downloaded file and drag **Raspberry Pi Imager** into Applications, then open it. (If macOS warns it's from the internet, click **Open**.)
- [x] In Imager you'll see three buttons. Click them in order:
  - [x] **CHOOSE DEVICE** → select **Raspberry Pi 5**.
  - [x] **CHOOSE OS** → select **Raspberry Pi OS (64-bit)**. (It's usually the top "recommended" option.)
  - [x] **CHOOSE STORAGE** → select your microSD card. **Read the name and size carefully** — make sure it's the card, not your Mac's drive or a backup disk. Picking the wrong one erases it.
- [x] Click **NEXT**. It will ask **"Would you like to apply OS customisation settings?"** → click **EDIT SETTINGS**. This pre-configures the Pi so it works without a screen. Fill in:
  - [x] **Set hostname:** tick it, type `jarvis`  → this lets us reach the Pi at `jarvis.local` later.
  - [x] **Set username and password:** tick it. Pick a username (e.g. `donnie`) and a password. **Write both down** — you'll need them to log in.
  - [x] **Configure wireless LAN:** tick it, enter your WiFi name and password (backup to the cable). Set **Wireless LAN country** to **NZ**.
  - [x] **Set locale settings:** Time zone **Pacific/Auckland**, keyboard **US** (or your preference).
  - [x] Go to the **SERVICES** tab at the top → tick **Enable SSH** → choose **Use password authentication**.
  - [x] Click **SAVE**.
- [x] Back on the apply-settings prompt, click **YES**. If it asks to confirm erasing the card, click **YES** again.
- [x] Wait. It writes, then verifies — a few minutes. When it says **"You can now remove the SD card,"** you're done.
- [x] Eject the reader, take out the microSD, and put it into the **Pi** (the slot is on the underside, opposite the USB ports; it clicks in).

---

## Step 3 — First boot and connect from your Mac (10 min) ✅ DONE
> *Note for next time: the login username is `jarvis` (matches the hostname). Connect with `ssh jarvis@jarvis.local`.*

> **Network plan: WiFi now, wired later.** The router isn't at the work desk, and Step 5 (audio) needs the Pi within arm's reach so you can talk into the mic and hear the speaker. WiFi was configured during flashing, so the Pi joins wireless on boot — keep it on the desk and **skip the Cat6 today.** Switch to wired Ethernet later, once Jarvis's permanent always-on home is decided (wired is a touch more reliable for 24/7 running).

- [x] *(Skip today — wired later)* ~~Plug the Cat6 into the router.~~ The Pi uses WiFi for now.
- [x] Plug the **power supply** into the Pi's USB-C port and into the wall. The Pi turns on immediately — a green light blinks as it starts. It joins WiFi automatically. **The first boot takes 1–2 minutes; leave it alone.** *(Note: the SD card must be inserted first — flickering green = it's reading the card and booting.)*
- [x] On your Mac, open **Terminal** (press Cmd+Space, type "Terminal," hit Enter).
- [x] Type this and press Enter — **username is `jarvis`**:
  ```bash
  ssh jarvis@jarvis.local
  ```
- [x] The first time, it asks **"Are you sure you want to continue connecting?"** → type `yes` and Enter.
- [x] It asks for the password you set in Step 2. Type it (the screen shows nothing as you type — that's normal) and press Enter.
- [x] **Success looks like:** the prompt changes to something like `jarvis@jarvis:~ $`. You're now typing *on the Pi*. 🎉
- [x] **If `jarvis.local` doesn't work** (error like "could not resolve hostname"): open your router's admin page, find the device named `jarvis` in the connected-devices list, note its IP (e.g. `192.168.1.42`), and use that instead: `ssh jarvis@192.168.1.42`.

> From here on, every command goes in this SSH window — i.e. it runs on the Pi, not your Mac.

---

## Step 4 — Update the Pi (15 min, mostly waiting) ✅ DONE
This downloads the latest fixes. Copy-paste one block at a time, press Enter, wait for the prompt to come back before the next.

- [x] ```bash
  sudo apt update && sudo apt full-upgrade -y
  ```
  (It may ask for your password the first time you use `sudo`. Lots of text will scroll — that's normal. Wait for the `$` prompt to return.)
- [x] ```bash
  sudo rpi-eeprom-update -a
  ```
  (Updates the Pi's firmware. Reported a firmware update → reboot needed.)
- [x] ```bash
  sudo reboot
  ```
  This restarts the Pi and **kicks you out of SSH** (you'll see "connection closed" — that's expected). Wait ~1 minute, then reconnect: `ssh jarvis@jarvis.local` again. *(Fan spinning up during the update confirmed the cooler is wired correctly.)*

---

## Step 5 — Get audio working (20–30 min — go slow here)
This is the fiddliest part, so take it step by step. The **ReSpeaker** (round microphone board) is plug-and-play — no driver needed. We'll send sound *out* through the **Pebble speaker**.
📷 *ReSpeaker board photo — find the green 3.5mm jack and USB port:* https://wiki.seeedstudio.com/ReSpeaker_Mic_Array_v2.0/

- [ ] Plug the ReSpeaker into the Pi with the **USB-A → Micro-USB** cable (the ReSpeaker board has a small trapezoid Micro-USB port; USB-A end goes into the Pi).
- [ ] Plug the Pebble speaker in for power (**USB-C**). For the sound itself, the simplest path: connect the Pebble's audio cable to the **green 3.5mm headphone jack on the ReSpeaker board**. (We can switch to USB audio later if you prefer.)
- [ ] **See if the Pi found the microphone:**
  ```bash
  arecord -l
  ```
  You should see a line mentioning **ReSpeaker** or **ArrayUAC10**. Note the card name exactly as shown.
- [ ] **See the speaker / output:**
  ```bash
  aplay -l
  ```
  Note the output device listed.
- [ ] **Record a 5-second test** (talk into the mic after you press Enter; it stops itself after 5 seconds):
  ```bash
  arecord -d 5 -f cd test.wav
  ```
  (If that errors, we'll add the specific device name — bring me the `arecord -l` output.)
- [ ] **Play it back:**
  ```bash
  aplay test.wav
  ```
  You should hear your own voice through the Pebble. **If you do — the hardest part of the whole day is done.** 🎉
- [ ] Write down: the mic's card name from `arecord -l`, and the output device from `aplay -l`. We'll put these into Jarvis's config.

> No sound on playback? First check the Pebble's own volume knob and that it's powered on. If recording or playback errors, copy the exact message — this is the most common place to need a hand, and it's quick to fix once I see the device names.

---

## Step 6 — Install the building blocks Jarvis needs (10 min) ✅ DONE
These are background tools (audio plumbing, a basic voice for testing). Paste the whole block:
```bash
sudo apt install -y git python3-venv python3-dev ffmpeg \
  libportaudio2 portaudio19-dev espeak-ng awscli
```
Wait for the `$` prompt to return. (Lots of scrolling = normal.)

---

## Step 7 — Download the Jarvis code (15 min) ✅ DONE
- [x] Get the code onto the Pi (cloned straight away — public repo, no auth needed):
  ```bash
  cd ~
  git clone https://github.com/cinch-strike/PersonalJarvis.git
  cd PersonalJarvis/jarvis/phase1
  ```
- [~] Create an isolated Python environment and install Jarvis's libraries:
  ```bash
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip wheel
  .venv/bin/python -m pip install -r requirements.txt   # ← running now
  ```
  (The last line takes a few minutes and prints a lot — normal. Pulling from piwheels = pre-built Pi wheels.)
- [ ] **Check the core libraries loaded** (note: we do *not* run `jarvis.py` today — it needs the wake word that's still being built):
  ```bash
  .venv/bin/python -c 'import faster_whisper, sounddevice, anthropic, boto3; print("core ok")'
  ```
  **Good = it prints `core ok`.** If it prints an error instead, copy it and bring it to chat.

> **⚠️ Python version note:** this Pi runs **Python 3.13.5**, but the project was built for **3.11** (HANDOFF.md flags faster-whisper issues on newer Python). Watch the requirements install for faster-whisper errors. If it fails, the fix is to install Python 3.11 alongside (`pyenv` or the deadsnakes-equivalent) and recreate the venv with 3.11. Holding to see if 3.13 works first.

---

## Step 8 — Add your credentials (10 min) ✅ DONE
So Jarvis can reach the cloud memory (AWS) and Claude (Anthropic).

- [ ] AWS (same details you used on your Mac):
  ```bash
  aws configure --profile jarvis
  ```
  It asks four things, one per line:
  - **AWS Access Key ID:** paste the `jarvis-local` key
  - **AWS Secret Access Key:** paste the secret
  - **Default region name:** `ap-southeast-2`
  - **Default output format:** `json`
- [ ] Anthropic API key — add it so it's always available:
  ```bash
  echo 'export ANTHROPIC_API_KEY=PASTE_YOUR_KEY_HERE' >> ~/.bashrc
  source ~/.bashrc
  ```
  (Replace `PASTE_YOUR_KEY_HERE` with your real key.)
- [ ] **Test the cloud connection:**
  ```bash
  aws dynamodb list-tables --profile jarvis --region ap-southeast-2
  ```
  **Good = you see `jarvis-memory` in the output.** That proves the Pi can reach your cloud memory.

---

## Step 9 — Write down three things and you're done (5 min)
Bring these back to chat — they go straight into the Phase 2 setup:
- [ ] The Pi's address (the `jarvis.local` name, or the IP you used).
- [ ] The microphone card name (from `arecord -l`).
- [ ] The speaker output name (from `aplay -l`).

That's a full, healthy Pi base. 🎉

---

## What we are NOT doing today (on purpose)
- The wake word ("Hey Jarvis") — Claude Code is building it now.
- Running the full talking voice loop on the Pi — it needs that wake word plus the Linux voice, both still in progress.
- Making Jarvis auto-start 24/7 — we set that up once the loop runs.

## The three snags beginners hit most (and the fix)
1. **`jarvis.local` won't connect** → use the Pi's IP from your router instead (Step 3).
2. **Audio record/playback errors** → almost always just needs the exact device name from `arecord -l` / `aplay -l`. Send me those and I'll give you the precise command.
3. **An `import` error in Step 7** → usually means one `apt` package from Step 6 didn't install. Copy the error; it's a one-line fix.

Whenever you're unsure, the safe move is the same: **copy exactly what's on screen and bring it to chat.** Good luck — this is the fun part. ⚡
