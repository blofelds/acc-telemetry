"""
Read Assetto Corsa original gear by matching one large glyph.

The gear digit is the same block font as speed, but much larger, and it
turns red at high RPM. Competizione profiles omit ``reader`` and stay on
OCR. Neutral is stored as ``N.png`` and returned as 0.
"""

from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from src.ac_speed_reader import READER_NAME, pad_glyph, white_mask

_CANVAS = 72
_MATCH_THRESHOLD = 0.55
# Files that may live in the templates folder. 5/6 are optional until a
# clip that reaches those gears is available.
_TEMPLATE_NAMES = ("1", "2", "3", "4", "5", "6", "N")


def gear_ink_mask(roi_bgr: np.ndarray) -> np.ndarray:
    """Keep white digit strokes and red high-RPM strokes."""
    white = white_mask(roi_bgr)
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 80, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 80, 100]), np.array([180, 255, 255])),
    )
    return cv2.bitwise_or(white, red)


def isolate_glyph(roi_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Return the trimmed ink blob, or None if the box is empty."""
    if roi_bgr is None or roi_bgr.size == 0:
        return None
    mask = gear_ink_mask(roi_bgr)
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) < 8 or len(cols) < 8:
        return None
    return mask[rows[0]: rows[-1] + 1, cols[0]: cols[-1] + 1]


class AcGearReader:
    """Match the gear ROI against saved pictures of this HUD font."""

    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)
        self.templates = self._load_templates(self.template_dir)

    def read(self, roi_bgr: np.ndarray) -> Optional[int]:
        """
        Return gear as an integer, or None if nothing matches.

        Neutral (``N.png``) is returned as 0. Missing 5/6 templates mean
        those gears read as None until pictures are added.
        """
        glyph = isolate_glyph(roi_bgr)
        if glyph is None:
            return None
        sample = pad_glyph(glyph, height=_CANVAS, width=_CANVAS).astype(np.float32)
        best_name = None
        best_score = _MATCH_THRESHOLD
        for name, template in self.templates.items():
            score = float(
                cv2.matchTemplate(sample, template, cv2.TM_CCOEFF_NORMED).max()
            )
            if score > best_score:
                best_score = score
                best_name = name
        if best_name is None:
            return None
        if best_name == "N":
            return 0
        return int(best_name)

    @staticmethod
    def _load_templates(template_dir: Path) -> Dict[str, np.ndarray]:
        if not template_dir.is_dir():
            raise FileNotFoundError(
                f"Assetto Corsa gear templates not found: {template_dir}"
            )
        templates = {}
        for name in _TEMPLATE_NAMES:
            path = template_dir / f"{name}.png"
            if not path.is_file():
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise FileNotFoundError(f"Could not read gear template {path}")
            templates[name] = image.astype(np.float32)
        if not templates:
            raise FileNotFoundError(
                f"No gear templates in {template_dir}. "
                "Add 1.png through 6.png and N.png as available."
            )
        return templates


__all__ = ["READER_NAME", "AcGearReader", "gear_ink_mask", "isolate_glyph"]
