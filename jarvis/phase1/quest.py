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
# Comma-separated: every form is accepted, the FIRST is the one Vlad echoes
# back. Bianca's clue asks guests to "name the bloom", singular, so they will
# say "rose" — accepting only "roses" would fail everyone who solved it.
def _forms(raw: str) -> list:
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


WORD1_FORMS = _forms(os.environ.get("JARVIS_QUEST_WORD1", "winter,wintertime"))
WORD2_FORMS = _forms(os.environ.get("JARVIS_QUEST_WORD2", "roses,rose"))
# ⚠️ These two are for DISPLAY only — what Vlad echoes back. Matching uses the
# _FORMS lists above. Change one without the other and the prop will recognise
# words it does not repeat, or repeat words it does not recognise.
WORD1 = WORD1_FORMS[0]
WORD2 = WORD2_FORMS[0]

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

# Words that mark an utterance as an ATTEMPT rather than chatter. Needed because
# length alone does not separate them: "okay I think I know the keyword it's
# winter" is nine words and is obviously a guess, while "we sat by the roses in
# the garden all afternoon" is nine words and obviously is not.
GUESS_MARKERS = {"word", "words", "keyword", "keywords", "magic", "spell",
                 "secret", "code", "password", "phrase", "say", "think", "guess"}

# How short an utterance can be and still count as offering a word bare.
BARE_MAX_WORDS = 5

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

# {word1} and {word2} are substituted from the config above, so the moment of
# recognition stays correct if the magic words ever change. A custom string
# without placeholders works fine — substitution is simply a no-op.
STORY = os.environ.get("JARVIS_QUEST_STORY", (
    "{word1} {word2}... {word1} {word2}. Yes. Yes, I can see her now, after all "
    "these years — thank you for that, truly. Her name was Elena, and she was "
    "always, always cold. Six centuries ago she told me she had found a great "
    "box of hot water out in the garden, and that she would warm her bones for "
    "just a moment. She never came back. If you are braver than I am, go and look."
))

FOUND = os.environ.get("JARVIS_QUEST_FOUND", (
    "Elena! After all this time. But look closely at her — something is missing, "
    "is it not? Tell me what."
))

# ⚠️ Deliberately does NOT name Donnie. Working out WHO is the last gate of the
# puzzle, and guests are meant to try several adults. Note "their hands", not
# "his" — a gendered pronoun would eliminate half the adults at the party and
# retire Bianca as a decoy in one word.
# ⚠️ The words must be spoken at the handover too, so a guest who simply finds
# the skull and jaw without solving anything cannot walk up and win.
JAW = os.environ.get("JARVIS_QUEST_JAW", (
    "Her jaw! She cannot speak to me without it. I saw something pale on the "
    "table in the room where everyone gathers. Bring them both to my own blood — "
    "six hundred years on, one of my line still walks among you tonight. Place "
    "them in their hands and say the words, or they will not know you. "
    "Now tell me your name, so that I may curse it kindly."
))

# How long after the jaw stage we treat the next thing said as a name. Expires
# so a visitor who wanders off does not cause the NEXT guest's first sentence to
# be filed as a winner.
NAME_WINDOW_S = float(os.environ.get("JARVIS_QUEST_NAME_WINDOW_S", "60"))

# ⚠️ Spoken AFTER the jaw instruction, so it must not send them back a step.
# The earlier version ended "go, fetch her jaw", which was written before the
# handover stage existed and contradicted the line immediately before it.
NAME_THANKS = os.environ.get("JARVIS_QUEST_NAME_THANKS", (
    "{name}. I shall remember it, which is more than I can say for most of the "
    "living. Now go, and do not forget the words — they will not know you "
    "without them."
))

# Asking Vlad to say it again must NOT reach the LLM. Claude does not know the
# quest exists, so it would improvise — confidently — and could send a child to
# a location that is not in the puzzle at all. Elena's story is 75 words in a
# loud room full of children; being asked to repeat it is the expected case,
# not an edge case.
REPEAT_ANY = {"again", "repeat", "repeated"}
REPEAT_MAX_WORDS = 8

