"""
Call-out lines for the motion-triggered skull.
──────────────────────────────────────────────
A fixed list gets repetitive fast at a busy party, but generating a line the
moment someone walks up would add an obvious pause before the prop speaks. So
we spend one API call at startup and rotate through the results all session.

Kept out of jarvis.py deliberately: this is pure text handling, so it stays
importable — and testable — without numpy, sounddevice or Whisper.
"""

from __future__ import annotations

import config

PROMPT = (
    "Write {count} different opening lines to call out to a guest who has just "
    "walked up to you, in character. Vary them: some teasing, some ominous, "
    "some mock-prophetic, some curious. Each must be ONE short sentence that "
    "works spoken aloud at a noisy party. Output ONLY the lines, one per line, "
    "with no numbering, quotes, stage directions or commentary."
)

MIN_USABLE = 4      # below this the LLM clearly misunderstood; use defaults
MAX_LINE_LEN = 160  # anything longer doesn't work shouted across a driveway


def parse(reply: str) -> list:
    """Pull clean one-per-line barkers out of a raw LLM reply."""
    lines, seen = [], set()
    for raw in (reply or "").splitlines():
        line = raw.strip().lstrip("0123456789.-–—•) ").strip().strip('"').strip()
        # Drop empties, headers, and anything too long to work as a call-out.
        if not line or len(line) > MAX_LINE_LEN or line.endswith(":"):
            continue
        if line.lower() not in seen:
            seen.add(line.lower())
            lines.append(line)
    return lines


def build(llm_backend) -> list:
    """Fresh call-out lines for this run, written by the LLM in character.

    Falls back to the configured lines on any failure — the prop must still
    start with no network.
    """
    if not config.BARKER_GENERATE:
        return config.BARKER_LINES
    try:
        reply = llm_backend.generate(
            system=config.SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": PROMPT.format(count=config.BARKER_COUNT)}],
            max_tokens=900,
        )
    except Exception as e:  # noqa: BLE001 — never block startup on this
        print(f"   (barker generation failed: {e}; using default lines)")
        return config.BARKER_LINES

    lines = parse(reply)
    if len(lines) < MIN_USABLE:
        print("   (barker generation gave too few usable lines; using defaults)")
        return config.BARKER_LINES
    return lines
