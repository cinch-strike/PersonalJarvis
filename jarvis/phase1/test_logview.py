"""
Unit tests for the transcript view.

Pure rendering and the refuse-to-serve guard — no socket is opened, no database
is touched, so these run anywhere the rest of the suite does.
"""

import unittest
from unittest import mock

import logview


def _turn(sid, role, content, at="2026-09-09 19:00:00"):
    return {"id": 1, "session_id": sid, "role": role,
            "content": content, "created_at": at}


class MarkdownTests(unittest.TestCase):
    def test_empty_says_so_rather_than_rendering_nothing(self):
        out = logview.render_markdown([])
        self.assertIn("No conversations recorded yet", out)

    def test_turns_are_grouped_by_session(self):
        out = logview.render_markdown([
            _turn(1, "user", "hello"),
            _turn(2, "user", "hello again"),
        ])
        self.assertIn("## Session 1", out)
        self.assertIn("## Session 2", out)

    def test_roles_render_as_readable_speakers(self):
        out = logview.render_markdown([
            _turn(1, "user", "are you dead"),
            _turn(1, "assistant", "I am resting"),
        ])
        self.assertIn("Guest:", out)
        self.assertIn(f"{logview.config.NAME}:", out)


class HtmlEscapingTests(unittest.TestCase):
    """Transcript content is speech from strangers plus model output — it is
    untrusted text by definition and must never reach the page unescaped."""

    def test_script_tags_in_speech_are_escaped(self):
        html = logview.render_html([_turn(1, "user", "<script>alert(1)</script>")])
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

    def test_quotes_and_ampersands_are_escaped(self):
        html = logview.render_html([_turn(1, "user", 'a & b "c"')])
        self.assertIn("&amp;", html)
        self.assertNotIn('a & b "c"', html)

    def test_timestamp_is_escaped_too(self):
        html = logview.render_html([_turn(1, "user", "hi", at="<b>x</b>")])
        self.assertNotIn("<b>x</b>", html)

    def test_empty_renders_a_page_not_a_crash(self):
        self.assertIn("Nothing recorded yet", logview.render_html([]))


class TokenGuardTests(unittest.TestCase):
    def test_serve_refuses_without_a_token(self):
        # Fail closed: guests share the WiFi, and this page is the whole night.
        with mock.patch.object(logview, "TOKEN", ""):
            self.assertEqual(logview.serve(), 1)


if __name__ == "__main__":
    unittest.main()
