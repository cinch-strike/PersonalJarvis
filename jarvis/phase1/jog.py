"""
Interactive jaw calibration — `jarvis.py --jog-jaw`.
────────────────────────────────────────────────────
Drive the servo one degree at a time with the arrow keys and mark the positions
that matter, so the config numbers come from the actual mounted linkage instead
of guesswork.

The servo is driven to the new angle, given a moment to get there, and then
released. That matters: a servo commanded to *hold* a position hunts around its
deadband, and a jaw attached to it amplifies that jitter into obvious chatter —
which is both distracting and hard to tell apart from a real fault. Between
moves it should be silent. Press 'h' if you do need it actively held.

Typical session:

    1. jog until the cable just takes up its slack   → mark  (jaw still open)
    2. keep going until the jaw is fully closed      → mark
    3. those two marks are your open and closed angles

⚠️ Direction depends on how the servo is mounted, so ↑ isn't guaranteed to be
counter-clockwise on your build. Press ↑ once and watch which way the spline
turns — if it's backwards, just use the other key. The numbers are what matter,
not the sign.
"""

from __future__ import annotations

import select
import sys
import time

# Terminals send arrows in one of two forms depending on whether they're in
# "application cursor key" mode: ESC [ A (normal) or ESC O A (application).
# Both are common over SSH, so accept either.
_ARROWS = {
    "[A": "up", "[B": "down", "[C": "right", "[D": "left",
    "OA": "up", "OB": "down", "OC": "right", "OD": "left",
}

# Letter fallbacks, so a terminal that mangles escape sequences can't block a
# calibration session. w/s and k/j (vim) both move fine.
# NB: no vim h/l here — 'h' is the hold toggle, and a movement key that also
# toggles hold would be a nasty surprise mid-calibration.
_LETTERS = {
    "w": "up", "s": "down", "k": "up", "j": "down",
    "d": "right", "a": "left",
    "+": "up", "-": "down",
}


def read_key(stream=None, timeout: float = 0.25) -> str:
    """Return a key name. Arrow keys arrive as a 3-byte escape sequence.

    The timeout separates a real arrow key from a bare Esc press — without it,
    Esc alone would block waiting for two bytes that never arrive.
    """
    stream = stream or sys.stdin
    ch = stream.read(1)
    if ch != "\x1b":
        return _LETTERS.get(ch, ch)
    try:
        ready, _, _ = select.select([stream], [], [], timeout)
        if not ready:
            return "esc"
    except (OSError, ValueError, AttributeError):
        # No real file descriptor (a pipe or an in-memory stream in tests) —
        # just read and let a short stream return "esc" on its own.
        pass
    return _ARROWS.get(stream.read(2), "esc")


def input_ready(timeout: float, stream=None) -> bool:
    """True if a keypress is waiting. Lets the loop idle-release the servo."""
    stream = stream or sys.stdin
    try:
        ready, _, _ = select.select([stream], [], [], timeout)
        return bool(ready)
    except (OSError, ValueError, AttributeError):
        return True      # can't poll — treat as ready and just block on read


def clamp(angle: float, low: float, high: float) -> tuple:
    """Clamp, and report whether we hit a limit — so the UI can say so."""
    if angle < low:
        return low, True
    if angle > high:
        return high, True
    return angle, False


def _render(angle: float, limited: bool, marks: list, driving: bool = False) -> str:
    state = "holding" if driving else "quiet  "
    bar = "  ⚠️ at limit" if limited else ""
    tail = f"   marks: {', '.join(f'{m:g}°' for m in marks)}" if marks else ""
    return f"\r   angle: {angle:>7.1f}°  [{state}]{bar}{tail}          "


