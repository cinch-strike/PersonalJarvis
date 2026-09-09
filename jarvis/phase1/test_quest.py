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

    def test_the_key_question(self):
        self._is("Vlad, who are you waiting for?", "Her name was Elena")

    def test_key_question_variations_still_work(self):
        # A child half-remembers it, or Whisper drops a word.
        for said in ("who do you miss", "who are you waiting on",
                     "so who is he waiting for", "who do you miss the most"):
            with self.subTest(said=said):
                self.q._awaiting_name_until = 0
                self._is(said, "Her name was Elena")

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
