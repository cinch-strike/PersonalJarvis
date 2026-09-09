"""
The Elena treasure hunt — scripted, stateless, and deliberately forgiving.
─────────────────────────────────────────────────────────────────────────
Three stages, each triggered by what a guest SAYS rather than by remembered
progress:

  1. "Vlad, who are you waiting for?"   → he tells Elena's story (spa pool)
  2. "we found the skull"               → he asks what is missing
  3. "the jaw"                          → he sends them to fetch it, and asks
                                          their name so the log records a winner

⚠️ STATELESS ON PURPOSE. Vlad cannot tell one guest from another — the sensor
re-arms between visitors and groups overlap all evening. Track "which stage is
this team on" and one group reaching stage two changes what the next group
hears. Because each stage has a distinct trigger, no memory is needed, and a
group that says a later phrase first simply gets that answer. They still have to
physically find the skull.

⚠️ SCRIPTED, NOT IMPROVISED. Quest replies bypass the LLM entirely and are
spoken verbatim. If the model paraphrased "a great box of hot water" as "a warm
bath", the puzzle would send a child to the wrong room and nobody would know
why. Bypassing is also faster, which matters with kids waiting.

⚠️ MATCHING IS FUZZY BY NECESSITY. This is Whisper tiny.en in a loud room. We
match on sets of common words, never on exact sentences and never on Elena's
name — possessives transcribe badly ("Elenas", "a Lena's", "Alaina's") and
requiring the name would add failure without adding security. Nobody reaches
stage two by accident.

Every string is configurable, so the wording can change up to the night without
touching code. See JARVIS_QUEST_* in HANDOFF.md.
"""

from __future__ import annotations

import os
import re
import time

QUEST_ENABLED = os.environ.get("JARVIS_QUEST_ENABLED", "false").lower() in (
    "1", "true", "yes", "on"
)

# Where winners are recorded. Separate from the conversation transcript so it
# can be read at a glance on the night: one line per event, newest at the end.
QUEST_LOG = os.path.expanduser(
    os.environ.get("JARVIS_QUEST_LOG", "~/quest_log.txt")
)

# The two magic words, said in this order, unlock Elena's story.
#
# ⚠️ CHOSEN FOR WHISPER, not for atmosphere. Both are two syllables, both are
# extremely common English, neither has a homophone, and nothing about them
# sounds alike — so a half-heard one cannot be mistaken for the other. Invented
# or Latin words are exactly what tiny.en destroys in a loud room ("Nosferatu"
# comes back as "nose for a two"). If these change, keep those properties.
WORD1 = os.environ.get("JARVIS_QUEST_WORD1", "winter").strip().lower()
WORD2 = os.environ.get("JARVIS_QUEST_WORD2", "roses").strip().lower()

# ⚠️ Must say TWO and must say WRITTEN. "If you could find them for me" reads to
# a child as "guess the magic words", and they will stand there guessing instead
# of going to look. Saying how many also stops someone who finds one word and
# gets no story from concluding they were wrong.
# Deliberately does NOT name locations: Vlad cannot know where the cards were
# hidden, and if he did the clue cards would be decoration.
FORGOTTEN = os.environ.get("JARVIS_QUEST_FORGOTTEN", (
    "Waiting? For six hundred years I have been waiting, and I cannot for the "
    "life of me remember what for. Her face is gone. Her name is gone. There "
    "were two words once — the ones she used to say — and I am told they are "
    "still written somewhere about this place. I cannot go and look. I have no "
    "legs. But you do."
))

# ⚠️ Same reasoning as WRONG_ORDER: a guest holding one word who gets silence
# concludes they were wrong and stops. Confirms without leaking the other word.
HALF_WAY = os.environ.get("JARVIS_QUEST_HALF_WAY", (
    "One of them. I feel it — something stirs, but I cannot see her yet. "
    "There is another word. Find it."
))

# ⚠️ Never answer a near-miss with silence. Someone who found both words and got
# nothing back has no way to know they were one swap away from solving it.
WRONG_ORDER = os.environ.get("JARVIS_QUEST_WRONG_ORDER", (
    "Close. Those are the words, but they do not fall in that order. "
    "Try them the other way about."
))

STORY = os.environ.get("JARVIS_QUEST_STORY", (
    "Her name was Elena, and she was always, always cold. Six centuries ago she "
    "told me she had found a great box of hot water out in the garden, and that "
    "she would warm her bones for just a moment. She never came back. If you are "
    "braver than I am, go and look."
))

FOUND = os.environ.get("JARVIS_QUEST_FOUND", (
    "Elena! After all this time. But look closely at her — something is missing, "
    "is it not? Tell me what."
))