def run(step: float = 1.0, coarse: float = 5.0, settle_s: float = 1.0) -> int:
    import config
    import jaw as jaw_module

    try:
        import termios
        import tty
    except ImportError:
        print("\n❌ --jog-jaw needs a Unix terminal.\n")
        return 1

    if not sys.stdin.isatty():
        print("\n❌ --jog-jaw needs an interactive terminal (run it over SSH "
              "directly, not through a pipe).\n")
        return 1

    jaw = jaw_module.build_jaw()
    if jaw._ensure_servo() is None:
        print(f"\n❌ Could not open servo: {jaw.error}")
        print("   Is the service holding it? sudo systemctl stop jarvis\n")
        return 1

    print(f"\n🦴 Jaw jog — GPIO {jaw.pin}   range {jaw.min_angle}..{jaw.max_angle}°")
    print(f"""
   ↑ / ↓    move {step:g}°          → / ←   move {coarse:g}°
   (w / s)  same, if arrows don't work in your terminal
   m        mark this angle    h       toggle constant hold
   r        release now        q       quit

   The servo stops driving {settle_s:g}s after each move, so it sits silent
   instead of hunting. Press h if you need it actively held.

   ⚠️ The first move attaches the servo and may snap it toward 0°.
      Keep a hand near the jaw.
""")

    angle = float(config.JAW_CLOSED_ANGLE)
    marks: list = []
    attached = False
    driving = False
    hold_always = False
    last_move = 0.0
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        sys.stdout.write(_render(angle, False, marks, driving))
        sys.stdout.flush()

        while True:
            # Idle: once the servo has had time to reach the angle, stop
            # pulsing it. A servo told to hold hunts around its deadband, and
            # the jaw turns that tiny jitter into visible, audible chatter.
            if not input_ready(0.1):
                if (driving and not hold_always
                        and time.time() - last_move >= settle_s):
                    jaw._detach()
                    driving = False
                    sys.stdout.write(_render(angle, False, marks, driving))
                    sys.stdout.flush()
                continue

            key = read_key()
            if key in ("q", "\x03"):          # q or Ctrl-C
                break

            delta = {"up": step, "down": -step,
                     "right": coarse, "left": -coarse}.get(key)

            if delta is not None:
                angle, limited = clamp(angle + delta, jaw.min_angle, jaw.max_angle)
                jaw._move_to(angle)
                attached = driving = True
                last_move = time.time()
            elif key == "m":
                marks.append(angle)
                limited = False
                sys.stdout.write(f"\r   ✅ marked {angle:g}°" + " " * 40 + "\n")
            elif key == "h":
                hold_always = not hold_always
                limited = False
                if hold_always:
                    jaw._move_to(angle)
                    attached = driving = True
                state = "ON (will hunt)" if hold_always else "OFF (silent at rest)"
                sys.stdout.write(f"\r   constant hold: {state}" + " " * 25 + "\n")
            elif key == "r":
                jaw._detach()                  # stop pulsing; jaw goes slack
                driving = False
                limited = False
                sys.stdout.write("\r   (released — next move re-attaches)"
                                 + " " * 20 + "\n")
            else:
                # Say so rather than ignoring it — a key that silently does
                # nothing reads as a dead servo.
                shown = repr(key).strip("'")
                sys.stdout.write(f"\r   (unrecognised key: {shown} — use w/s "
                                 f"if arrows don't work)" + " " * 10 + "\n")
                sys.stdout.write(_render(angle, False, marks))
                sys.stdout.flush()
                continue

            sys.stdout.write(_render(angle, limited, marks, driving))
            sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        jaw.close()

    print("\n")
    if marks:
        print("   Marked angles: " + ", ".join(f"{m:g}°" for m in marks))
        lo, hi = min(marks), max(marks)
        print(f"\n   Suggested config:")
        print(f"     JARVIS_JAW_CLOSED_ANGLE={hi:g}")
        print(f"     JARVIS_JAW_OPEN_ANGLE={lo:g}")
        print("\n   (swap those two if your closed position was the lower number)")
    else:
        print("   No marks taken.")

    if attached:
        print("\n   Servo released — the jaw will hang slack again.")
    print()
    return 0
