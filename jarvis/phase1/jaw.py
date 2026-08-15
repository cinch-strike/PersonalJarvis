"""
Servo-driven jaw for the talking skull.
───────────────────────────────────────
Flaps a hobby servo (SG90) while the prop is speaking, so the jaw moves in time
with the voice. Driven by a background thread rather than audio amplitude: from
a couple of metres away a natural syllable-rate flap reads as talking, and it
needs no tap into the audio pipeline.

  speak() → jaw.start_talking() → ...TTS plays... → jaw.stop_talking()

Design notes:
  • Angles are configurable because the mechanism doesn't exist yet — closed/open
    get tuned once there's a real printed jaw to look at.
  • The servo is DETACHED when idle. A hobby servo told to hold a position buzzes
    and draws current continuously; detaching keeps the prop silent between
    visitors and avoids browning out the Pi.
  • Every failure path degrades to a no-op. A missing servo, missing gpiozero, or
    bad pin must never stop the skull from talking — the voice is the feature,
    the jaw is decoration.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Optional


class JawError(RuntimeError):
    """Raised only by the standalone test path; the runtime path degrades quietly."""


class Jaw:
    """A servo jaw. Safe to construct and call even with no hardware attached."""

    def __init__(
        self,
        pin: int = 18,
        closed_angle: float = 0.0,
        open_angle: float = 25.0,
        min_angle: float = -45.0,
        max_angle: float = 45.0,
        rate_hz: float = 6.0,
        enabled: bool = True,
    ) -> None:
        self.pin = pin
        self.closed_angle = closed_angle
        self.open_angle = open_angle
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.rate_hz = max(0.5, rate_hz)
        self.enabled = enabled
        self._servo = None
        self._thread: Optional[threading.Thread] = None
        self._talking = threading.Event()
        self._stop = threading.Event()
        self.error: Optional[str] = None

    # ─── hardware ────────────────────────────────────────────────────────────

    def _ensure_servo(self):
        """Create the servo on first use. Returns None if unavailable."""
        if self._servo is not None or not self.enabled or self.error:
            return self._servo
        try:
            from gpiozero import AngularServo

            self._servo = AngularServo(
                self.pin,
                min_angle=self.min_angle,
                max_angle=self.max_angle,
                # SG90 clones want a slightly wider pulse range than the default.
                min_pulse_width=0.0005,
                max_pulse_width=0.0025,
            )
        except Exception as e:  # noqa: BLE001 — jaw must never break speech
            self.error = str(e)
            self._servo = None
        return self._servo

    def _move_to(self, angle: float) -> None:
        servo = self._ensure_servo()
        if servo is None:
            return
        try:
            servo.angle = max(self.min_angle, min(self.max_angle, angle))
        except Exception as e:  # noqa: BLE001
            self.error = str(e)

    def _detach(self) -> None:
        """Stop driving the servo so it doesn't buzz while idle."""
        if self._servo is not None:
            try:
                self._servo.detach()
            except Exception:
                pass

    # ─── talking ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        """Flap while `_talking` is set; rest closed and detached otherwise."""
        while not self._stop.is_set():
            if not self._talking.wait(timeout=0.2):
                continue
            # Vary the swing and timing a little so it doesn't look mechanical.
            span = self.open_angle - self.closed_angle
            self._move_to(self.closed_angle + span * random.uniform(0.55, 1.0))
            time.sleep(random.uniform(0.6, 1.4) / (2 * self.rate_hz))
            if not self._talking.is_set():
                break
            self._move_to(self.closed_angle)
            time.sleep(random.uniform(0.6, 1.4) / (2 * self.rate_hz))
        self._move_to(self.closed_angle)
        time.sleep(0.15)          # let it arrive before we stop driving it
        self._detach()

    def start_talking(self) -> None:
        if not self.enabled:
            return
        self._stop.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        self._talking.set()

    def stop_talking(self) -> None:
        self._talking.clear()
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=1.0)

    def close(self) -> None:
        self.stop_talking()
        if self._servo is not None:
            try:
                self._servo.close()
            except Exception:
                pass
            self._servo = None


def build_jaw() -> Jaw:
    """Construct the jaw from config."""
    import config

    return Jaw(
        pin=config.SERVO_PIN,
        closed_angle=config.JAW_CLOSED_ANGLE,
        open_angle=config.JAW_OPEN_ANGLE,
        min_angle=config.SERVO_MIN_ANGLE,
        max_angle=config.SERVO_MAX_ANGLE,
        rate_hz=config.JAW_RATE_HZ,
        enabled=config.JAW_ENABLED,
    )


def self_test() -> int:
    """Standalone servo check — `python jarvis.py --test-jaw`.

    Sweeps to closed, to open, then flaps for a few seconds. Lets you prove the
    servo and wiring work (and dial in angles) before a jaw exists to attach.
    """
    import config

    jaw = build_jaw()
    print(f"\n🦴 Jaw test — GPIO {jaw.pin}")
    print(f"   closed={jaw.closed_angle}°  open={jaw.open_angle}°  "
          f"range={jaw.min_angle}..{jaw.max_angle}°\n")

    if jaw._ensure_servo() is None:
        print(f"   ❌ Could not open servo: {jaw.error}")
        print("      Install gpiozero + lgpio, and check JARVIS_SERVO_PIN.\n")
        return 1

    try:
        print("   → closed position"); jaw._move_to(jaw.closed_angle); time.sleep(1.5)
        print("   → open position");   jaw._move_to(jaw.open_angle);   time.sleep(1.5)
        print("   → closed position"); jaw._move_to(jaw.closed_angle); time.sleep(1.5)
        print("   → flapping for 5s (this is what 'talking' looks like)")
        jaw.start_talking(); time.sleep(5); jaw.stop_talking()
        print("\n   ✅ Done. Tune with JARVIS_JAW_CLOSED_ANGLE / "
              "JARVIS_JAW_OPEN_ANGLE / JARVIS_JAW_RATE_HZ.\n")
        return 0
    finally:
        jaw.close()