JAW = os.environ.get("JARVIS_QUEST_JAW", (
    "Her jaw! She cannot speak a word to me without it. I saw something pale on "
    "the table in the middle of the room where everyone gathers. Bring me both — "
    "carry them to Donnie — and Elena and I shall be whole again. "
    "Now tell me your name, so that I may curse it kindly."
))

# How long after the jaw stage we treat the next thing said as a name. Expires
# so a visitor who wanders off does not cause the NEXT guest's first sentence to
# be filed as a winner.
NAME_WINDOW_S = float(os.environ.get("JARVIS_QUEST_NAME_WINDOW_S", "60"))

NAME_THANKS = os.environ.get("JARVIS_QUEST_NAME_THANKS", (
    "{name}. I shall remember it, which is more than I can say for most of the "
    "living. Go — fetch her jaw."
))

_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set:
    return set(_WORD.findall((text or "").lower()))


def _tokens(text: str) -> list:
    """Words in the order spoken — the set form cannot answer 'which came first'."""
    return _WORD.findall((text or "").lower())


def _count(text: str) -> int:
    return len(_WORD.findall((text or "").lower()))


# Each stage lists GROUPS of words. At least one word from every group must be
# present. That is deliberately loose: the card is cryptic, so guests improvise
# the question rather than reciting it, and "what are you waiting for" has to
# work as well as "who are you waiting for". Requiring exact words here would
# strand people who had already solved the puzzle.
STAGES = (
    {
        "name": "forgotten",
        "groups": ({"who", "whom", "what", "whos", "whats"},
                   {"waiting", "waits", "wait", "waited", "waitin",
                    "miss", "misses", "missing", "missed",
                    "lost", "lose", "loses", "losing"}),
        "max_words": None,
        "reply": lambda: FORGOTTEN,
    },
    {
        "name": "found",
        "groups": ({"skull"},
                   {"found", "find", "finded", "got", "have", "has",
                    "seen", "see", "saw", "theres", "there"}),
        "max_words": None,
        "reply": lambda: FOUND,
    },
    {
        # "jaw" is one short common word and Vlad will hear it in ordinary
        # chatter. Requiring a SHORT utterance keeps a rambling sentence that
        # happens to contain it from handing the answer to a group that has not
        # earned it.
        "name": "jaw",
        "groups": ({"jaw", "jaws", "jawbone", "teeth", "tooth", "mouth"},),
        "max_words": 6,
        "reply": lambda: JAW,
    },
)


def _log(event: str, detail: str = "") -> None:
    """Append one line to the quest log. Never raises — a logging failure must
    not stop the prop mid-conversation."""
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(QUEST_LOG, "a", encoding="utf-8") as f:
            f.write(f"{stamp}  {event}{('  ' + detail) if detail else ''}\n")
    except OSError:
        pass


class Quest:
    """Matches quest triggers against a transcript. One instance per run."""

    def __init__(self, enabled: bool = None):
        self.enabled = QUEST_ENABLED if enabled is None else enabled
        self._awaiting_name_until = 0.0

    def _awaiting_name(self) -> bool:
        return time.monotonic() < self._awaiting_name_until

    def check(self, text: str):
        """Scripted reply for this utterance, or None to let the LLM answer."""
        if not self.enabled or not (text or "").strip():
            return None

        # A name is only expected in the window right after the jaw stage.
        if self._awaiting_name():
            self._awaiting_name_until = 0.0
            name = text.strip().rstrip(".!?")
            _log("WINNER-NAME", name)
            return NAME_THANKS.format(name=name)

        # Magic words first: they are two fixed tokens, so they are both the most
        # reliable trigger and the one that must not be shadowed by a looser
        # stage matching the same sentence.
        toks = _tokens(text)
        has1, has2 = WORD1 in toks, WORD2 in toks
        if has1 and has2:
            if toks.index(WORD1) < toks.index(WORD2):
                _log("STAGE-WORDS", text.strip())
                return STORY
            _log("STAGE-WORDS-WRONG-ORDER", text.strip())
            return WRONG_ORDER
        if has1 or has2:
            # Only when the word is offered on its own. "It is cold like winter
            # in here" is chatter, not an attempt, and answering it would hand
            # a passer-by half the puzzle.
            if _count(text) <= 4:
                _log("STAGE-WORDS-HALF", text.strip())
                return HALF_WAY

        words = _words(text)
        for stage in STAGES:
            if not all(group & words for group in stage["groups"]):
                continue
            if stage["max_words"] and _count(text) > stage["max_words"]:
                continue
            _log(f"STAGE-{stage['name'].upper()}", text.strip())
            if stage["name"] == "jaw":
                self._awaiting_name_until = time.monotonic() + NAME_WINDOW_S
            return stage["reply"]()
        return None
