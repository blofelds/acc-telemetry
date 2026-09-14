"""Assetto Corsa speed uses digit pictures. Competizione stays on OCR."""

import unittest
from pathlib import Path

import cv2

from src.ac_speed_reader import AcSpeedReader
from src.lap_detector import LapDetector

FIXTURES = Path("tests/fixtures/ac_speed")
TEMPLATES = "templates/speed_digits/ac_1080p"


class TestAcSpeedReader(unittest.TestCase):
    def test_reads_saved_crops_from_both_clips(self):
        reader = AcSpeedReader(TEMPLATES)
        for path in sorted(FIXTURES.glob("*.png")):
            image = cv2.imread(str(path))
            self.assertIsNotNone(image, path.name)
            self.assertEqual(reader.read(image), int(path.stem), path.name)

    def test_missing_reader_stays_on_ocr(self):
        self.assertEqual(LapDetector.speed_reader_from_roi({}), 'ocr')
        self.assertEqual(LapDetector.speed_reader_from_roi(None), 'ocr')
        self.assertEqual(
            LapDetector.speed_reader_from_roi({'reader': 'OCR'}), 'ocr'
        )

    def test_profile_selects_assetto_corsa(self):
        self.assertEqual(
            LapDetector.speed_reader_from_roi({'reader': 'assetto_corsa'}),
            'assetto_corsa',
        )

    def test_unknown_reader_raises(self):
        with self.assertRaises(ValueError):
            LapDetector.speed_reader_from_roi({'reader': 'template'})

    def test_configured_profile_names_the_ac_reader(self):
        import yaml
        with open("config/roi_config.yaml") as handle:
            profiles = yaml.safe_load(handle)
        ac = profiles["assetto_corsa_1080p"]["speed"]
        self.assertEqual(ac["reader"], "assetto_corsa")
        self.assertTrue(ac["templates"].endswith("ac_1080p/"))
        acc = profiles["my_ps5_1080p"]["speed"]
        self.assertNotIn("reader", acc)


if __name__ == "__main__":
    unittest.main()
