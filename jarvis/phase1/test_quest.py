"""
Unit tests for the Elena treasure hunt.

Pure text matching, so these run anywhere. They encode what "forgiving enough
for a child shouting in a noisy room" actually means, which is the whole design
risk: Whisper tiny.en will not hand us the sentence anyone rehearsed.
"""

import unittest

import quest


class StageMatchingTests(unittest.TestCase):
    def setUp(self):
        self.q = quest.Quest(enabled=True)
        quest.QUEST_LOG = "/dev/null"

    def _is(self, text, expected_start):
        reply = self.q.check(text)
        self.assertIsNotNone(reply, f"no match for {text!r}")
        self.assertTrue(reply.startswith(expected_start), reply[:60])

    def test_the_key_question_admits_he_has_forgotten(self):
        # Not the story — that needs the magic words. This is what sends guests
        # off to find them, and it explains why he holds back at all.
        self._is("Vlad, who are you waiting for?", "Waiting?")

    def test_key_question_variations_still_work(self):
        # The card is cryptic on purpose, so guests improvise rather than
        # reciting. Every one of these is a phrasing a real person would try,
        # and four of them failed before the matcher took question words and
        # waiting words as separate groups.
        for said in ("who do you miss", "who are you waiting on",
                     "so who is he waiting for", "who do you miss the most",
                     "what are you waiting for", "what do you wait for",
                     "what did you lose", "what have you lost",
                     "what are you missing"):
            with self.subTest(said=said):
                self.q._awaiting_name_until = 0
                self._is(said, "Waiting?")

    def test_a_loss_word_alone_does_not_trigger(self):
        # Otherwise "I lost my phone" gets a guest the whole story.
        for said in ("I lost my phone", "we are waiting for the pizza",
                     "my sister is missing her jumper"):
            with self.subTest(said=said):
                self.q._awaiting_name_until = 0
                self.assertIsNone(self.q.check(said))

    def test_a_question_word_alone_does_not_trigger(self):
        for said in ("who is that over there", "what is the weather"):
            with self.subTest(said=said):
                self.q._awaiting_name_until = 0
                self.assertIsNone(self.q.check(said))

    def test_found_the_skull(self):
        self._is("we found the skull", "Elena!")

    def test_found_stage_does_not_require_her_name(self):
        # Possessives transcribe badly; requiring "Elena's" would only add
        # failure. Nobody reaches this stage by accident.
        self._is("I have a skull", "Elena!")

    def test_jaw_stage(self):
        self._is("the jaw", "Her jaw!")

    def test_lower_teeth_also_works(self):
        self._is("her teeth are missing", "Her jaw!")

    def test_long_sentence_mentioning_jaw_does_not_trigger(self):
        # Otherwise ordinary chatter gives the answer away to the next group.
        self.assertIsNone(
            self.q.check("my grandad broke his jaw falling off a ladder last year")
        )

    def test_ordinary_conversation_is_left_to_the_llm(self):
        for said in ("what is the weather", "are you really dead", "hello"):
            with self.subTest(said=said):
                self.assertIsNone(self.q.check(said))

    def test_empty_transcript_is_ignored(self):
        self.assertIsNone(self.q.check(""))
        self.assertIsNone(self.q.check("   "))


class MagicWordTests(unittest.TestCase):
    """Two fixed words beat any amount of clever matching — which is the whole
    reason this stage exists. These guard that it stays reliable AND that a
    near-miss never answers with silence."""

    def setUp(self):
        self.q = quest.Quest(enabled=True)
        quest.QUEST_LOG = "/dev/null"

    def test_words_in_order_tell_the_story(self):
        reply = self.q.check(f"{quest.WORD1} {quest.WORD2}")
        self.assertTrue(reply.startswith("Her name was Elena"), reply[:50])

    def test_words_inside_a_sentence_still_work(self):
        reply = self.q.check(f"the magic words are {quest.WORD1} {quest.WORD2}")
        self.assertTrue(reply.startswith("Her name was Elena"), reply[:50])

    def test_wrong_order_gets_a_hint_not_silence(self):
        # Someone who found both words and got nothing has no way to know they
        # were one swap from solving it.
        reply = self.q.check(f"{quest.WORD2} {quest.WORD1}")
        self.assertIsNotNone(reply)
        self.assertTrue(reply.startswith("Close."), reply[:50])

    def test_one_word_alone_is_not_enough(self):
        self.assertIsNone(self.q.check(quest.WORD1))
        self.assertIsNone(self.q.check(quest.WORD2))

    def test_a_magic_word_in_ordinary_chatter_does_not_fire(self):
        self.assertIsNone(self.q.check(f"it is cold like {quest.WORD1} in here"))


class NameCaptureTests(unittest.TestCase):
    def setUp(self):
        self.q = quest.Quest(enabled=True)
        quest.QUEST_LOG = "/dev/null"

    def test_name_is_taken_only_after_the_jaw_stage(self):
        self.assertIsNone(self.q.check("Sophie"))          # nothing pending
        self.q.check("the jaw")                            # opens the window
        reply = self.q.check("Sophie")
        self.assertIn("Sophie", reply)

    def test_window_closes_after_one_name(self):
        self.q.check("the jaw")
        self.q.check("Sophie")
        self.assertIsNone(self.q.check("Marcus"))

    def test_window_expires_so_the_next_guest_is_not_logged_as_a_winner(self):
        self.q.check("the jaw")
        self.q._awaiting_name_until = 0.0                  # simulate the timeout
        self.assertIsNone(self.q.check("hello there"))


class DisabledTests(unittest.TestCase):
    def test_disabled_quest_never_intercepts(self):
        q = quest.Quest(enabled=False)
        self.assertIsNone(q.check("Vlad, who are you waiting for?"))
        self.assertIsNone(q.check("we found the skull"))


if __name__ == "__main__":
    unittest.main()
