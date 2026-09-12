# Template Matching Implementation for Lap Number Detection

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Overview

This document explains how we switched from OCR to template matching for lap number recognition, achieving **67x faster** performance (1.5ms vs 100ms per frame).

## The Problem

Initially, we used Tesseract OCR to read lap numbers from the HUD. While accurate, OCR was:
- ❌ **Slow**: 50-200ms per frame
- ❌ **Overkill**: Recognizing only 0-9 digits doesn't need full OCR
- ❌ **CPU-intensive**: Would struggle on longer videos

## The Solution: Template Matching

Template matching is a computer vision technique where we:
1. Create reference images (templates) of each digit 0-9
2. Slide each template across the ROI to find matches
3. Combine matched digits into a number

### Performance Comparison

| Method | Time per Frame | Speedup | Frames per Second |
|--------|---------------|---------|-------------------|
| Tesseract OCR | ~100ms | 1x | ~10 fps |
| Template Matching | ~1.5ms | **67x** | ~666 fps |

## Implementation

### 1. Template Creation

Templates are extracted from the actual video to ensure they match the font, size, and rendering:

```python
# Located in: templates/lap_digits/
0.png  # Digit "0" (23×13 pixels)
1.png  # Digit "1" (29×39 pixels)
2.png  # Digit "2" (23×13 pixels)
...
9.png  # Digit "9" (8×6 pixels)
```

**Important**: Templates must come from the same video source (same resolution, HUD scale, rendering).

### 2. ROI Extraction

The lap number is shown in the "LAP NUMBER" indicator in the top-left HUD:

```yaml
# config/roi_config.yaml
lap_number:
  x: 237      # Position of "LAP NUMBER" box
  y: 71
  width: 47   # ROI contains digit + "LAPS" text
  height: 37
```

**Note**: The ROI intentionally includes extra space ("LAPS" text, background) because the sliding window algorithm handles this automatically.

### 3. Sliding Window Algorithm

The key innovation is using **sliding window template matching** instead of trying to isolate digits first:

```python
def recognize_number(self, roi: np.ndarray, max_digits: int = 2) -> Optional[int]:
    """
    Scan entire ROI with each digit template.
    Find all matches above confidence threshold.
    Combine matches left-to-right into a number.
    """
    # Preprocess ROI to binary
    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    
    # Slide each template across the ROI
    matches = []
    for digit, template in self.templates.items():
        result = cv2.matchTemplate(binary, template, cv2.TM_CCOEFF_NORMED)
        
        # Find all positions where match confidence > 0.6
        locations = np.where(result >= 0.6)
        
        for y, x in zip(*locations):
            confidence = result[y, x]
            matches.append((x, digit, confidence))
    
    # Sort matches by x-position (left to right)
    matches.sort(key=lambda m: m[0])
    
    # Remove duplicates at similar positions
    # Combine digits into number: "1" at x=10, "1" at x=25 → "11"
    return combine_digits(matches)
```

### 4. How It Works Step-by-Step

#### Example: Detecting Lap 8

1. **Input ROI** (47×37 pixels):
   ```
   ┌─────────────────┐
   │  8    LAPS      │  ← White text on dark background
   └─────────────────┘
   ```

2. **Preprocessing**:
   ```
   Convert to grayscale → Threshold → Binary image
   ```

3. **Template Sliding**:
   - Slide "0" template: No match
   - Slide "1" template: No match
   - ...
   - Slide "8" template: **MATCH at x=12, confidence=0.82** ✅
   - Slide "9" template: No match

4. **Result**: Detected matches: `[(x=12, digit="8", conf=0.82)]`
   → Lap number = **8**

#### Example: Detecting Lap 11

1. **Input ROI**:
   ```
   ┌─────────────────┐
   │  11   LAPS      │  ← Two "1" digits
   └─────────────────┘
   ```

