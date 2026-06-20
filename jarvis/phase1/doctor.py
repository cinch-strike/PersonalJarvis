"""
Jarvis environment doctor.
──────────────────────────
A read-only pre-flight check for a new machine or a freshly set-up Pi. It
verifies everything Jarvis needs *without opening the mic, loading Whisper, or
calling an LLM* — so it's safe and fast to run during hardware bring-up.

  python jarvis.py --doctor

Each probe returns OK / WARN / FAIL:
  OK    ready to go
  WARN  not fatal, but something to know (e.g. offline LLM not reachable yet)
  FAIL  Jarvis won't work until this is fixed

Exit code is 0 unless at least one probe FAILs.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass

import config

OK, WARN, FAIL = "OK", "WARN", "FAIL"
_ICON = {OK: "✅", WARN: "⚠️ ", FAIL: "❌"}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def check_python() -> Check:
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) == (3, 11):
        return Check("Python", OK, ver)
    if (3, 9) <= (v.major, v.minor) < (3, 14):
        return Check("Python", WARN, f"{ver} — project targets 3.11 (3.11 recommended)")
    return Check(
        "Python", WARN,
        f"{ver} — 3.14+ has known faster-whisper issues; use 3.11",
    )


def check_tts() -> Check:
    import tts
    try:
        backend = tts.select_tts_backend(config.VOICE, override=config.TTS_BACKEND)
        return Check("TTS backend", OK, backend.name)
    except tts.TTSError as e:
        return Check("TTS backend", FAIL, str(e))


def check_input() -> Check:
    import input_trigger
    try:
        trigger = input_trigger.select_input_trigger(
            config.INPUT_MODE, lambda: None, lambda: None, lambda: None
        )
        return Check("Input mode", OK, trigger.name)
    except input_trigger.InputError as e:
        return Check("Input mode", FAIL, str(e))


def check_llm() -> Check:
    import llm
    try:
        backend = llm.select_llm_backend(config.LLM_BACKEND)
    except llm.LLMError as e:
        return Check("LLM backend", FAIL, str(e))
    if backend.available():
        return Check("LLM backend", OK, f"{backend.name} (reachable)")
    return Check(
        "LLM backend", WARN,
        f"{backend.name} not reachable now — set ANTHROPIC_API_KEY or start Ollama",
    )


def check_anthropic_key() -> Check:
    mode = (config.LLM_BACKEND or "auto").lower()
    if mode == "ollama":
        return Check("Anthropic key", OK, "n/a (offline ollama mode)")
    if os.environ.get("ANTHROPIC_API_KEY"):
        return Check("Anthropic key", OK, "ANTHROPIC_API_KEY is set")
    status = WARN if mode == "auto" else FAIL
    return Check("Anthropic key", status, "ANTHROPIC_API_KEY not set")


def check_sqlite() -> Check:
    import memory
    path = memory.DB_PATH
    db_dir = os.path.dirname(path) or "."
    if not os.access(db_dir, os.W_OK):
        return Check("Memory (SQLite)", FAIL, f"directory not writable: {db_dir}")
    exists = os.path.exists(path)
    if exists and not os.access(path, os.W_OK):
        return Check("Memory (SQLite)", FAIL, f"db file not writable: {path}")
    state = "existing db" if exists else "will be created on first run"
    return Check("Memory (SQLite)", OK, f"{path} ({state})")


def check_aws() -> Check:
    """Best-effort DynamoDB reachability via aws_sync's table/region/profile."""
    import aws_sync
    if not aws_sync._BOTO3_AVAILABLE:
        return Check("AWS DynamoDB", WARN, "boto3 not installed — cloud sync disabled")
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError, BotoCoreError

        session = boto3.session.Session(
            region_name=aws_sync.AWS_REGION, profile_name=aws_sync.AWS_PROFILE
        )
        if session.get_credentials() is None:
            return Check(
                "AWS DynamoDB", WARN,
                f"no credentials for profile '{aws_sync.AWS_PROFILE}' — "
                "run: aws configure --profile jarvis",
            )
        client = session.client(
            "dynamodb",
            config=Config(
                connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}
            ),
        )
        resp = client.describe_table(TableName=aws_sync.TABLE_NAME)
        tstatus = resp["Table"]["TableStatus"]
        ok = tstatus == "ACTIVE"
        return Check(
            "AWS DynamoDB",
            OK if ok else WARN,
            f"{aws_sync.TABLE_NAME} @ {aws_sync.AWS_REGION} ({tstatus})",
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "ResourceNotFoundException":
            return Check(
                "AWS DynamoDB", FAIL,
                f"table '{aws_sync.TABLE_NAME}' not found in {aws_sync.AWS_REGION}",
            )
        return Check("AWS DynamoDB", WARN, f"reachability check failed: {e}")
    except (BotoCoreError, Exception) as e:  # noqa: BLE001 — doctor must not crash
        return Check("AWS DynamoDB", WARN, f"could not reach DynamoDB: {e}")


# Order matters only for display.
ALL_CHECKS = (
    check_python,
    check_tts,
    check_input,
    check_llm,
    check_anthropic_key,
    check_sqlite,
    check_aws,
)


def run() -> int:
    """Run every probe, print a report, and return an exit code."""
    print(f"\n🩺 Jarvis doctor  (platform: {platform.system()})\n")
    results = [probe() for probe in ALL_CHECKS]

    width = max(len(r.name) for r in results)
    for r in results:
        print(f"   {_ICON[r.status]} {r.name.ljust(width)}  {r.detail}")

    fails = sum(1 for r in results if r.status == FAIL)
    warns = sum(1 for r in results if r.status == WARN)
    print()
    if fails:
        print(f"   ❌ {fails} blocking issue(s), {warns} warning(s). "
              "Fix the ❌ items before running Jarvis.\n")
        return 1
    if warns:
        print(f"   ⚠️  Ready, with {warns} warning(s) to be aware of.\n")
        return 0
    print("   ✅ All systems go.\n")
    return 0