# How long a scripted line stays repeatable. Bounded because the last line is
# shared state in an otherwise stateless design: without a window, a group that
# walks up cold and says "say that again" would be handed whatever stage the
# PREVIOUS group had reached.
REPEAT_WINDOW_S = float(os.environ.get("JARVIS_QUEST_REPEAT_WINDOW_S", "180"))

REPEAT_PREFIX = os.environ.get("JARVIS_QUEST_REPEAT_PREFIX",
                               "Again? Very well. Listen this time. ")

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
                    "lost", "lose", "loses", "losing",
                    # "what are you LOOKING for" is at least as natural as
                    # "waiting for", and missed entirely in the first field test.
                    "looking", "look", "looks", "seeking", "seek",
                    "searching", "search", "after", "expecting", "want"}),
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


def _story() -> str:
    """The story with the magic words filled in.

    Falls back to the raw string if a custom JARVIS_QUEST_STORY contains a
    stray brace — a formatting error must never be what stops the prop from
    answering at the most important moment of the puzzle.
    """
    try:
        return STORY.format(word1=WORD1, word2=WORD2)
    except (KeyError, IndexError, ValueError):
        return STORY


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
        self._last_line = None
        self._last_line_until = 0.0

    def _awaiting_name(self) -> bool:
        return time.monotonic() < self._awaiting_name_until

    def _remember(self, line: str) -> str:
        self._last_line, self._last_line_until = line, time.monotonic() + REPEAT_WINDOW_S
        return line

    def _wants_repeat(self, text: str) -> bool:
        if _count(text) > REPEAT_MAX_WORDS:
            return False
        words = _words(text)
        if REPEAT_ANY & words:
            return True
        # "what did you say", "what was that"
        return bool({"what"} & words and {"say", "said", "that"} & words)

    def check(self, text: str):
        """Scripted reply for this utterance, or None to let the LLM answer."""
        if not self.enabled or not (text or "").strip():
            return None

        # Before anything else: a repeat request must never reach the LLM.
        if (self._last_line and time.monotonic() < self._last_line_until
                and self._wants_repeat(text)):
            _log("REPEAT", text.strip())
            return REPEAT_PREFIX + self._last_line

        # A name is only expected in the window right after the jaw stage.
        if self._awaiting_name():
            self._awaiting_name_until = 0.0
            name = text.strip().rstrip(".!?")
            _log("WINNER-NAME", name)
            return self._remember(NAME_THANKS.format(name=name))

        # Magic words first: they are two fixed tokens, so they are both the most
        # reliable trigger and the one that must not be shadowed by a looser
        # stage matching the same sentence.
        toks = _tokens(text)
        # Earliest position of any accepted form, so "winter rose" and
        # "winter roses" behave identically.
        i1 = min((toks.index(w) for w in WORD1_FORMS if w in toks), default=None)
        i2 = min((toks.index(w) for w in WORD2_FORMS if w in toks), default=None)
        has1, has2 = i1 is not None, i2 is not None
        if has1 and has2:
            if i1 < i2:
                _log("STAGE-WORDS", text.strip())
                return self._remember(_story())
            _log("STAGE-WORDS-WRONG-ORDER", text.strip())
            return self._remember(WRONG_ORDER)
        if has1 or has2:
            # Fire when it reads as an attempt: either offered bare, or carrying
            # a word like "keyword" or "magic" that says they are guessing.
            # Chatter that merely mentions roses gets nothing.
            if _count(text) <= BARE_MAX_WORDS or (GUESS_MARKERS & _words(text)):
                _log("STAGE-WORDS-HALF", text.strip())
                return self._remember(HALF_WAY)

        words = _words(text)
        for stage in STAGES:
            if not all(group & words for group in stage["groups"]):
                continue
            if stage["max_words"] and _count(text) > stage["max_words"]:
                continue
            _log(f"STAGE-{stage['name'].upper()}", text.strip())
            if stage["name"] == "jaw":
                self._awaiting_name_until = time.monotonic() + NAME_WINDOW_S
            return self._remember(stage["reply"]())
        return None