2. **Template Sliding**:
   - Slide "1" template: 
     - MATCH at x=10, confidence=0.78 ✅
     - MATCH at x=26, confidence=0.80 ✅

3. **Result**: Detected matches: `[(x=10, "1", 0.78), (x=26, "1", 0.80)]`
   → Sorted by x-position → "11"
   → Lap number = **11**

## Advantages of Sliding Window Approach

### 1. **Robust to Noise**
The ROI contains more than just the digit:
- ✅ "LAPS" text → Ignored (doesn't match any template)
- ✅ Background variations → Ignored
- ✅ Anti-aliasing artifacts → Low confidence, filtered out

### 2. **Automatic Multi-Digit Detection**
No need to manually split the ROI:
- Single digit (1-9): Finds 1 match
- Double digit (10-99): Finds 2 matches at different x-positions
- Automatically combines left-to-right

### 3. **No Manual Digit Isolation Required**
Previous approaches tried to:
1. Find connected components
2. Identify which is the digit
3. Crop to exact digit bounds
4. Then match

**Problem**: Fails if there's noise or multiple text elements.

**Sliding window**: Just scan everything, let confidence scores decide what's a digit.

### 4. **Fast & Efficient**
- OpenCV's `matchTemplate` is optimized C++ code
- Sliding 10 templates across 47×37 ROI takes ~1.5ms
- No complex preprocessing needed

## Why This Works Better Than Previous Attempts

### ❌ Attempt 1: Resize Entire ROI to Template Size
```python
# Problem: Distorts everything
roi_resized = cv2.resize(roi, template.shape)  # 47×37 → 13×23
result = cv2.matchTemplate(roi_resized, template)
# Result: "8 LAPS" squashed to 13×23 looks nothing like "8"
# Match score: 0.20 (too low) ❌
```

### ❌ Attempt 2: Isolate Largest Connected Component
```python
# Problem: Fails if "LAPS" text is larger than digit
components = find_connected_components(roi)
largest = get_largest(components)  # Might get "LAPS" not "8"
result = cv2.matchTemplate(largest, template)
# Result: Unreliable, depends on relative sizes ❌
```

### ✅ Final Solution: Sliding Window
```python
# Scans entire ROI, finds digits wherever they are
result = cv2.matchTemplate(roi, template)
locations = np.where(result > 0.6)  # High confidence = real digit
# Result: Works regardless of noise, text, or background ✅
```

## Configuration & Tuning

### Confidence Threshold
```python
threshold = 0.6  # Balance between false positives and missed detections
```

- **Too low (< 0.5)**: False positives (noise detected as digits)
- **Too high (> 0.7)**: Missed detections (real digits rejected)
- **Sweet spot (0.6)**: Works well for lap numbers

### Duplicate Filtering
```python
min_distance = 10  # Minimum pixels between distinct digits
```

Since templates slide pixel-by-pixel, the same digit might match at multiple nearby positions:
- x=12, confidence=0.78
- x=13, confidence=0.79 ← Very close to x=12
- x=14, confidence=0.77

We filter these to keep only the best match in each region.

### Maximum Digits
```python
max_digits = 2  # For lap numbers (1-99)
max_digits = 3  # For speed (0-999 km/h)
```

If more matches are found, keep the N with highest confidence.

## Creating Templates from Video

Templates MUST match the actual video to work properly. Here's how to extract them:

### 1. Run Extraction Script
```bash
# extract_lap_digit_templates.py removed (historical calibration helper)
```

This scans the video and extracts lap number samples to `debug/digit_extraction/`.

### 2. Identify Sample Frames
Look for frames showing different lap numbers:
- `frame240_mask.png` → Shows "0"
- `frame5880_mask.png` → Shows "1"
- `frame8370_mask.png` → Shows "3"
- etc.

### 3. Copy as Templates
```bash
# copy_extracted_as_templates.py removed (historical calibration helper)
```

This automatically creates templates from the extracted frames.

### 4. Verify Templates
```bash
# test_template_matching.py removed
```

Should show successful detections on various frames.

## Integration with Main Pipeline

### In `main.py`:
```python
# Initialize lap detector with template matching
lap_detector = LapDetector(roi_config, enable_performance_stats=True)

# Process each frame
for frame_num, timestamp, roi_dict in processor.process_frames():
    lap_number = lap_detector.extract_lap_number(processor.current_frame)
    # lap_number is now detected via template matching (not OCR)
```

### In `src/lap_detector.py`:
```python
def extract_lap_number(self, frame: np.ndarray) -> Optional[int]:
    # Extract ROI
    roi = frame[y:y+h, x:x+w]
    
    # Preprocess to isolate white digits
    white_mask = isolate_white_text(roi)
    
    # Use template matching (not OCR!)
    lap_number = self.lap_matcher.recognize_number(white_mask, max_digits=2)
    
    return lap_number
```

## Troubleshooting

### No Detections
**Symptom**: All frames return `None` for lap number

**Possible causes**:
1. Templates don't match video (different resolution/HUD scale)
   - **Fix**: Re-extract templates from the actual video
2. ROI coordinates wrong (not capturing lap number)
   - **Fix**: Run `a temporary debug script under debug/ (visualize_roi_debug.py was removed)` to check ROI position
3. Threshold too high
   - **Fix**: Lower threshold from 0.6 to 0.5 temporarily for testing

### Wrong Numbers Detected
**Symptom**: Detecting "3" when video shows "8"

**Possible causes**:
1. Template quality poor (noisy, partial digit)
   - **Fix**: Find clearer frame to extract template
2. Multiple matches with similar confidence
   - **Fix**: Check `filtered_matches` logic in code

### Inconsistent Detections
**Symptom**: Frame 1000: lap 5, Frame 1001: None, Frame 1002: lap 5

**Solution**: This is normal! Use the caching logic in `LapDetector`:
```python
# Cache last valid lap number
if lap_number is not None:
    self._last_valid_lap_number = lap_number
    return lap_number
else:
    return self._last_valid_lap_number  # Use cached value
```

## Performance Statistics

From a real 48-minute race video (69,699 frames):

```
⚡ Lap Detection Performance:
   Method: Template Matching
   Total frames: 69,699
   Recognition calls: 69,699
   Avg time per frame: 1.5ms
   Speedup vs OCR: 67x faster
   
   Total processing time: ~105 seconds
   (vs ~7000 seconds with OCR = 1.9 hours saved!)
```

## Future Enhancements

### 1. Multi-Scale Templates
Currently, templates work for one specific resolution. Could add:
```python
templates_720p = load_templates('templates/lap_digits_720p/')
templates_1080p = load_templates('templates/lap_digits_1080p/')
```

### 2. Adaptive Thresholding
Adjust confidence threshold based on video quality:
```python
if video_quality == 'high':
    threshold = 0.7  # Be more strict
else:
    threshold = 0.5  # Be more lenient
```

### 3. Template Learning
Automatically improve templates during processing:
```python
if confidence > 0.9:  # Very confident match
    update_template(digit, matched_region)  # Use as new template
```

## Conclusion

Template matching provides a fast, robust solution for digit recognition in gaming HUDs:

- ✅ **67x faster than OCR**
- ✅ **Handles noise and background text automatically**
- ✅ **Works for multi-digit numbers without manual splitting**
- ✅ **Simple to implement and maintain**

The sliding window approach is key: instead of trying to isolate digits first, we scan the entire ROI and let confidence scores determine what's a digit and what's noise.

---

**Related Documentation**:
- [Template Matching Guide](TEMPLATE_MATCHING_GUIDE.md) - General guide (existing)
- [Performance Optimization](PERFORMANCE_OPTIMIZATION.md) - Why template matching is faster
- [ROI Configuration](../config/roi_config.yaml) - ROI coordinates setup


