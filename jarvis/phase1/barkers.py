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

FLUSH_PROMPT = (
    "You are mounted in a bathroom at a Halloween party and a guest has just "
    "flushed the toilet. Write {count} different one-line reactions, in "
    "character. Rude enough to be funny, clean enough for someone's parents to "
    "hear — cheeky, not crude. Vary them: some mock-offended, some approving, "
    "some ominous. Each must be ONE short sentence that works spoken aloud. "
    "Output ONLY the lines, one per line, with no numbering, quotes, stage "
    "directions or commentary."
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


def _generate(llm_backend, prompt: str, fallback: list, label: str) -> list:
    """Ask the LLM for a batch of in-character lines, or fall back quietly.

    Shared by every line type: the prop must still start with no network, so
    every failure path returns the configured defaults rather than raising.
    """
    try:
        reply = llm_backend.generate(
            system=config.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
        )
    except Exception as e:  # noqa: BLE001 — never block startup on this
        print(f"   ({label} generation failed: {e}; using default lines)")
        return fallback

    lines = parse(reply)
    if len(lines) < MIN_USABLE:
        print(f"   ({label} generation gave too few usable lines; using defaults)")
        return fallback
    return lines


def build(llm_backend) -> list:
    """Fresh call-out lines for this run, written by the LLM in character."""
    if not config.BARKER_GENERATE:
        return config.BARKER_LINES
    return _generate(
        llm_backend,
        PROMPT.format(count=config.BARKER_COUNT),
        config.BARKER_LINES,
        "barker",
    )


def build_flush_lines(llm_backend) -> list:
    """Comebacks for when the toilet flushes."""
    if not config.FLUSH_GENERATE:
        return config.FLUSH_LINES
    return _generate(
        llm_backend,
        FLUSH_PROMPT.format(count=config.FLUSH_COUNT),
        config.FLUSH_LINES,
        "flush line",
    )
