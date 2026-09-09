"""
Unit tests for env-file duplicate detection.
────────────────────────────────────────────
Pure text handling, so these run anywhere — no Pi, no mic, no env file on disk.

Guarding real faults, not hypotheticals: on 9 Sep 2026 a duplicated
JARVIS_ELEVENLABS_KEY killed the voice with HTTP 401 because the stale copy came
last, and a duplicated JARVIS_INPUT_MODE had "wake_word" and "motion" in the
same file with only line order deciding which the prop used.
"""

import os
import tempfile
import unittest

import config
import doctor


def _env_file(text: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False)
    f.write(text)
    f.close()
    return f.name


class DuplicateEnvVarsTests(unittest.TestCase):
    def setUp(self):
        self._paths = []

    def tearDown(self):
        for p in self._paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _write(self, text):
        p = _env_file(text)
        self._paths.append(p)
        return p

    def test_clean_file_has_no_duplicates(self):
        p = self._write("A=1\nB=2\nC=3\n")
        self.assertEqual(config.duplicate_env_vars(p), {})

    def test_identical_duplicate_is_reported(self):
        p = self._write("A=1\nB=2\nA=1\n")
        self.assertEqual(config.duplicate_env_vars(p), {"A": ["1", "1"]})

    def test_conflicting_duplicate_keeps_both_values_in_order(self):
        # The real JARVIS_INPUT_MODE fault: order alone decided the behaviour.
        p = self._write("JARVIS_INPUT_MODE=wake_word\nX=1\nJARVIS_INPUT_MODE=motion\n")
        self.assertEqual(
            config.duplicate_env_vars(p),
            {"JARVIS_INPUT_MODE": ["wake_word", "motion"]},
        )

    def test_export_prefix_is_understood(self):
        # .bashrc style and jarvis.env style must both be caught.
        p = self._write("export A=1\nA=2\n")
        self.assertEqual(config.duplicate_env_vars(p), {"A": ["1", "2"]})

    def test_comments_and_blank_lines_are_ignored(self):
        p = self._write("# A=1\n\n   \nA=1\n")
        self.assertEqual(config.duplicate_env_vars(p), {})

    def test_values_containing_equals_are_kept_whole(self):
        # plughw:CARD=V3,DEV=0 must survive intact.
        p = self._write("O=plughw:CARD=V3,DEV=0\nO=plughw:3,0\n")
        self.assertEqual(
            config.duplicate_env_vars(p),
            {"O": ["plughw:CARD=V3,DEV=0", "plughw:3,0"]},
        )

    def test_missing_file_is_not_an_error(self):
        # This runs at boot; it must never be the thing that stops the prop.
        self.assertEqual(config.duplicate_env_vars("/no/such/file.env"), {})


class DoctorEnvCheckTests(unittest.TestCase):
    """The severity split matters: agreeing duplicates are untidy, conflicting
    ones mean the file does not do what it appears to say."""

    def setUp(self):
        self._orig = config.ENV_FILE
        self._paths = []

    def tearDown(self):
        config.ENV_FILE = self._orig
        for p in self._paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _use(self, text):
        p = _env_file(text)
        self._paths.append(p)
        config.ENV_FILE = p

    def test_clean_file_passes(self):
        self._use("A=1\nB=2\n")
        self.assertEqual(doctor.check_env_file().status, doctor.OK)

    def test_agreeing_duplicate_warns(self):
        self._use("A=1\nA=1\n")
        self.assertEqual(doctor.check_env_file().status, doctor.WARN)

    def test_conflicting_duplicate_fails(self):
        self._use("A=1\nA=2\n")
        c = doctor.check_env_file()
        self.assertEqual(c.status, doctor.FAIL)
        self.assertIn("A", c.detail)


if __name__ == "__main__":
    unittest.main()
