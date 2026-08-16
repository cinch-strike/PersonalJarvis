"""
LED eyes for the talking skull.
───────────────────────────────
Three states, because the *change* in brightness is what reads as "it noticed
you" — far more than raw brightness:

    idle      dim, steady          waiting, unsettling
    alert     brighter             someone has just walked up
    talking   pulsing, brightest   in time with speech

Driven by hardware-ish PWM via gpiozero's PWMLED, so brightness is continuous
rather than just on/off. Both eyes share one GPIO — they'd always match anyway,
and two red LEDs at ~4mA each stay well under the Pi's ~16mA per-pin limit.

Like jaw.py, every failure path degrades to a no-op: missing gpiozero, a bad
pin, or no LEDs attached must never stop the skull talking. The eyes are
decoration; the voice is the feature.

⚠️ Each LED needs a series resistor (330Ω or 470Ω). An LED's current rises
exponentially past its forward voltage, so without one it self-destructs and can
take the GPIO pin with it.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Optional


class Eyes:
    """PWM-driven LED eyes. Safe to construct and call with no hardware."""

    def __init__(
        self,
        pin: int = 23,
        idle_level: float = 0.15,
        alert_level: float = 0.6,
        talk_level: float = 1.0,
        rate_hz: float = 6.0,
        enabled: bool = True,
    ) -> None:
        self.pin = pin
        self.idle_level = self._clamp(idle_level)
        self.alert_level = self._clamp(alert_level)
        self.talk_level = self._clamp(talk_level)
        self.rate_hz = max(0.5, rate_hz)
        self.enabled = enabled
        self._led = None
        self._thread: Optional[threading.Thread] = None
        self._talking = threading.Event()
        self._stop = threading.Event()
        self.error: Optional[str] = None

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    # ─── hardware ────────────────────────────────────────────────────────────

    def _ensure_led(self):
        if self._led is not None or not self.enabled or self.error:
            return self._led
        try:
            from gpiozero import PWMLED

            self._led = PWMLED(self.pin)
        except Exception as e:  # noqa: BLE001 — eyes must never break speech
            self.error = str(e)
            self._led = None
        return self._led

    def _set(self, level: float) -> None:
        led = self._ensure_led()
        if led is None:
            return
        try:
            led.value = self._clamp(level)
        except Exception as e:  # noqa: BLE001
            self.error = str(e)

    # ─── states ──────────────────────────────────────────────────────────────

    def idle(self) -> None:
        """Dim steady glow — the resting state."""
        self.stop_talking()
        self._set(self.idle_level)

    def alert(self) -> None:
        """Brighten — someone has just been detected."""
        self.stop_talking()
        self._set(self.alert_level)

    def _pulse(self) -> None:
        """Flicker between alert and talk level while speaking."""
        while not self._stop.is_set() and self._talking.is_set():
            self._set(random.uniform(self.alert_level, self.talk_level))
            # Slightly irregular so it looks alive rather than mechanical.
            time.sleep(random.uniform(0.6, 1.4) / (2 * self.rate_hz))
        self._set(self.alert_level)

    def start_talking(self) -> None:
        if not self.enabled:
            return
        self._stop.clear()
        self._talking.set()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._pulse, daemon=True)
            self._thread.start()

    def stop_talking(self) -> None:
        self._talking.clear()
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=1.0)

    def close(self) -> None:
        self.stop_talking()
        if self._led is not None:
            try:
                self._led.off()
                self._led.close()
            except Exception:
                pass
            self._led = None


def build_eyes() -> Eyes:
    """Construct from config."""
    import config

    return Eyes(
        pin=config.EYES_PIN,
        idle_level=config.EYES_IDLE,
        alert_level=config.EYES_ALERT,
        talk_level=config.EYES_TALK,
        rate_hz=config.JAW_RATE_HZ,      # match the jaw so they move together
        enabled=config.EYES_ENABLED,
    )


def self_test() -> int:
    """Standalone LED check — `python jarvis.py --test-eyes`."""
    import config

    eyes = build_eyes()
    print(f"\n👁  Eye test — GPIO {eyes.pin}")
    print(f"   idle={eyes.idle_level}  alert={eyes.alert_level}  talk={eyes.talk_level}\n")

    if eyes._ensure_led() is None:
        print(f"   ❌ Could not open LEDs: {eyes.error}")
        print("      Install gpiozero + lgpio, and check JARVIS_EYES_PIN.\n")
        return 1

    try:
        print("   → off");            eyes._set(0);    time.sleep(1.5)
        print("   → idle (dim)");     eyes.idle();     time.sleep(2.5)
        print("   → alert (brighter)"); eyes.alert();  time.sleep(2.5)
        print("   → talking (pulsing) for 5s")
        eyes.start_talking(); time.sleep(5); eyes.stop_talking()
        print("   → back to idle");   eyes.idle();     time.sleep(2)
        print("\n   ✅ Done. Tune with JARVIS_EYES_IDLE / _ALERT / _TALK (0-1).\n")
        return 0
    finally:
        eyes.close()
