"""
Unit tests for the ambience player's stop contract.

The speaker is a single-opener device, so one stray `aplay` left running mutes
the prop completely: the speech player gets "Device or resource busy" and the
line is lost with only a log entry to show for it. That happened in the field on
12 Sep — the graveyard loop kept playing and the skull went silent.

These are deterministic on purpose. An earlier version drove real threads and
slept, which was flaky AND passed against the broken code, so it guarded
nothing.
"""

import unittest
from unittest import mock

import ambience


class _FakeProc:
    def __init__(self):
        self.terminated = self.killed = False
        self._alive = True

    def wait(self, timeout=None):
        self._alive = False
        return 0

    def terminate(self):
        self.terminated = True
        self._alive = False

    def kill(self):
        self.killed = True
        self._alive = False

    def poll(self):
        return None if self._alive else 0


class LoopRespawnTests(unittest.TestCase):
    """The actual bug: the loop spawning a replacement after stop() had already
    walked past, leaving a player nothing would ever kill."""

    def setUp(self):
        self.amb = ambience.Ambience(path="/tmp/graveyard.wav", enabled=True)
        self.spawns = 0

    def _popen(self, *a, **kw):
        self.spawns += 1
        return _FakeProc()

    def test_loop_does_not_spawn_once_stop_is_set(self):
        self.amb._stop.set()
        with mock.patch.object(ambience.subprocess, "Popen", side_effect=self._popen):
            self.amb._loop()
        self.assertEqual(self.spawns, 0, "loop spawned a player after stop()")

    def test_loop_rechecks_the_flag_while_holding_the_lock(self):
        # The actual race: the flag gets set after the while-check but before
        # the spawn. Re-checking under the lock is what makes that safe, so the
        # lock is swapped for one that sets the flag as it is acquired.
        amb = self.amb

        class _LockThatStops:
            def __enter__(self):
                amb._stop.set()
                return self

            def __exit__(self, *a):
                return False

        amb._lock = _LockThatStops()
        with mock.patch.object(ambience.subprocess, "Popen", side_effect=self._popen):
            amb._loop()
        self.assertEqual(self.spawns, 0, "spawned despite stop() during the lock")


class StopTests(unittest.TestCase):
    def setUp(self):
        self.amb = ambience.Ambience(path="/tmp/graveyard.wav", enabled=True)

    def test_stop_terminates_the_running_player(self):
        proc = _FakeProc()
        self.amb._proc = proc
        with mock.patch.object(ambience.Ambience, "_kill_strays"):
            self.amb.stop()
        self.assertTrue(proc.terminated)
        self.assertIsNone(self.amb._proc)

    def test_stop_kills_a_player_that_ignores_terminate(self):
        proc = _FakeProc()
        proc.terminate = lambda: setattr(proc, "terminated", True)   # stays alive
        proc.wait = lambda timeout=None: (_ for _ in ()).throw(Exception("still running"))
        self.amb._proc = proc
        with mock.patch.object(ambience.Ambience, "_kill_strays"):
            self.amb.stop()
        self.assertTrue(proc.killed, "a player ignoring terminate must be killed")

    def test_stop_sweeps_for_strays(self):
        # The backstop for the race, since the race itself is hard to force.
        with mock.patch.object(ambience.Ambience, "_kill_strays") as sweep:
            self.amb.stop()
        sweep.assert_called_once()

    def test_stray_sweep_matches_only_our_own_file(self):
        # Must never be able to kill the speech player or anything else.
        with mock.patch.object(ambience.shutil, "which", return_value="/usr/bin/pkill"), \
             mock.patch.object(ambience.subprocess, "run") as run:
            self.amb._kill_strays()
        pattern = run.call_args[0][0][-1]
        self.assertIn("graveyard", pattern)
        self.assertTrue(pattern.startswith("aplay"), pattern)

    def test_stop_before_start_is_harmless(self):
        ambience.Ambience(path="/tmp/x.wav").stop()

    def test_stop_is_safe_to_call_twice(self):
        self.amb.stop()
        self.amb.stop()


if __name__ == "__main__":
    unittest.main()
