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
import re
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
        # Guards _proc so stop() and the loop cannot race over spawning/killing.
        self._lock = threading.Lock()

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
                # ⚠️ Spawn under the lock and re-check the flag first. Without
                # this, stop() could terminate the running aplay and the loop
                # would immediately start another one — which then held the
                # speaker, so Vlad's own aplay got "Device or resource busy" and
                # his line never played. From outside: the graveyard loop
                # carries on and the skull has gone mute.
                with self._lock:
                    if self._stop.is_set():
                        return
                    self._proc = subprocess.Popen(
                        self._cmd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                proc = self._proc
                if proc is not None:
                    proc.wait()
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
        """Silence immediately — called before the prop speaks or listens.

        ⚠️ Must leave NO aplay running. The speaker is a single-opener device,
        so one stray ambience process is enough to mute the prop entirely: the
        speech aplay gets "Device or resource busy" and the line is lost with
        only a log entry to show for it.
        """
        self._stop.set()
        # Take the lock so the loop cannot be midway through spawning a
        # replacement while we are killing the current one.
        with self._lock:
            proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                pass
            if proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)
        # Belt and braces: if the thread somehow outlived the join, it may have
        # spawned one more. Kill whatever is there now.
        with self._lock:
            stray, self._proc = self._proc, None
        if stray is not None:
            try:
                stray.kill()
            except Exception:
                pass
        self._kill_strays()

    def _kill_strays(self) -> None:
        """Kill any aplay still holding OUR file, whatever spawned it.

        ⚠️ Deliberately not elegant. The race this backs up is narrow and hard
        to reproduce, and the failure it prevents is the worst one available:
        a single surviving aplay holds the speaker, the prop's own playback
        gets "Device or resource busy", and the skull goes mute while the
        graveyard loop plays on. Silence with a log line is worse than a
        clumsy pkill.

        Matched on the ambience path, so it can only ever hit our own player —
        never the speech aplay, never anything else on the system.
        """
        if not self.path or not shutil.which("pkill"):
            return
        try:
            subprocess.run(["pkill", "-f", f"aplay.*{re.escape(self.path)}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=2)
        except Exception:  # noqa: BLE001 — ambience is decoration, never fatal
            pass


def build_ambience() -> Ambience:
    """Construct from config."""
    import config

    return Ambience(
        path=config.AMBIENCE_FILE,
        device=config.AUDIO_OUTPUT,
        enabled=config.AMBIENCE_ENABLED,
    )
