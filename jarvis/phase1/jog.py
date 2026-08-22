"""
Interactive jaw calibration — `jarvis.py --jog-jaw`.
────────────────────────────────────────────────────
Drive the servo one degree at a time with the arrow keys and mark the positions
that matter, so the config numbers come from the actual mounted linkage instead
of guesswork.

Unlike --test-jaw, this **holds** position between keypresses. The normal jaw
detaches when idle (a held servo buzzes and draws current all night), but here
you need it to stay put while you look at the jaw and decide.

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

# Terminals send arrows in one of two forms depending on whether they're in
# "application cursor key" mode: ESC [ A (normal) or ESC O A (application).
# Both are common over SSH, so accept either.
_ARROWS = {
    "[A": "up", "[B": "down", "[C": "right", "[D": "left",
    "OA": "up", "OB": "down", "OC": "right", "OD": "left",
}

# Letter fallbacks, so a terminal that mangles escape sequences can't block a
# calibration session. w/s and k/j (vim) both move fine.
_LETTERS = {
    "w": "up", "s": "down", "k": "up", "j": "down",
    "d": "right", "a": "left", "l": "right", "h": "left",
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


def clamp(angle: float, low: float, high: float) -> tuple:
    """Clamp, and report whether we hit a limit — so the UI can say so."""
    if angle < low:
        return low, True
    if angle > high:
        return high, True
    return angle, False


def _render(angle: float, limited: bool, marks: list) -> str:
    bar = "  ⚠️ at limit" if limited else ""
    tail = f"   marks: {', '.join(f'{m:g}°' for m in marks)}" if marks else ""
    return f"\r   angle: {angle:>7.1f}°{bar}{tail}          "


def run(step: float = 1.0, coarse: float = 5.0) -> int:
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
   m        mark this angle    r       release (jaw goes slack)
   q        quit

   ⚠️ The first move attaches the servo and may snap it toward 0°.
      Keep a hand near the jaw.
""")

    angle = float(config.JAW_CLOSED_ANGLE)
    marks: list = []
    attached = False
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        sys.stdout.write(_render(angle, False, marks))
        sys.stdout.flush()

        while True:
            key = read_key()
            if key in ("q", "\x03"):          # q or Ctrl-C
                break

            delta = {"up": step, "down": -step,
                     "right": coarse, "left": -coarse}.get(key)

            if delta is not None:
                angle, limited = clamp(angle + delta, jaw.min_angle, jaw.max_angle)
                jaw._move_to(angle)
                attached = True
            elif key == "m":
                marks.append(angle)
                limited = False
                sys.stdout.write(f"\r   ✅ marked {angle:g}°" + " " * 40 + "\n")
            elif key == "r":
                jaw.close()                    # detach: jaw falls slack
                attached = False
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

            sys.stdout.write(_render(angle, limited, marks))
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
