"""
Tests for aws_sync.py — pushing unsynced SQLite rows to DynamoDB.

DynamoDB is faked (no network, no AWS account): we patch aws_sync._get_table
to return a stand-in table that records writes. The graceful-failure contract
is the focus — sync must never raise and must only mark rows synced on a clean
write. aws_sync.py's logic is exercised, never modified.

Run: .venv/bin/python -m unittest test_aws_sync -v
"""

import os
import tempfile
import unittest
from unittest import mock

import aws_sync
import memory
from botocore.exceptions import ClientError


# ─── Fakes ──────────────────────────────────────────────────────────────────

class FakeBatch:
    def __init__(self, fail=False):
        self.items = []
        self._fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def put_item(self, Item):
        if self._fail:
            raise ClientError(
                {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
                "PutItem",
            )
        self.items.append(Item)


class FakeTable:
    def __init__(self, fail=False):
        self.batch = FakeBatch(fail=fail)

    def batch_writer(self):
        return self.batch


def _turn(id, session_id=1, role="user", content="hi", created_at="2026-01-01T00:00:00Z"):
    return {
        "id": id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": created_at,
    }


# ─── Unit tests with a faked table ───────────────────────────────────────────

class TestSyncWithFakeTable(unittest.TestCase):
    def test_nothing_to_sync_returns_zero(self):
        self.assertEqual(aws_sync.sync_to_dynamodb(turns=[]), 0)

    def test_no_table_keeps_rows_queued(self):
        with mock.patch.object(aws_sync, "_get_table", return_value=None), \
             mock.patch.object(memory, "mark_synced") as marker:
            result = aws_sync.sync_to_dynamodb(turns=[_turn(1)])
        self.assertEqual(result, 0)
        marker.assert_not_called()

    def test_successful_sync_writes_and_marks(self):
        table = FakeTable()
        turns = [_turn(1, content="a"), _turn(2, role="assistant", content="b")]
        with mock.patch.object(aws_sync, "_get_table", return_value=table), \
             mock.patch.object(memory, "mark_synced") as marker:
            result = aws_sync.sync_to_dynamodb(turns=turns)

        self.assertEqual(result, 2)
        # Items mapped correctly (id -> turn_id).
        self.assertEqual(
            [(i["session_id"], i["turn_id"], i["role"], i["content"]) for i in table.batch.items],
            [(1, 1, "user", "a"), (1, 2, "assistant", "b")],
        )
        marker.assert_called_once_with([1, 2])

    def test_write_failure_marks_nothing_and_does_not_raise(self):
        table = FakeTable(fail=True)
        with mock.patch.object(aws_sync, "_get_table", return_value=table), \
             mock.patch.object(memory, "mark_synced") as marker:
            result = aws_sync.sync_to_dynamodb(turns=[_turn(1)])
        self.assertEqual(result, 0)
        marker.assert_not_called()


# ─── Integration: real temp SQLite + faked table ─────────────────────────────

class TestSyncIntegration(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = memory.DB_PATH
        self._tmpdir = tempfile.TemporaryDirectory()
        memory.DB_PATH = os.path.join(self._tmpdir.name, "test_memory.db")

    def tearDown(self):
        memory.DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()

    def test_pulls_unsynced_then_flips_flag_in_db(self):
        sid = memory.start_session()
        memory.save_turn(sid, "user", "remember this")
        memory.save_turn(sid, "assistant", "noted")
        self.assertEqual(len(memory.get_unsynced_turns()), 2)

        table = FakeTable()
        with mock.patch.object(aws_sync, "_get_table", return_value=table):
            synced = aws_sync.sync_to_dynamodb()  # turns=None → pull from DB

        self.assertEqual(synced, 2)
        self.assertEqual(len(table.batch.items), 2)
        # Rows are now flagged synced in the real (temp) DB.
        self.assertEqual(memory.get_unsynced_turns(), [])


if __name__ == "__main__":
    unittest.main()
