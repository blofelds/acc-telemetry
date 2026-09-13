"""Bar orientation comes from the ROI profile, not a hardcoded direction."""

import unittest

import numpy as np
import yaml

from src.telemetry_extractor import TelemetryExtractor
from src.video_processor import VideoProcessor
from src.web.services.processing import VideoProcessingService


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

    def test_vertical_bar_ignores_color_that_is_not_anchored_at_the_bottom(self):
        """Car interior showing through an empty bar must not read as fill.

        The empty pedal is transparent. A red dashboard glyph in the middle
        of the crop used to set the fill line, which stuck brake near 64%.
        """
        height, width = 80, 8
        brake = np.zeros((height, width, 3), dtype=np.uint8)
        brake[26:40, :] = (0, 0, 255)
        extractor = TelemetryExtractor({
            'throttle': {'orientation': 'vertical'},
            'brake': {'orientation': 'vertical'},
        })

        reading = extractor.extract_frame_telemetry({
            'throttle': np.zeros_like(brake),
            'brake': brake,
        })

        self.assertEqual(reading['brake'], 0.0)

    def test_vertical_fill_stops_at_a_gap_above_the_pedal(self):
        """A blob above the fill must not raise the reading.

        A one-row hole inside the fill is compression noise and still
        counts. A larger gap is the end of the pedal.
        """
        height, width = 80, 8
        brake = np.zeros((height, width, 3), dtype=np.uint8)
        brake[48:, :] = (0, 0, 255)
        brake[50, :] = 0
        brake[20:28, :] = (0, 0, 255)
        extractor = TelemetryExtractor({
            'throttle': {'orientation': 'vertical'},
            'brake': {'orientation': 'vertical'},
        })

        reading = extractor.extract_frame_telemetry({
            'throttle': np.zeros_like(brake),
            'brake': brake,
        })

        self.assertAlmostEqual(reading['brake'], 40.0)

    def test_vertical_fill_ignores_a_thin_background_streak(self):
        """A single colored column is interior texture, not the pedal."""
        height, width = 80, 8
        brake = np.zeros((height, width, 3), dtype=np.uint8)
        brake[:, 0] = (0, 0, 255)
        extractor = TelemetryExtractor({
            'throttle': {'orientation': 'vertical'},
            'brake': {'orientation': 'vertical'},
        })

        reading = extractor.extract_frame_telemetry({
            'throttle': np.zeros_like(brake),
            'brake': brake,
        })

        self.assertEqual(reading['brake'], 0.0)


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


    def test_height_match_does_not_select_assetto_corsa(self):
        config = {
            'my_ps5_1080p': {'throttle': {'orientation': 'horizontal'}},
            'assetto_corsa_1080p': {'throttle': {'orientation': 'vertical'}},
        }
        service = VideoProcessingService.__new__(VideoProcessingService)
        name, profile = service.select_roi_profile(config, 1080)
        self.assertEqual(name, 'my_ps5_1080p')
        self.assertEqual(profile['throttle']['orientation'], 'horizontal')

        name, profile = service.select_roi_profile(
            config, 1080, profile_name='assetto_corsa_1080p'
        )
        self.assertEqual(name, 'assetto_corsa_1080p')
        self.assertEqual(profile['throttle']['orientation'], 'vertical')


if __name__ == '__main__':
    unittest.main()
