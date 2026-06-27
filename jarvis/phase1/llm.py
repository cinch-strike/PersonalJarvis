"""
LLM backends for Jarvis.
────────────────────────
Abstracts *which model answers* so Jarvis can run online (Claude) or fully
offline (Ollama on the Pi) — the Phase 3.5 goal.

  claude   Anthropic Claude (cloud, default model claude-opus-4-8).
  ollama   Local model via the Ollama HTTP API (offline, no API key).
  auto     Try Claude first; fall back to Ollama if Claude is unreachable.

Select via JARVIS_LLM_BACKEND (default "auto"). Backends take a system prompt
plus the running message history and return reply text. No backend opens a
network connection at construction time, so this module is import-safe and the
selected backend can be reported by `jarvis.py --check` without making a call.

On a Mac with ANTHROPIC_API_KEY set, "auto" behaves exactly like Phase 1: it
uses Claude.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import List

import config


class LLMError(RuntimeError):
    """Raised when an LLM backend can't be selected or fails to respond."""


Message = dict  # {"role": "user"|"assistant", "content": str}


class LLMBackend(ABC):
    """A chat backend. `available()` is a cheap, network-light reachability hint;
    `generate()` does the real call and raises LLMError on failure."""

    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Best-effort, fast check that this backend is usable right now."""

    @abstractmethod
    def generate(
        self, system: str, messages: List[Message], max_tokens: int, tools=None
    ) -> str:
        """Return the assistant reply for `messages` under `system`.

        `tools` is an optional tools.ToolRegistry; backends that support
        function calling (Claude) will use it, others ignore it.
        """


class ClaudeBackend(LLMBackend):
    """Anthropic Claude. Lazily creates the SDK client on first use so a missing
    API key degrades gracefully (in `auto`) instead of crashing at startup."""

    name = "claude"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or config.CLAUDE_MODEL
        self._client = None

    def available(self) -> bool:
        # Cheap check: the SDK needs an API key. Real network errors surface in
        # generate() and trigger fallback there.
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic()
            except Exception as e:  # missing key, import error, etc.
                raise LLMError(f"Claude client unavailable: {e}") from e
        return self._client

    def generate(
        self, system: str, messages: List[Message], max_tokens: int, tools=None
    ) -> str:
        client = self._get_client()
        schemas = tools.anthropic_schemas() if tools else None
        # Work on a copy so the intermediate tool turns aren't persisted to the
        # caller's conversation history / memory (only the final reply is).
        convo = list(messages)

        for _ in range(6):  # cap tool rounds to avoid runaway loops
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": convo,
            }
            if schemas:
                kwargs["tools"] = schemas
            try:
                response = client.messages.create(**kwargs)
            except Exception as e:
                raise LLMError(f"Claude request failed: {e}") from e

            if response.stop_reason != "tool_use":
                return "".join(
                    b.text for b in response.content
                    if getattr(b, "type", None) == "text"
                ).strip()

            # Claude asked to call one or more tools — run them and feed back.
            convo.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    print(f"  🔧 {block.name}({json.dumps(block.input)})")
                    output = tools.run(block.name, block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })
            convo.append({"role": "user", "content": results})

        raise LLMError("tool loop did not converge after several rounds")


class OllamaBackend(LLMBackend):
    """Local model via the Ollama HTTP API (offline). Uses stdlib urllib so it
    adds no Python dependency — Ollama itself is a system install on the Pi."""

    name = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        self.model = model or config.OLLAMA_MODEL
        self.host = (host or config.OLLAMA_HOST).rstrip("/")

    def _host_port(self) -> tuple[str, int]:
        parsed = urllib.parse.urlparse(self.host)
        return parsed.hostname or "localhost", parsed.port or 11434

    def available(self) -> bool:
        host, port = self._host_port()
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False

    def generate(
        self, system: str, messages: List[Message], max_tokens: int, tools=None
    ) -> str:
        # Local models here don't do function calling; tools are ignored.
        payload = {
            "model": self.model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, *messages],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            raise LLMError(f"Ollama request failed ({self.host}): {e}") from e

        try:
            return body["message"]["content"]
        except (KeyError, TypeError) as e:
            raise LLMError(f"Unexpected Ollama response: {body!r}") from e


class FallbackLLM(LLMBackend):
    """Tries each backend in priority order per call — so a Claude/network
    outage mid-session transparently drops to Ollama (and vice versa)."""

    def __init__(self, backends: List[LLMBackend]) -> None:
        if not backends:
            raise LLMError("FallbackLLM needs at least one backend.")
        self.backends = backends
        self.name = "auto(" + "→".join(b.name for b in backends) + ")"

    def available(self) -> bool:
        return any(b.available() for b in self.backends)

    def generate(
        self, system: str, messages: List[Message], max_tokens: int, tools=None
    ) -> str:
        errors = []
        for backend in self.backends:
            if not backend.available():
                errors.append(f"{backend.name}: not available")
                continue
            try:
                return backend.generate(system, messages, max_tokens, tools=tools)
            except LLMError as e:
                errors.append(str(e))
        raise LLMError(
            "All LLM backends failed:\n   " + "\n   ".join(errors)
        )


def select_llm_backend(mode: str | None = None) -> LLMBackend:
    """Pick and instantiate the LLM backend named by `mode`.

      auto    → FallbackLLM([Claude, Ollama])  (default)
      claude  → ClaudeBackend
      ollama  → OllamaBackend

    Raises LLMError for an unknown mode.
    """
    key = (mode if mode is not None else config.LLM_BACKEND or "auto").strip().lower()

    if key == "auto":
        return FallbackLLM([ClaudeBackend(), OllamaBackend()])
    if key == "claude":
        return ClaudeBackend()
    if key == "ollama":
        return OllamaBackend()

    raise LLMError(
        f"Unknown JARVIS_LLM_BACKEND '{mode}'. Valid values: auto, claude, ollama."
    )
