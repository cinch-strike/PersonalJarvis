#!/usr/bin/env python3
"""
Jarvis Phase 1 — AWS sync module
──────────────────────────────────────────────────────
Pushes unsynced SQLite conversation rows up to a DynamoDB table
("jarvis-memory") so memory survives across machines / Phase 2 hardware.

Designed to FAIL GRACEFULLY: if boto3 is missing, AWS credentials aren't
configured, or the network is down, sync logs a warning and returns without
raising — Jarvis must never crash because the cloud is unreachable.

DynamoDB table expectation (create once, on-demand billing):
    table name : jarvis-memory
    partition key : session_id  (Number)
    sort key      : turn_id     (Number)

Public API:
    sync_to_dynamodb(turns=None) -> int   # returns count successfully synced
"""

import os

TABLE_NAME = "jarvis-memory"
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "jarvis")

# boto3 is optional at import time — Jarvis should run fine without it.
try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        PartialCredentialsError,
    )
    _BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    _BOTO3_AVAILABLE = False
    # Stand-in exception types so the except clauses below stay valid.
    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

    class NoCredentialsError(Exception):
        pass

    class PartialCredentialsError(Exception):
        pass


def _log(msg: str) -> None:
    print(f"  [aws_sync] {msg}")


def _get_table():
    """Return a DynamoDB Table resource, or None if unavailable.

    Verifies credentials are actually resolvable before returning so callers
    get a clean None rather than a deferred failure mid-write.
    """
    if not _BOTO3_AVAILABLE:
        _log("boto3 not installed — skipping cloud sync (pip install boto3).")
        return None

    try:
        session = boto3.session.Session(region_name=AWS_REGION, profile_name=AWS_PROFILE)
        if session.get_credentials() is None:
            _log("no AWS credentials found — skipping cloud sync.")
            return None
        return session.resource("dynamodb").Table(TABLE_NAME)
    except (NoCredentialsError, PartialCredentialsError):
        _log("incomplete AWS credentials — skipping cloud sync.")
        return None
    except (BotoCoreError, ClientError) as e:
        _log(f"could not init DynamoDB client ({e}) — skipping cloud sync.")
        return None


def sync_to_dynamodb(turns=None) -> int:
    """Push unsynced conversation turns to DynamoDB.

    Args:
        turns: optional list of turn dicts (keys: id, session_id, role,
               content, created_at). If None, pulls all unsynced rows from
               the local SQLite store via memory.get_unsynced_turns().

    Returns:
        The number of turns successfully written. Always returns an int and
        never raises — failures are logged and counted as 0 synced.
    """
    # Imported lazily so a broken memory module can't break import of this one.
    import memory

    if turns is None:
        turns = memory.get_unsynced_turns()

    if not turns:
        _log("nothing to sync.")
        return 0

    table = _get_table()
    if table is None:
        # Graceful no-op: rows stay marked unsynced and retry next time.
        _log(f"{len(turns)} turn(s) left queued for next sync.")
        return 0

    synced_ids = []
    try:
        with table.batch_writer() as batch:
            for turn in turns:
                batch.put_item(
                    Item={
                        "session_id": turn["session_id"],
                        "turn_id": turn["id"],
                        "role": turn["role"],
                        "content": turn["content"],
                        "created_at": turn["created_at"],
                    }
                )
                synced_ids.append(turn["id"])
    except (BotoCoreError, ClientError) as e:
        # batch_writer flushes on context exit; a failure there means we can't
        # be sure which items landed, so don't mark anything synced.
        _log(f"sync failed ({e}) — {len(turns)} turn(s) remain queued.")
        return 0
    except Exception as e:  # noqa: BLE001 — never let sync crash Jarvis
        _log(f"unexpected sync error ({e}) — turns remain queued.")
        return 0

    # Only flip the local flag once the batch write succeeded.
    try:
        memory.mark_synced(synced_ids)
    except Exception as e:  # noqa: BLE001
        _log(f"warning: pushed {len(synced_ids)} turn(s) but failed to "
             f"mark them synced locally ({e}); may re-push next run.")

    _log(f"synced {len(synced_ids)} turn(s) to {TABLE_NAME}.")
    return len(synced_ids)


if __name__ == "__main__":
    # Manual test: python3 aws_sync.py
    count = sync_to_dynamodb()
    print(f"Done. {count} turn(s) synced.")
