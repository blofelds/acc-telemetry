# Throttle Detection Bug Fix - Technical Summary

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Date
October 22, 2024

## Problem Statement

The telemetry extraction was showing false throttle readings during braking events. Specifically:
- **During heavy braking (brake 99-100%)**, throttle showed 65-67% instead of 0%
- **Expected 3 throttle blips** during downshifting (6→5→4→3), but detected **6 blips**

## Root Cause Analysis

### Issue #1: False Throttle from UI Text Artifacts

**Symptoms:**
- Throttle reading of 65% while brake was at 99-100%
- Only 10-19 pixels detected in the throttle ROI

**Root Cause:**
The horizontal bar detection algorithm was detecting small amounts of green pixels from the **on-screen UI text overlay** (specifically the "TC: 37 10" traction control indicator). The algorithm found pixels at column 66-67 and calculated:
```
percentage = (67 / 103) * 100 = 65%
```

Even though only 10-19 pixels were detected (compared to 600-1200+ pixels for real throttle), the algorithm reported this as valid throttle input.

**Visual Evidence:**
- Debug images showed tiny green pixels around text characters
- These pixels were captured within the throttle ROI boundaries
- Not actual throttle bar, just UI overlay artifacts

### Issue #2: False Throttle Blips (Noise)

**Symptoms:**
- 6 throttle blips detected during braking instead of expected 3
- "Extra" blips had only 50-67 pixels
- Consistently low pixel counts across all frames

**Root Cause:**
The initial pixel threshold of 50 was too low. Some detections had:
- Blip #5: 50-67 pixels (avg 64)
- Blip #6: 54-57 pixels (avg 56)

These were text/UI artifacts, not real throttle bars.

## Solutions Implemented

### Fix #1: Minimum Pixel Threshold (Initial)

**File:** `src/telemetry_extractor.py`

**Change:**
```python
# Added minimum pixel threshold check
total_detected_pixels = np.count_nonzero(mask)
min_pixels_threshold = 50  # Initial threshold

if total_detected_pixels < min_pixels_threshold:
    return 0.0  # Filter out noise
```

**Result:**
- Eliminated some false readings
- Still detected 6 blips instead of 3

### Fix #2: Increased Pixel Threshold (Final)

**Change:**
```python
min_pixels_threshold = 150  # Increased from 50 to 150
```

**Rationale:**
- Real throttle bars have 300-700+ pixels
- UI text artifacts have <100 pixels
- Threshold of 150 provides good separation

**Result:**
- ✅ Eliminated false 65% throttle readings during pure braking
- ✅ Reduced 6 false blips to 3 real downshift blips
- ✅ Still captures actual throttle blips accurately

## Verification Results

### Before Fix:
```
Frame 61-63: Throttle 65% (10-12 pixels) - FALSE
Frame 67-70: Throttle 65% (14-19 pixels) - FALSE  
Frame 94-105: Throttle 45% (50-67 pixels) - FALSE

Total blips detected: 6
```

### After Fix:
```
Frame 61-63: Throttle 0% - CORRECT
Frame 67-70: Throttle 0% - CORRECT
Frame 94-105: Throttle 0% - CORRECT

Total blips detected: 3 (matching actual downshifts)
```

## Technical Details

### Pixel Count Analysis

| Detection Type | Pixel Count | Status |
|---------------|-------------|---------|
| Real throttle bar | 300-1200+ | Valid |
| Throttle blip during downshift | 300-700 | Valid |
| UI text artifacts | 10-100 | **Filtered** |
| Partial throttle release | 200-400 | Valid |

### Horizontal Bar Detection Logic

The algorithm detects horizontal bars by:
1. Converting image to HSV color space
2. Applying color masks (green + yellow for throttle)
3. Sampling middle rows to avoid edges
4. Finding rightmost filled pixel per row
5. **NEW:** Checking total pixel count against threshold
6. Calculating percentage based on median filled width

### Color Detection Ranges

**Green (normal throttle):**
- Hue: 35-85
- Saturation: 50-255
- Value: 50-255

**Yellow (TC active):**
- Hue: 15-35
- Saturation: 100-255
- Value: 100-255

## Why This Works

### Throttle Blipping is Correct
The 3 detected throttle blips during braking are **legitimate**:
- Console ACC (and PC ACC) applies automatic throttle blip during downshifts
- This matches rev-matching technique (heel-toe)
- Blips occur at ~0.15-0.2s intervals, matching human shift timing
- Peak throttle of 45-67% is appropriate for rev-matching

### Real-World Validation
User confirmed:
- Downshifted from 6th → 5th → 4th → 3rd gear (3 shifts)
- Expected 3 throttle blips for rev-matching
- Now correctly detects exactly 3 blips

## Configuration

### Current ROI Settings (1280×720 resolution)
```yaml
throttle:
  x: 1170
  y: 670
  width: 103
  height: 14
```

### Pixel Threshold
```python
min_pixels_threshold = 150  # In telemetry_extractor.py
```

## Lessons Learned

1. **Computer vision needs robust filtering**: A single pixel count isn't enough; need to validate signal strength
2. **UI overlays create artifacts**: Text and indicators can interfere with bar detection
3. **Context matters**: What looks like a bug might be correct (throttle blipping is real)
4. **Incremental thresholds**: Started at 50, needed 150 - empirical tuning required
5. **Pixel density validation**: Not just presence of pixels, but sufficient quantity

## Future Improvements

### Potential Enhancements:
1. **Adaptive thresholds**: Calculate threshold based on video resolution
2. **Temporal smoothing**: Require consistent detection across multiple frames
3. **ROI validation**: Check if bars are actually present in expected locations
4. **Confidence scoring**: Assign confidence levels to detections
5. **Machine learning**: Train classifier to distinguish real bars from artifacts

### Additional Validation:
- Test with different HUD scales
- Test with different graphics settings
- Test with different lighting conditions
- Validate across multiple tracks/cars

## Files Modified

- `src/telemetry_extractor.py` - Added pixel threshold validation

## Testing Methodology

1. **Frame-by-frame analysis**: Examined specific problematic frames (61-70, 94-105)
2. **Pixel count verification**: Measured actual pixels detected per frame
3. **Visual inspection**: Generated enlarged ROI images to see what was detected
4. **Pattern analysis**: Studied throttle blip timing and characteristics
5. **Ground truth comparison**: Validated against known driver inputs (3 downshifts)

## Conclusion

The bug was caused by insufficient filtering in the horizontal bar detection algorithm. By increasing the minimum pixel threshold from 50 to 150, we successfully:

- ✅ Eliminated false throttle readings from UI text artifacts
- ✅ Preserved legitimate throttle blip detection during downshifts  
- ✅ Achieved accurate telemetry matching real driver inputs

The telemetry extraction now correctly distinguishes between real throttle inputs and visual noise, providing accurate data for lap analysis.

---

**Status:** ✅ RESOLVED  
**Version:** v1.1 (with pixel threshold fix)  
**Tested:** ACC PS5 gameplay, 1280×720 resolution, ~49s lap footage

