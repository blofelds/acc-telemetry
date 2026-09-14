"""
Read Assetto Corsa original speed digits by matching each glyph.

Tesseract reads Competizione's plain speed font. It does not read this
block font: a 1 is a thin stroke, and a 7 is a top bar with a stem.
Pictures of those glyphs, cut from this HUD, are the reader.

Competizione profiles omit ``reader`` and stay on OCR.
"""

from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

READER_NAME = "assetto_corsa"
_CANVAS = (28, 24)  # height, width
_MATCH_THRESHOLD = 0.55


def white_mask(roi_bgr: np.ndarray) -> np.ndarray:
    """Keep the white digit strokes and drop the dark cabin behind them."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 0, 150), (180, 80, 255))


def segment_glyphs(roi_bgr: np.ndarray) -> List[np.ndarray]:
    """
    Return one binary glyph per digit, left to right.

    A column is a gap only when it has almost no ink. A wide blob is left
    whole: a 7 is wide, and cutting it invents a leading 1. A 1 that has
    joined the next digit will not match, and that frame returns no speed.
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return []
    mask = white_mask(roi_bgr)
    glyphs = []
    for start, end in _column_spans(mask):
        glyph = _trim_rows(mask[:, start:end])
        if glyph is not None:
            glyphs.append(glyph)
    return glyphs


def _column_spans(mask: np.ndarray) -> List[tuple]:
    counts = (mask > 0).sum(axis=0)
    spans = []
    start = None
    for x, count in enumerate(counts):
        if count >= 3 and start is None:
            start = x
        elif count < 3 and start is not None:
            if x - start >= 3:
                spans.append((start, x))
            start = None
    if start is not None and mask.shape[1] - start >= 3:
        spans.append((start, mask.shape[1]))
    return spans


def _trim_rows(glyph: np.ndarray) -> Optional[np.ndarray]:
    rows = np.where(glyph.any(axis=1))[0]
    if len(rows) < 6:
        return None
    return glyph[rows[0]: rows[-1] + 1, :]


def pad_glyph(glyph: np.ndarray, height: int = _CANVAS[0], width: int = _CANVAS[1]) -> np.ndarray:
    """Center a glyph on a fixed canvas so each digit can be compared."""
    canvas = np.zeros((height, width), np.uint8)
    image = glyph
    h, w = image.shape[:2]
    if h > height or w > width:
        scale = min(width / w, height / h)
        image = cv2.resize(
            image,
            (max(1, int(w * scale)), max(1, int(h * scale))),
            interpolation=cv2.INTER_NEAREST,
        )
        h, w = image.shape[:2]
    y0 = (height - h) // 2
    x0 = (width - w) // 2
    canvas[y0:y0 + h, x0:x0 + w] = image
    return canvas


class AcSpeedReader:
    """Match each segmented digit against saved pictures of this HUD font."""

    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)
        self.templates = self._load_templates(self.template_dir)

    def read(self, roi_bgr: np.ndarray) -> Optional[int]:
        """
        Return the speed in km/h, or None if a glyph does not match.

        Args:
            roi_bgr: Cropped speed box (BGR).

        Returns:
            Integer speed, or None.
        """
        digits = []
        for glyph in segment_glyphs(roi_bgr):
            digit = self._match(glyph)
            if digit is None:
                return None
            digits.append(digit)
        if not digits:
            return None
        value = int("".join(digits))
        if value > 400:
            return None
        return value

    def read_leading_digits(
        self, roi_bgr: np.ndarray, max_digits: int = 2
    ) -> Optional[int]:
        """
        Read up to ``max_digits`` from the left; stop at the first unmatched glyph.

        Lap is ``N LAPS`` or ``NN LAPS`` — no slash. Speed-style matching would
        fail if the crop catches a non-digit (for example the edge of LAPS).
        Taking only the leading digit matches keeps the lap value.
        """
        digits = []
        for glyph in segment_glyphs(roi_bgr):
            digit = self._match(glyph)
            if digit is None:
                break
            digits.append(digit)
            if len(digits) >= max_digits:
                break
        if not digits:
            return None
        return int("".join(digits))

    def _match(self, glyph: np.ndarray) -> Optional[str]:
        sample = pad_glyph(glyph).astype(np.float32)
        best_digit = None
        best_score = _MATCH_THRESHOLD
        for digit, template in self.templates.items():
            score = float(cv2.matchTemplate(sample, template, cv2.TM_CCOEFF_NORMED).max())
            if score > best_score:
                best_score = score
                best_digit = digit
        return best_digit

    @staticmethod
    def _load_templates(template_dir: Path) -> Dict[str, np.ndarray]:
        if not template_dir.is_dir():
            raise FileNotFoundError(
                f"Assetto Corsa speed templates not found: {template_dir}"
            )
        templates = {}
        for digit in "0123456789":
            path = template_dir / f"{digit}.png"
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise FileNotFoundError(
                    f"Missing speed template {path}. "
                    "Each digit needs a file named 0.png through 9.png."
                )
            templates[digit] = image.astype(np.float32)
        return templates
