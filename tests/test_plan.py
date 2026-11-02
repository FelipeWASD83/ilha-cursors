"""The step plan of every .ani: within what Windows accepts and shaped as intended."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate import HOLD, MAX_STEPS, ani_plan  # noqa: E402
from ilhacursors.shapes import CURSORS, ease  # noqa: E402


class PlanTests(unittest.TestCase):
    def test_steps_stay_under_the_windows_limit(self):
        for c in CURSORS:
            if c.is_ani:
                frames, sequence, rates = ani_plan(c)
                self.assertLess(len(sequence), 65536, c.file)
                self.assertLessEqual(len(sequence), MAX_STEPS, c.file)
                self.assertEqual(len(sequence), len(rates), c.file)
                self.assertTrue(all(0 <= i < len(frames) for i in sequence), c.file)
                self.assertTrue(all(r >= 1 for r in rates), c.file)  # 0 makes Windows refuse the file

    def test_still_cursors_play_the_intro_once_then_hold(self):
        for c in CURSORS:
            if c.intro and not c.animated:
                frames, sequence, rates = ani_plan(c)
                self.assertEqual(sequence, list(range(c.intro_frames + 1)), c.file)
                self.assertEqual(rates[-1], HOLD, c.file)
                self.assertEqual(rates[:-1], [1] * c.intro_frames, c.file)

    def test_loops_follow_their_intro(self):
        for c in CURSORS:
            if c.animated:
                frames, sequence, rates = ani_plan(c)
                n = c.intro_frames
                self.assertEqual(len(frames), n + c.frames, c.file)
                self.assertEqual(sequence[n:n + c.frames], list(range(n, n + c.frames)), c.file)
                self.assertGreater(len(sequence) - n, 100 * c.frames, c.file)  # minutes of loop before the intro returns

    def test_the_arrow_stays_a_still_cur(self):
        arrow = next(c for c in CURSORS if c.role == "Arrow")
        self.assertFalse(arrow.is_ani)

    def test_spring_starts_at_zero_and_settles_at_one(self):
        self.assertEqual(ease(0.0), 0.0)
        self.assertAlmostEqual(ease(1.0), 1.0)
        self.assertGreater(max(ease(i / 100) for i in range(101)), 1.0)  # it overshoots like the island


if __name__ == "__main__":
    unittest.main()
