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
    # 3.11–3.13 are confirmed working (Pi runs 3.13.5 with faster-whisper fine).
    # 3.14+ has known faster-whisper issues; <3.11 is untested.
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if (3, 11) <= (v.major, v.minor) <= (3, 13):
        return Check("Python", OK, ver)
    if (v.major, v.minor) >= (3, 14):
        return Check(
            "Python", WARN, f"{ver} — 3.14+ has known faster-whisper issues; use 3.11–3.13"
        )
    return Check("Python", WARN, f"{ver} — untested; project targets 3.11–3.13")


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


def check_wake_word() -> Check:
    """Only relevant when running in wake_word mode (the headless-Pi trigger)."""
    if (config.INPUT_MODE or "").strip().lower() != "wake_word":
        return Check("Wake word", OK, "n/a (push_to_talk mode)")
    try:
        import pvporcupine  # noqa: F401
    except ImportError:
        return Check(
            "Wake word", FAIL,
            "pvporcupine not installed — .venv/bin/python -m pip install pvporcupine",
        )
    if not config.PORCUPINE_KEY:
        return Check(
            "Wake word", FAIL,
            "JARVIS_PORCUPINE_KEY not set (free key: https://console.picovoice.ai)",
        )
    return Check("Wake word", OK, f"pvporcupine ready, keyword \"{config.WAKE_KEYWORD}\"")


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
    """Verify AWS credentials resolve for the sync profile.

    We deliberately do NOT call describe_table/list_tables: JarvisMemoryPolicy
    grants only PutItem (read/describe are denied by design), so probing the
    table would report a false failure. Jarvis only ever calls PutItem, so a
    resolvable credential is the right-sized readiness signal here.
    """
    import aws_sync
    if not aws_sync._BOTO3_AVAILABLE:
        return Check("AWS DynamoDB", WARN, "boto3 not installed — cloud sync disabled")
    try:
        import boto3
        from botocore.exceptions import BotoCoreError

        session = boto3.session.Session(
            region_name=aws_sync.AWS_REGION, profile_name=aws_sync.AWS_PROFILE
        )
        if session.get_credentials() is None:
            return Check(
                "AWS DynamoDB", WARN,
                f"no credentials for profile '{aws_sync.AWS_PROFILE}' — "
                "run: aws configure --profile jarvis",
            )
        return Check(
            "AWS DynamoDB", OK,
            f"credentials OK for {aws_sync.TABLE_NAME} @ {aws_sync.AWS_REGION} "
            "(PutItem-only policy; table not probed)",
        )
    except (BotoCoreError, Exception) as e:  # noqa: BLE001 — doctor must not crash
        return Check("AWS DynamoDB", WARN, f"could not resolve AWS credentials: {e}")


# Order matters only for display.
ALL_CHECKS = (
    check_python,
    check_tts,
    check_input,
    check_wake_word,
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
