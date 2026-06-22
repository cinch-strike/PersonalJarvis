# Jarvis Project — Hardware Checklist

Order in sequence. Phase 1 is software only — start ordering Stage 1 hardware while you build it.
Skeleton breadboard circuits first, 3D printed enclosure last.

---

## Stage 1 — Pi Hub  *(order first, arrives while you code Phase 1)*

**Where to buy: PB Tech — pbtech.co.nz**

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 1 | Raspberry Pi 5 (8GB) | The always-on Jarvis brain | $363.69 | [x] |
| 2 | Pi 5 Official 27W USB-C PSU | Must be official — Pi 5 is fussy about power | $24.90 | [x] |
| 3 | SanDisk Extreme 64GB microSDXC (A2, V30, U3) | A2 rating matters for OS responsiveness. 170MB/s read. | $67.85 | [x] |
| 4 | Pi 5 Active Cooler | Runs hot under Whisper load — not optional | $9.75 | [x] |

---

## Stage 2 — Microphone  *(order same time as Stage 1)*

**Where to buy: Element14 NZ — nz.element14.com**
(Search: Seeed Studio 107990053)

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 5 | ReSpeaker Mic Array v2.0 | 4-mic far-field array, beamforming, XMOS XVF-3000, plug-and-play USB. 12 RGB LEDs. | $129.06 | [x] |

---

## Stage 3 — Speaker & Cables  *(grab from Jaycar — they have NZ stores)*

**Where to buy: Jaycar NZ — jaycar.co.nz**

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 6 | Creative Pebble V3 speaker | USB-C powered, Bluetooth 5.0. Ordered via Ubuy NZ (incl. shipping). | $220.00 | [x] |
| 7 | USB-A to USB-A Cable 0.5m (5-pack) | ReSpeaker to Pi | $23.90 | [x] |
| 8 | USB-C to USB-C Cable 1m | Speaker to Pi | $29.90 | [x] |
| 9 | Cat6 Patch Cable 0.5m | Wired is more reliable than WiFi for Pi | $7.30 | [x] |

> Note: Jaycar is also great for breadboards, jumper wires, LEDs, and any other prototyping gear you want on the desk. Worth a browse while you're there.

---

## Stage 3.5 — Offline LLM Acceleration *(optional — for Phase 3.5)*

**Where to buy: PB Tech or Element14 NZ**

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 3.5a | Hailo-8L AI HAT+ for Pi 5 | M.2 HAT that adds dedicated AI inference chip. Dramatically faster than CPU-only Ollama on Pi. 13 TOPS. | ~$110–130 | [ ] |
| 3.5b | M.2 HAT+ (if not included) | Some bundles include, some don't — check what comes with Hailo | ~$15 | [ ] |

> Without the Hailo HAT, Ollama will still run on Pi 5 CPU but responses will be slow (10–30s for small models). The HAT makes it usable in real-time. Skip if budget is tight — can add later.

---

## Stage 4 — Prototyping Extras  *(optional but fun — breadboard era!)*

**Where to buy: Jaycar NZ or Element14 NZ**

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 10 | Full-size breadboard | For testing circuits before committing | ~$10 | [x] |
| 11 | Jumper wire kit (M-M, M-F, F-F) | Essential for breadboard prototyping | ~$12 | [ ] |
| 12 | LED assortment + 330Ω resistors | Status indicators — Jarvis needs a glow | ~$8 | [ ] |
| 13 | Small relay module (5V) | For any future power switching projects | ~$10 | [ ] |

---

## Stage 5 — 3D Printer  *(order last — after circuits are working)*

**Where to buy: Marvle3D NZ (Authorized Bambu Lab Distributor)**
228 Bush Road, Rosedale, Auckland
Phone: 022 696 8218 | marvle3d.co.nz | Mon–Sat 9:30–4:30

| # | Item | Notes | Est. Cost NZD | ✓ |
|---|------|-------|---------------|---|
| 14 | Bambu Lab P2S Combo (Starter Bundle) | Includes printer + AMS 2 Pro + 4 filament rolls. CoreXY, fully enclosed, multicolour. | ~$1,799* | [ ] |
| 15 | Extra PLA filament — 2x 1kg spools | Matte or standard. White/grey good for enclosures. | ~$66 | [ ] |

*Starter Bundle adds filament rolls — worth it over Machine Only for getting started immediately.

> Once the printer arrives, we'll spec the PAM8403 amp module + speaker drivers to build audio directly into the 3D printed Jarvis dock enclosure — replacing the standalone Pebble speaker.

---

## Cost Summary

| Stage | Items | Est. NZD |
|-------|-------|----------|
| Stage 1 — Pi Hub | 4 items | ~$180 |
| Stage 2 — Microphone | 1 item | ~$65 |
| Stage 3 — Speaker & Cables | 4 items | ~$79 |
| Stage 4 — Prototyping Extras | 4 items | ~$40 |
| Stage 5 — 3D Printer | 2 items | ~$1,865 |
| **Total** | **15 items** | **~$2,229** |

---

*Prices are estimates in NZD. Verify current pricing with each retailer before ordering.*
