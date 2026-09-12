"""Bar orientation comes from the ROI profile, not a hardcoded direction."""

import unittest

import numpy as np
import yaml

from src.telemetry_extractor import TelemetryExtractor
from src.video_processor import VideoProcessor


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


    def test_missing_steering_roi_is_not_required(self):
        profile = {
            'throttle': {'x': 0, 'y': 0, 'width': 8, 'height': 80},
            'brake': {'x': 10, 'y': 0, 'width': 8, 'height': 80},
        }
        processor = VideoProcessor('unused.mp4', profile)
        frame = np.zeros((100, 40, 3), dtype=np.uint8)
        rois = processor.frame_rois(frame)
        self.assertEqual(set(rois), {'throttle', 'brake'})
        self.assertEqual(rois['throttle'].shape, (80, 8, 3))


    def test_ac_profile_uses_vertical_bars_and_omits_steering(self):
        with open('config/roi_config.yaml') as config_file:
            profiles = yaml.safe_load(config_file)

        ac = profiles['assetto_corsa_1080p']
        self.assertEqual(ac['throttle']['orientation'], 'vertical')
        self.assertEqual(ac['brake']['orientation'], 'vertical')
        self.assertNotIn('steering', ac)
        self.assertNotIn('track_map', ac)

        acc = profiles['my_ps5_1080p']
        self.assertEqual(acc['throttle']['orientation'], 'horizontal')
        self.assertIn('steering', acc)


if __name__ == '__main__':
    unittest.main()
