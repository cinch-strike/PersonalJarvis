"""
Tests for memory.py — SQLite sessions + conversation turns.

Each test runs against a throwaway DB in a temp dir (memory.DB_PATH is
swapped out and restored), so nothing touches the real jarvis_memory.db.
memory.py's logic is exercised, never modified.

Run: .venv/bin/python -m unittest test_memory -v
"""

import os
import sqlite3
import tempfile
import unittest

import memory


class MemoryTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = memory.DB_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        memory.DB_PATH = os.path.join(self._tmpdir.name, "test_memory.db")

    def tearDown(self):
        memory.DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()

    def _raw(self, query, params=()):
        """Query the temp DB directly to assert on stored state."""
        conn = sqlite3.connect(memory.DB_PATH)
        try:
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()


class TestSessions(MemoryTestCase):
    def test_start_session_returns_increasing_ids(self):
        first = memory.start_session()
        second = memory.start_session()
        self.assertEqual(second, first + 1)

    def test_new_session_has_no_end_time(self):
        sid = memory.start_session()
        ended = self._raw("SELECT ended_at FROM sessions WHERE id=?", (sid,))[0][0]
        self.assertIsNone(ended)

    def test_close_session_sets_end_time(self):
        sid = memory.start_session()
        memory.close_session(sid)
        ended = self._raw("SELECT ended_at FROM sessions WHERE id=?", (sid,))[0][0]
        self.assertIsNotNone(ended)


class TestTurns(MemoryTestCase):
    def test_save_and_recall_roundtrip(self):
        sid = memory.start_session()
        memory.save_turn(sid, "user", "hello")
        memory.save_turn(sid, "assistant", "hi there")
        turns = memory.load_recent_turns()
        self.assertEqual(
            [(t["role"], t["content"]) for t in turns],
            [("user", "hello"), ("assistant", "hi there")],
        )

    def test_recall_is_chronological_oldest_first(self):
        sid = memory.start_session()
        for i in range(5):
            memory.save_turn(sid, "user", f"msg{i}")
        contents = [t["content"] for t in memory.load_recent_turns()]
        self.assertEqual(contents, ["msg0", "msg1", "msg2", "msg3", "msg4"])

    def test_recall_respects_limit_and_keeps_latest(self):
        sid = memory.start_session()
        for i in range(10):
            memory.save_turn(sid, "user", f"msg{i}")
        turns = memory.load_recent_turns(n=3)
        # Most recent 3, still oldest→newest within that window.
        self.assertEqual([t["content"] for t in turns], ["msg7", "msg8", "msg9"])

    def test_recall_empty_returns_empty_list(self):
        self.assertEqual(memory.load_recent_turns(), [])

    def test_invalid_role_raises(self):
        sid = memory.start_session()
        with self.assertRaises(ValueError):
            memory.save_turn(sid, "system", "nope")
        # And nothing was written.
        self.assertEqual(self._raw("SELECT COUNT(*) FROM conversations")[0][0], 0)


class TestSyncSupport(MemoryTestCase):
    def test_get_unsynced_returns_only_unsynced_oldest_first(self):
        sid = memory.start_session()
        t1 = memory.save_turn(sid, "user", "a")
        t2 = memory.save_turn(sid, "assistant", "b")
        memory.mark_synced([t1])
        unsynced = memory.get_unsynced_turns()
        self.assertEqual([t["id"] for t in unsynced], [t2])

    def test_mark_synced_flips_flag(self):
        sid = memory.start_session()
        t1 = memory.save_turn(sid, "user", "a")
        memory.mark_synced([t1])
        synced = self._raw("SELECT synced FROM conversations WHERE id=?", (t1,))[0][0]
        self.assertEqual(synced, 1)

    def test_mark_synced_empty_is_noop(self):
        sid = memory.start_session()
        memory.save_turn(sid, "user", "a")
        memory.mark_synced([])  # must not raise
        self.assertEqual(len(memory.get_unsynced_turns()), 1)


if __name__ == "__main__":
    unittest.main()
