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
        self.assertIn("Elena", reply)

    def test_words_inside_a_sentence_still_work(self):
        reply = self.q.check(f"the magic words are {quest.WORD1} {quest.WORD2}")
        self.assertIn("Elena", reply)

    def test_the_story_echoes_the_words_back(self):
        # Without the moment of recognition it jumps straight into the story
        # and lands flat — the payoff needs a beat.
        reply = self.q.check(f"{quest.WORD1} {quest.WORD2}")
        self.assertTrue(reply.lower().startswith(quest.WORD1), reply[:40])
        self.assertIn(quest.WORD2, reply.lower())

    def test_story_placeholders_track_a_word_change(self):
        # If the magic words change, the recognition line must follow them.
        orig = (quest.WORD1, quest.WORD2, quest.WORD1_FORMS, quest.WORD2_FORMS)
        try:
            # Both must move together: the _FORMS drive matching, the bare names
            # drive what Vlad echoes back.
            quest.WORD1_FORMS, quest.WORD2_FORMS = ["amber"], ["willow"]
            quest.WORD1, quest.WORD2 = "amber", "willow"
            reply = quest.Quest(enabled=True).check("amber willow")
            self.assertIsNotNone(reply)
            self.assertIn("amber willow", reply.lower())
            self.assertNotIn(orig[0], reply.lower())
        finally:
            (quest.WORD1, quest.WORD2,
             quest.WORD1_FORMS, quest.WORD2_FORMS) = orig

    def test_a_custom_story_without_placeholders_is_left_alone(self):
        # A formatting error must never be what stops the prop answering at the
        # most important moment of the puzzle.
        orig = quest.STORY
        try:
            quest.STORY = "no placeholders here at all"
            self.assertEqual(quest._story(), "no placeholders here at all")
            quest.STORY = "a stray { brace"
            self.assertEqual(quest._story(), "a stray { brace")
        finally:
            quest.STORY = orig

    def test_singular_and_plural_both_work(self):
        # Bianca's clue asks guests to "name the bloom", singular, so they say
        # "rose". Accepting only the plural would fail everyone who solved it,
        # and no wording of the clue can control what someone actually says.
        for second in quest.WORD2_FORMS:
            with self.subTest(second=second):
                q = quest.Quest(enabled=True)
                reply = q.check(f"{quest.WORD1} {second}")
                self.assertIn("Elena", reply)

    def test_either_form_alone_gets_the_half_way_hint(self):
        for second in quest.WORD2_FORMS:
            with self.subTest(second=second):
                q = quest.Quest(enabled=True)
                self.assertTrue(q.check(second).startswith("One of them"))

    def test_order_is_checked_across_forms(self):
        q = quest.Quest(enabled=True)
        reply = q.check(f"{quest.WORD2_FORMS[-1]} {quest.WORD1}")
        self.assertTrue(reply.startswith("Close."), reply[:40])

    def test_wrong_order_gets_a_hint_not_silence(self):
        # Someone who found both words and got nothing has no way to know they
        # were one swap from solving it.
        reply = self.q.check(f"{quest.WORD2} {quest.WORD1}")
        self.assertIsNotNone(reply)
        self.assertTrue(reply.startswith("Close."), reply[:50])

    def test_one_word_alone_is_acknowledged_not_ignored(self):
        # They will usually find one before the other. Silence here reads as
        # "wrong word" and stops them looking for the second.
        for word in (quest.WORD1, quest.WORD2):
            with self.subTest(word=word):
                reply = self.q.check(word)
                self.assertIsNotNone(reply)
                self.assertTrue(reply.startswith("One of them"), reply[:40])

    def test_half_way_hint_does_not_leak_the_other_word(self):
        reply = self.q.check(quest.WORD1)
        self.assertNotIn(quest.WORD2, reply.lower())

    def test_a_magic_word_in_a_long_sentence_is_chatter_not_an_attempt(self):
        # Answering "we sat by the roses all afternoon" would hand a passer-by
        # half the puzzle for nothing.
        self.assertIsNone(
            self.q.check(f"we sat by the {quest.WORD2} in the garden all afternoon")
        )

    def test_a_magic_word_in_ordinary_chatter_does_not_fire(self):
        self.assertIsNone(self.q.check(f"it is cold like {quest.WORD1} in here"))


class FieldTranscriptRegressionTests(unittest.TestCase):
    """Sentences taken verbatim from the first live test, both of which failed.

    Kept as literal strings rather than tidied paraphrases — the point is that
    real speech through Whisper does not look like the phrases anyone drafts.
    """

    def setUp(self):
        self.q = quest.Quest(enabled=True)
        quest.QUEST_LOG = "/dev/null"

    def test_looking_for_reaches_the_forgotten_stage(self):
        # Only "waiting/miss/lost" were listed; "looking" is just as natural.
        reply = self.q.check("Do you know who what you're looking for?")
        self.assertIsNotNone(reply)
        self.assertTrue(reply.startswith("Waiting?"), reply[:40])

    def test_a_nine_word_guess_still_counts_as_a_guess(self):
        # Failed on a four-word cutoff. Length cannot separate a guess from
        # chatter; a marker word like "keyword" can.
        reply = self.q.check("Okay, I think I know the keyword, it's winter.")
        self.assertIsNotNone(reply)
        self.assertTrue(reply.startswith("One of them"), reply[:40])

    def test_chatter_of_the_same_length_still_stays_quiet(self):
        self.assertIsNone(
            self.q.check("we sat by the roses in the garden all afternoon"))


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
