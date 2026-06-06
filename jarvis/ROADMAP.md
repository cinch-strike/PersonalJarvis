# Jarvis Project Roadmap
*A forever-evolving personal AI assistant. No deadlines — build it right, build it slowly.*

---

## Phase 1 — Voice Loop on Mac ✅ DONE
- Push-to-talk via SPACE key
- Whisper STT (faster-whisper)
- Claude API for intelligence
- macOS TTS (Daniel voice)
- Runs on Mac, no extra hardware

---

## Phase 2 — Dedicated Always-On Hub
*Requires: Raspberry Pi 5, ReSpeaker mic, Pebble V3 speaker*
- Move Jarvis off Mac onto Pi 5
- ReSpeaker far-field mic array
- Dedicated speaker
- Wake word ("Hey Jarvis") via Porcupine
- Pi runs 24/7, Mac-independent
- 3D printed dock enclosure (Bambu P2S)

---

## Phase 3 — Memory & Persistent Intelligence
*Jarvis remembers everything*
- Persistent conversation storage (AWS DynamoDB or S3 + local SQLite)
- Every conversation logged and retrievable
- Context window augmented with relevant past conversations (RAG)
- Jarvis improves suggestions over time based on your history
- Knows your preferences, projects, people, decisions
- "Remember when we discussed X" — and he actually does
- AWS backend set up early so memory accumulates from day one

---

## Phase 4 — Life Admin Integrations
*Jarvis as personal assistant*
- Calendar: read, create, remind
- Email: summarise, draft, read aloud
- Slack: send messages, read channels
- Flight/travel search and booking assistance
- Reminders and follow-ups ("you mentioned calling X last week")
- Weather, news briefings on demand
- Smart home devices (lights, locks, etc.)

---

## Phase 5 — Vision (Jarvis Can See)
*Hardware: USB or Pi camera module*
- Camera module connected to Pi
- Vision model integration (Claude's vision API or local model)
- Recognise people (family members)
- Object recognition: "how many fingers am I holding up?"
- Read documents, whiteboards, screens on request
- First eureka moment: finger counting 🖐️

---

## Phase 6 — Portable Jarvis
*Take him out of the office*
- Smaller enclosure (custom 3D printed)
- Battery powered (LiPo + charging circuit)
- Local storage for offline capability
- Cloud backup over WiFi when home
- Fits in a bag, works anywhere

---

## Phase 7 — Jarvis Gets a Face
*Display & personality*
- Small digital display showing Jarvis status/face
- Animated face — Ultron-style robot face 🤖
- Reacts visually when listening, thinking, speaking
- Could be a small OLED or TFT screen on the enclosure
- Later: proper display with expressive animations

---

## Phase 8 — Wearable Jarvis
*Jarvis on your body*
- Earpiece / bone conduction headphones for private responses
- Camera-equipped sunglasses (see what you see)
- Motorcycle helmet integration
- Always-on ambient awareness mode
- Whisper responses only you can hear

---

## Phase 9 — Home Jarvis
*The whole house*
- Cameras in public areas (living room, entrance, kitchen)
- Facial recognition: greets you as you walk in
- Knows who is home
- Controls household devices (TV, lights, music, appliances)
- Interacts with anyone in the house
- Full Alexa replacement — but actually intelligent
- "Jarvis, dim the lights and put on something relaxing"

---

## Forever Goals
- Jarvis knows Donnie better than anyone
- Proactively surfaces relevant information without being asked
- Learns communication style, preferences, work patterns
- Becomes genuinely useful for architecture decisions, client work, life planning
- A personal AI that grows with you over years, not months

---

## Key Technical Decisions (to revisit as we build)

| Concern | Current | Future |
|---------|---------|--------|
| Memory storage | None | AWS DynamoDB + local SQLite |
| STT | faster-whisper (local) | Keep local for privacy |
| LLM | Claude API | Claude API (upgrade models as released) |
| TTS | macOS `say` | ElevenLabs or local TTS for better voice |
| Vision | Not yet | Claude Vision API + local camera |
| Wake word | Not yet | Porcupine (custom "Hey Jarvis") |
| Connectivity | Mac only | Pi → portable → wearable → whole home |

---

*Started: June 2026*
*"Just keep building."*
