"""
Telemetry extraction module for detecting throttle, brake, and steering values from ROI images.
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple


class TelemetryExtractor:
    """Extracts telemetry values from ROI images using computer vision."""

    VALID_ORIENTATIONS = ('horizontal', 'vertical')

    def __init__(self, roi_config: Optional[Dict] = None):
        """
        Read bar orientation from the selected ROI profile.

        ACC pedal bars fill left to right. Assetto Corsa (original) bars are
        thin vertical strips that fill from the bottom. Missing
        ``orientation`` stays ``horizontal`` so existing ACC profiles keep
        working without a YAML change.

        Args:
            roi_config: One profile from roi_config.yaml (the throttle/brake
                entries), not the whole file. None uses horizontal bars.
        """
        roi_config = roi_config or {}
        self.throttle_orientation = self.bar_orientation(roi_config.get('throttle'))
        self.brake_orientation = self.bar_orientation(roi_config.get('brake'))

    @classmethod
    def bar_orientation(cls, roi_entry: Optional[Dict] = None, default: str = 'horizontal') -> str:
        """
        Return ``horizontal`` or ``vertical`` for a throttle/brake ROI entry.

        Args:
            roi_entry: One ROI mapping (x, y, width, height, optional orientation).
            default: Used when the entry or the key is missing.

        Returns:
            ``horizontal`` or ``vertical``.

        Raises:
            ValueError: If orientation is present but not one of those two.
        """
        if not roi_entry:
            return default

        raw = roi_entry.get('orientation', default)
        if raw is None or str(raw).strip() == '':
            return default

        orientation = str(raw).strip().lower()
        if orientation not in cls.VALID_ORIENTATIONS:
            raise ValueError(
                f"Invalid bar orientation '{raw}'. "
                f"Use 'horizontal' or 'vertical'."
            )
        return orientation

    @staticmethod
    def extract_bar_percentage(roi_image: np.ndarray, target_color: str = 'green', orientation: str = 'horizontal') -> float:
        """
        Extract percentage value from a bar by detecting filled portion.
        Supports both horizontal and vertical bars.
        
        Args:
            roi_image: Cropped image of the bar
            target_color: 'green' for throttle, 'gray' for brake
            orientation: 'vertical' (fill from the bottom) or 'horizontal'
                (fill from the left). Defaults to horizontal, which matches
                ACC. Pass the profile value for Assetto Corsa original.
            
        Returns:
            Percentage value (0.0 to 100.0)
        """
        if roi_image is None or roi_image.size == 0:
            return 0.0
            
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
        
        if target_color == 'green':
            # Green AND Yellow color ranges (bars change color when TC activate)
            # Green range
            lower_green = np.array([35, 50, 50])
            upper_green = np.array([85, 255, 255])
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            
            # Yellow/Orange range (when TC active)
            lower_yellow = np.array([15, 100, 100])
            upper_yellow = np.array([35, 255, 255])
            mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            
            # Combine both masks
            mask = cv2.bitwise_or(mask_green, mask_yellow)
            
        elif target_color == 'red':
            # Red, Orange, Yellow color ranges (brake bar changes when ABS activates)
            # Red range (HSV red wraps around at 0/180)
            # ADJUSTED: Lowered V threshold from 100 → 50 to detect dim brake bars
            lower_red1 = np.array([0, 100, 50])
            upper_red1 = np.array([10, 255, 255])
            mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)

            lower_red2 = np.array([170, 100, 50])
            upper_red2 = np.array([180, 255, 255])
            mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)

            # Orange/Yellow range (when ABS active)
            # ADJUSTED: Lowered V threshold from 100 → 50 for consistency
            lower_orange = np.array([10, 100, 50])
            upper_orange = np.array([40, 255, 255])
            mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
            
            # Combine all masks
            mask = cv2.bitwise_or(cv2.bitwise_or(mask_red1, mask_red2), mask_orange)
            
        else:  # gray/white
            # Gray/white color range
            lower_bound = np.array([0, 0, 100])
            upper_bound = np.array([180, 50, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        height, width = mask.shape
        
        if orientation == 'vertical':
            percentage = TelemetryExtractor._vertical_fill_percentage(mask)
            
        else:  # horizontal
            # Sample middle 80% of rows (10% to 90%) to avoid edge artifacts while capturing
            # enough valid rows to bypass text overlays (which create holes in the middle)
            start_row = int(height * 0.1)
            end_row = int(height * 0.9)
            # Ensure at least one row is selected
            if start_row == end_row:
                end_row += 1
                
            middle_rows = mask[start_row:end_row, :]

            # Find the continuous filled region from the left edge
            # This handles text overlays and gaps by detecting the main bar fill
            filled_widths = []
            for row in middle_rows:
                non_zero_cols = np.where(row > 0)[0]
                if len(non_zero_cols) == 0:
                    continue

                # Find the longest continuous run starting from near the left edge
                # The bar fills from left to right, so we want the leftmost continuous region
                max_continuous_width = 0
                current_run_start = None
                current_run_length = 0

                for i, col in enumerate(non_zero_cols):
                    if current_run_start is None:
                        # Start new run
                        current_run_start = col
                        current_run_length = 1
                    elif col == non_zero_cols[i-1] + 1:
                        # Continue existing run (consecutive pixel)
                        current_run_length += 1
                    else:
                        # Gap detected - save previous run if it's the best so far
                        if current_run_length > max_continuous_width:
                            max_continuous_width = current_run_length
                        # Start new run
                        current_run_start = col
                        current_run_length = 1

                # Don't forget the last run
                if current_run_length > max_continuous_width:
                    max_continuous_width = current_run_length

                if max_continuous_width > 0:
                    filled_widths.append(max_continuous_width)

            if not filled_widths:
                return 0.0

            # Use 80th percentile instead of median
            # Why: Text overlays (e.g. "ABS") create holes in the bar, causing many rows to have 
            # artificially low widths. The "true" bar width is represented by the solid rows 
            # above/below the text. Since "bad" rows might outnumber "good" rows (e.g. 6 vs 3),
            # median fails. 80th percentile robustly picks the full width while rejecting single-row noise.
            filled_width = np.percentile(filled_widths, 80)
            percentage = (filled_width / width) * 100.0
        
        return min(100.0, max(0.0, percentage))

    @staticmethod
    def _vertical_fill_percentage(mask: np.ndarray) -> float:
        """
        Measure a vertical bar that fills from the bottom.

        The empty bar is transparent, so the car interior shows through.
        That background changes with the car and slides around as the
        camera pitches in braking and corners. A matching blob that is
        not anchored to the bottom of the ROI is not the pedal.

        A row counts only when most of its width is colored. The fill is
        a solid column; a dashboard glyph usually is not. A one or two
        pixel hole (compression, or the interior cutting across the bar)
        does not end the run.

        Args:
            mask: Binary mask of the bar color (255 = colored).

        Returns:
            Fill percentage from 0.0 to 100.0.
        """
        height, width = mask.shape
        if height == 0 or width == 0:
            return 0.0

        # Majority of the row, so a thin streak of interior color does
        # not start a fill. At least one pixel on a 1px-wide crop.
        min_colored = max(1, int(np.ceil(width * 0.5)))
        row_is_fill = np.count_nonzero(mask, axis=1) >= min_colored

        # Walk up from the bottom. Stop at a gap bigger than the hole
        # we are willing to treat as noise.
        gap_tolerance = 2
        gap = 0
        top = height
        for row in range(height - 1, -1, -1):
            if row_is_fill[row]:
                top = row
                gap = 0
            else:
                gap += 1
                if gap > gap_tolerance:
                    break

        filled_height = height - top
        return (filled_height / height) * 100.0

    @staticmethod
    def extract_steering_position(roi_image: np.ndarray) -> float:
        """
        Extract steering position from the steering indicator.
        Detects white dot position on horizontal scale.
        
        Args:
            roi_image: Cropped image of the steering indicator
            
        Returns:
            Normalized steering position (-1.0 = full left, 0.0 = center, +1.0 = full right)
        """
        if roi_image is None or roi_image.size == 0:
            return 0.0
            
        # Convert to grayscale
        gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)

        # Threshold to find bright white pixels (the dot)
        # Adjusted: 180 threshold (was 200) to catch slightly dimmer dots in different videos
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        
        # Find contours/bright regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0.0
        
        # Filter contours to find the steering dot
        # The steering dot should be:
        # 1. Small to medium size (3-100 pixels) - steering dot is compact
        # 2. Compact (roughly square, not elongated text)
        # 3. Located in the bottom half of ROI (scale line is at bottom)
        height = roi_image.shape[0]
        width = roi_image.shape[1]

        dot_candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area (steering dot is small, text is larger)
            # Adjusted: 3-100 pixels (was 5-50) to catch smaller dots in different videos
            if not (3 <= area < 100):
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio (dot should be roughly square, not elongated like text)
            aspect_ratio = w / h if h > 0 else 0
            if not (0.5 < aspect_ratio < 2.0):
                continue
            
            # Filter by vertical position (dot is in bottom 2/3 of ROI, text is at top)
            center_y = y + h // 2
            if center_y < height * 0.33:
                continue  # Skip things in top third (text labels)
            
            # Calculate centroid
            M = cv2.moments(contour)
            if M['m00'] == 0:
                continue
            
            cx = M['m10'] / M['m00']
            cy = M['m01'] / M['m00']
            
            dot_candidates.append({
                'contour': contour,
                'cx': cx,
                'cy': cy,
                'area': area
            })
        
        if not dot_candidates:
            # Fallback: if no good candidates, return center position
            return 0.0
        
        # Select the best candidate (largest area among filtered candidates)
        best_dot = max(dot_candidates, key=lambda d: d['area'])
        cx = best_dot['cx']
        
        # Normalize to -1.0 to +1.0 range
        normalized_position = (cx / width) * 2.0 - 1.0
        
        return max(-1.0, min(1.0, normalized_position))
    
    @staticmethod
    def extract_tc_active(roi_image: np.ndarray) -> int:
        """
        Detect if traction control (TC) is active by checking for yellow/orange color in throttle bar.
        TC activation causes the throttle bar to change from green to yellow/orange.
        
        Important: This method requires both yellow pixels AND an actual throttle bar to be present
        to avoid false positives from ABS glow bleeding into the throttle ROI.
        
        Args:
            roi_image: Cropped image of the throttle bar
            
        Returns:
            1 if TC is active (yellow/orange detected with throttle present), 0 otherwise
        """
        if roi_image is None or roi_image.size == 0:
            return 0
        
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
        
        # Yellow/Orange range (same as used in extract_bar_percentage for TC detection)
        lower_yellow = np.array([15, 100, 100])
        upper_yellow = np.array([35, 255, 255])
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # Green range (normal throttle color)
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        
        # Count pixels
        yellow_pixel_count = np.count_nonzero(mask_yellow)
        green_pixel_count = np.count_nonzero(mask_green)
        total_throttle_pixels = green_pixel_count + yellow_pixel_count
        
        # TC is active if:
        # 1. Yellow pixels present (>= 50)
        # 2. Total bar pixels present (>= 150) - ensures it's a real bar, not just glow
        # This prevents false positives from ABS glow bleeding into throttle ROI
        yellow_threshold = 50
        total_pixels_threshold = 150
        
        return 1 if (yellow_pixel_count >= yellow_threshold and 
                    total_throttle_pixels >= total_pixels_threshold) else 0
    
    @staticmethod
    def extract_abs_active(roi_image: np.ndarray) -> int:
        """
        Detect if ABS is active by checking for orange/yellow color in brake bar.
        ABS activation causes the brake bar to change from red to orange/yellow.
        
        Args:
            roi_image: Cropped image of the brake bar
            
        Returns:
            1 if ABS is active (orange detected), 0 otherwise
        """
        if roi_image is None or roi_image.size == 0:
            return 0
        
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)

        # Orange/Yellow range (same as used in extract_bar_percentage for ABS detection)
        # ADJUSTED: Lowered V threshold from 100 → 50 to detect dim ABS activation
        lower_orange = np.array([10, 100, 50])
        upper_orange = np.array([40, 255, 255])
        mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
        
        # Count orange pixels
        orange_pixel_count = np.count_nonzero(mask_orange)
        
        # Threshold: need at least 50 pixels to confirm ABS is active (avoid noise)
        min_pixels_threshold = 50
        
        return 1 if orange_pixel_count >= min_pixels_threshold else 0
    
    def extract_frame_telemetry(self, roi_dict: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Extract all telemetry values from a frame's ROI images.

        Throttle and brake orientation come from the ROI profile passed to
        the constructor. Steering is optional: Assetto Corsa original has no
        on-screen steering indicator, and a missing crop is reported as 0.0.

        Args:
            roi_dict: Dictionary with 'throttle' and 'brake' ROI images.
                'steering' is included when the profile defines that ROI.

        Returns:
            Dictionary with extracted values including TC and ABS activation status
        """
        steering_roi = roi_dict.get('steering')
        return {
            'throttle': self.extract_bar_percentage(
                roi_dict['throttle'], 'green', self.throttle_orientation
            ),
            'brake': self.extract_bar_percentage(
                roi_dict['brake'], 'red', self.brake_orientation
            ),
            'steering': self.extract_steering_position(steering_roi),
            'tc_active': self.extract_tc_active(roi_dict['throttle']),
            'abs_active': self.extract_abs_active(roi_dict['brake'])
        }

