"""Bar orientation comes from the ROI profile, not a hardcoded direction."""

import unittest

import numpy as np

from src.telemetry_extractor import TelemetryExtractor


def _green_from_bottom(height: int, width: int, filled_rows: int) -> np.ndarray:
    """BGR image with a solid green fill rising from the bottom."""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    if filled_rows > 0:
        image[height - filled_rows :, :] = (0, 255, 0)
    return image


class TestBarOrientation(unittest.TestCase):
    def test_missing_orientation_defaults_to_horizontal(self):
        extractor = TelemetryExtractor({'throttle': {'x': 1}, 'brake': {}})
        self.assertEqual(extractor.throttle_orientation, 'horizontal')
        self.assertEqual(extractor.brake_orientation, 'horizontal')

    def test_profile_orientation_is_read(self):
        extractor = TelemetryExtractor({
            'throttle': {'orientation': 'vertical'},
            'brake': {'orientation': 'Vertical'},
        })
        self.assertEqual(extractor.throttle_orientation, 'vertical')
        self.assertEqual(extractor.brake_orientation, 'vertical')

    def test_invalid_orientation_raises(self):
        with self.assertRaises(ValueError):
            TelemetryExtractor({'throttle': {'orientation': 'diagonal'}})

    def test_vertical_fill_is_not_reported_as_full_when_measured_across(self):
        """A bar that is green only in the bottom 40% must not read as 100%.

        Horizontal measurement sees each colored row as fully filled, which
        is the bug on Assetto Corsa's 8px-wide pedal bars.
        """
        height, width, filled_rows = 80, 8, 32
        throttle = _green_from_bottom(height, width, filled_rows)
        brake = np.zeros_like(throttle)

        horizontal = TelemetryExtractor({
            'throttle': {'orientation': 'horizontal'},
            'brake': {'orientation': 'horizontal'},
        })
        vertical = TelemetryExtractor({
            'throttle': {'orientation': 'vertical'},
            'brake': {'orientation': 'vertical'},
        })

        across = horizontal.extract_frame_telemetry({
            'throttle': throttle,
            'brake': brake,
        })
        up = vertical.extract_frame_telemetry({
            'throttle': throttle,
            'brake': brake,
        })

        self.assertEqual(across['throttle'], 100.0)
        self.assertAlmostEqual(up['throttle'], 40.0)
        self.assertEqual(across['brake'], 0.0)
        self.assertEqual(up['brake'], 0.0)
        self.assertEqual(up['steering'], 0.0)


if __name__ == '__main__':
    unittest.main()
