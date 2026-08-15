"""
Looping background ambience for the prop.
─────────────────────────────────────────
Plays a spooky loop (graveyard drone, wind, distant bells) while the prop is
idle, and stops it the moment someone approaches.

Why it stops: the mic and speaker share a room. Music playing under a
conversation wrecks Whisper's accuracy and risks the prop hearing itself — the
feedback problem we already fixed once. Silence while listening is not a
compromise, it's the point: the drone draws people in, and the sudden quiet when
the skull notices them is the effect.

Loops by re-spawning `aplay` rather than adding a dependency, since aplay is
already how the rest of the prop plays audio. Every failure path is a no-op:
missing file, missing aplay, or a bad device must never stop the skull talking.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import Optional


class Ambience:
    """A looping background sound. Safe to construct and call with no file set."""

    def __init__(
        self,
        path: str = "",
        device: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        self.path = path
        self.device = device
        self.enabled = bool(enabled and path)
        self.error: Optional[str] = None
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def available(self) -> bool:
        """True if we could actually play something."""
        if not self.enabled:
            return False
        if not os.path.exists(self.path):
            self.error = f"ambience file not found: {self.path}"
            return False
        if not shutil.which("aplay"):
            self.error = "aplay not installed (sudo apt install alsa-utils)"
            return False
        return True

    def _cmd(self) -> list:
        cmd = ["aplay", "-q"]
        if self.device:
            cmd += ["-D", self.device]
        cmd.append(self.path)
        return cmd

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._proc = subprocess.Popen(
                    self._cmd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self._proc.wait()
            except Exception as e:  # noqa: BLE001 — ambience is decoration
                self.error = str(e)
                return
            # A file that fails instantly would spin this loop hot; the stop
            # event doubles as the pacing wait.
            if self._stop.wait(timeout=0.3):
                return

    def start(self) -> None:
        if not self.available():
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Silence immediately — called before the prop listens."""
        self._stop.set()
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=1.0)


def build_ambience() -> Ambience:
    """Construct from config."""
    import config

    return Ambience(
        path=config.AMBIENCE_FILE,
        device=config.AUDIO_OUTPUT,
        enabled=config.AMBIENCE_ENABLED,
    )
