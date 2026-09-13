"""Speed OCR jumps that a car cannot make are not kept."""

import unittest

from src.lap_detector import LapDetector


def _detector() -> LapDetector:
    detector = LapDetector.__new__(LapDetector)
    detector._speed_history = []
    detector._last_valid_speed = None
    detector._max_speed_jump = 25
    detector._speed_regime_frames = 8
    detector._min_crash_fraction = 0.2
    detector._pending_speed = None
    detector._pending_speed_count = 0
    detector._history_size = 15
    detector._tesserocr_api = None
    return detector


class TestSpeedReading(unittest.TestCase):
    def test_dropped_leading_digit_does_not_stick(self):
        """113 read as 13 for many frames must stay near 113."""
        detector = _detector()
        for _ in range(3):
            self.assertEqual(detector._accept_speed_reading(113), 113)

        for _ in range(40):
            self.assertEqual(detector._accept_speed_reading(13), 113)

        self.assertEqual(detector._accept_speed_reading(4), 113)
        # A real nearby speed is kept, but the median still holds the
        # previous value until the new one is the majority of the window.
        self.assertEqual(detector._accept_speed_reading(125), 113)
        for _ in range(8):
            detector._accept_speed_reading(125)
        self.assertEqual(detector._accept_speed_reading(125), 125)

    def test_small_changes_are_kept(self):
        detector = _detector()
        self.assertEqual(detector._accept_speed_reading(100), 100)
        self.assertEqual(detector._accept_speed_reading(108), 104)
        self.assertEqual(detector._accept_speed_reading(110), 108)

    def test_implausible_value_is_not_the_first_reading(self):
        """Out of range and empty reads do not invent a speed."""
        detector = _detector()
        self.assertIsNone(detector._accept_speed_reading(None))
        self.assertIsNone(detector._accept_speed_reading(1465))
        self.assertEqual(detector._accept_speed_reading(90), 90)
        self.assertEqual(detector._accept_speed_reading(500), 90)

    def test_sustained_crash_replaces_the_held_speed(self):
        """A real drop that is not a missing digit is accepted after it repeats."""
        detector = _detector()
        self.assertEqual(detector._accept_speed_reading(180), 180)
        for _ in range(7):
            self.assertEqual(detector._accept_speed_reading(40), 180)
        self.assertEqual(detector._accept_speed_reading(40), 40)

    def test_collapsed_reading_is_not_a_crash(self):
        """168 read as 10 for many frames must stay at 168.

        The 1 merges into the next digit, so the wrong value is stable.
        It is a small fraction of the last speed, not a wall.
        """
        detector = _detector()
        for _ in range(3):
            self.assertEqual(detector._accept_speed_reading(168), 168)
        for _ in range(20):
            self.assertEqual(detector._accept_speed_reading(10), 168)
            self.assertEqual(detector._accept_speed_reading(1), 168)
        self.assertEqual(detector._accept_speed_reading(168), 168)


if __name__ == '__main__':
    unittest.main()
