"""Assetto Corsa gear uses digit pictures. Competizione stays on OCR."""

import unittest
from pathlib import Path

import cv2
import numpy as np
import yaml

from src.ac_gear_reader import AcGearReader
from src.lap_detector import LapDetector

FIXTURES = Path("tests/fixtures/ac_gear")
TEMPLATES = "templates/gear_digits/ac_1080p"


class TestAcGearReader(unittest.TestCase):
    def test_reads_saved_crops(self):
        reader = AcGearReader(TEMPLATES)
        expected = {"1": 1, "2": 2, "3": 3, "4": 4, "N": 0}
        for path in sorted(FIXTURES.glob("*.png")):
            image = cv2.imread(str(path))
            self.assertIsNotNone(image, path.name)
            self.assertEqual(reader.read(image), expected[path.stem], path.name)

    def test_profile_selects_assetto_corsa_for_gear(self):
        with open("config/roi_config.yaml") as handle:
            profiles = yaml.safe_load(handle)
        ac = profiles["assetto_corsa_1080p"]["gear"]
        self.assertEqual(ac["reader"], "assetto_corsa")
        self.assertTrue(ac["templates"].endswith("gear_digits/ac_1080p/"))
        acc = profiles["my_ps5_1080p"]["gear"]
        self.assertNotIn("reader", acc)

    def test_detector_uses_gear_templates(self):
        with open("config/roi_config.yaml") as handle:
            profiles = yaml.safe_load(handle)
        profile = profiles["assetto_corsa_1080p"]
        detector = LapDetector(profile)
        self.assertIsNotNone(detector._ac_gear_reader)
        crop = cv2.imread(str(FIXTURES / "2.png"))
        self.assertIsNotNone(crop)
        frame = np.zeros((1080, 1920, 3), np.uint8)
        gear = profile["gear"]
        x, y = gear["x"], gear["y"]
        h, w = crop.shape[:2]
        frame[y:y + h, x:x + w] = crop
        self.assertEqual(detector.extract_gear(frame), 2)


if __name__ == "__main__":
    unittest.main()
