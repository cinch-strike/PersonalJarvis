# Cowork Brief — Halloween treasure hunt clue cards

Hand this whole file to Cowork. It describes the puzzle it needs to write two
clue cards for, and the constraints those cards must satisfy.

**Related:** `HALLOWEEN.md` (the prop), `phase1/quest.py` (the code that matches
what guests say). The quest strings are all config — see `JARVIS_QUEST_*` in
`HANDOFF.md` — so wording can change right up to the night without touching code.

---

## What exists

A talking animatronic skull called **Vlad** sits at our Halloween party. He is an
ancient Eastern European vampire count — theatrical, vain, put-upon, reduced to a
table ornament and with opinions about that. He hears guests, replies in
character, and his jaw and eyes move as he speaks.

Adults and children both attend. Everything is **PG**: pantomime villain, never
horror. No violence, no biting, no blood, nothing that would genuinely frighten
a child.

## The puzzle chain

1. Guests get a cryptic card around **3pm**. It leads them to Vlad without naming
   him, and tells them to ask what he is waiting for.
2. They ask. Vlad says he has been waiting six hundred years but has **forgotten
   what for** — her face gone, her name gone. There were old words she used to
   say. If someone finds them, he might remember.
3. **Two more clues, hidden separately, each lead to one word.**
4. Said to Vlad **in order**, the words unlock the story.
5. He tells them about **Elena**, who was always cold, who went to warm herself in
   "a great box of hot water out in the garden" and never came back. That is the
   spa pool, where a jawless skull floats.
6. They report finding a skull. He asks what is missing. They say "the jaw".
7. He sends them to fetch it from the lounge table, and asks their name for the
   log.
8. Skull plus jaw brought to Donnie wins.

## What we need from you

**Two clue cards.** Each must lead to exactly ONE word:

| Card | Answer |
|---|---|
| Clue A | **WINTER** |
| Clue B | **ROSES** |

## Constraints

- **Medium difficulty.** Children can ask a parent for help.
- The answer word must **not appear in its own clue**.
- Each answer is a **single common English word**, not a phrase.
- The two clues should feel like a **matched pair** — found separately, but
  clearly two halves of one thing.
- PG and spooky-fun, not frightening.
- Cards will be printed and hidden around a house and garden.

## ⚠️ Two things that cannot change

**The answer words are fixed.** "Winter" and "roses" were chosen to survive
speech recognition in a loud room, not for atmosphere: both are two syllables,
both extremely common English, neither has a homophone, and nothing about them
sounds alike, so a half-heard one cannot be mistaken for the other. A more
evocative word will be misheard and the puzzle dies at its last step. This
project has already lost time to exactly that class of mistake.

**Each clue must resolve to one word, not a phrase.** The code matches those two
tokens specifically, and checks that the first is spoken before the second.

## Tone reference

This is the card that starts the hunt. Match its register:

> One here has waited longer than these walls,
> who owns no crown, no castle and no halls.
> He will not raise it first. He is too proud.
> But he will answer — if you ask aloud.
> Not what he was, and not what he became.
> Ask what he waits for. He'll give you her name.

## Nice to have

A short in-character line Vlad could say if someone brings him only **one** of
the two words — enough to confirm they are on the right track without giving the
other away.
