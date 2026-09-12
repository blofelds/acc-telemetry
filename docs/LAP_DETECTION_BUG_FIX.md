# Lap Detection Bug Fix - Oscillation at Lap 10 and 20

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Problem Description

The lap number detection was oscillating between consecutive values during laps 10/11 and 20/21, causing visualization artifacts where lap markers would appear multiple times in rapid succession.

**Example from broken data:**
```
Frame 27096: Lap 11
Frame 27097: Lap 10  ← Oscillation!
Frame 27098: Lap 10
...
Frame 27230: Lap 11
Frame 27242: Lap 10  ← Oscillation!
```

This created visual noise in the telemetry graphs with false lap boundaries appearing every few frames.

## Root Cause Analysis

### Primary Issue: Template Matching Ambiguity
When detecting two-digit numbers like "10", "11", "20", "21", the template matcher would sometimes:
1. Find both digits correctly → "10"
2. Next frame: Find only the "1" digit with high confidence → "1" (misdetected as single digit)
3. Next frame: Find both "1" and "0" again → "10"

This was due to:
- **Low matching threshold (0.6)**: Allowed partial/noisy matches
- **No temporal smoothing**: Each frame was independent, so flickering detections weren't filtered
- **Too permissive validation**: The lap detector allowed backward jumps of -1, enabling oscillation

### Secondary Issue: Visualization
The visualization code drew vertical lines at every lap transition, so when laps oscillated 10→11→10→11, it drew many false lines.

## Solution

### 1. Temporal Smoothing with Majority Voting (lap_detector.py)

Added a sliding window history that tracks the last 5 frame detections:

```python
self._lap_number_history: list = []  # Track recent detections
self._history_size: int = 5  # Number of frames to track
```

**Majority voting algorithm:**
- Collect last 5 detections (e.g., [10, 11, 10, 10, 10])
- Use Counter to find most common value (10 appears 4 times)
- Require 60% agreement (3/5 frames) to accept the value
- If no consensus, keep previous lap number

This filters out single-frame misdetections and requires consistency before changing lap numbers.

### 2. Stricter Validation Logic

Changed lap transition logic to prevent backward jumps:

**Before (broken):**
```python
if abs(lap_number - self._last_valid_lap_number) > 1:
    return self._last_valid_lap_number  # Reject jumps > 1
```

**After (fixed):**
```python
lap_diff = smoothed_lap - self._last_valid_lap_number

if lap_diff == 0:
    return self._last_valid_lap_number  # No change
elif lap_diff == 1:
    self._last_valid_lap_number = smoothed_lap  # Normal progression
    return smoothed_lap
elif lap_diff > 1:
    # Allow large jumps (session resets)
    self._last_valid_lap_number = smoothed_lap
    return smoothed_lap
else:
    # Reject backward jumps (lap_diff < 0)
    return self._last_valid_lap_number
```

Now **backward jumps are completely rejected**, preventing oscillation.

### 3. Higher Template Matching Threshold (template_matcher.py)

Increased threshold from 0.6 to 0.65:

```python
threshold = 0.65  # Increased from 0.6 to reduce false matches
```

This makes the matcher more strict, reducing false positives where partial matches were accepted.

### 4. Improved Duplicate Filtering

Reduced minimum distance between detected digits from 10 to 8 pixels:

```python
min_distance = 8  # Minimum x-distance between distinct digits
```

This allows proper detection of closely-spaced digits in the HUD while still filtering duplicates.

## Results

### Before Fix (telemetry_20251022_042207.csv)
```
Lap transitions detected: 95 (many false positives)

Lap 9 → 10 at frame 26988
Lap 10 → 11 at frame 27096
Lap 11 → 10 at frame 27097  ← Oscillation
Lap 10 → 11 at frame 27230
Lap 11 → 10 at frame 27242  ← Oscillation
... (continues oscillating for 2000+ frames)
Lap 10 → 11 at frame 29478  ← Finally stabilizes

Similar oscillations at lap 20→21
```

### After Fix (telemetry_20251022_042907.csv)
```
Lap transitions detected: 26 (clean)

Lap 9 → 10 at frame 26990
Lap 10 → 11 at frame 27232  ← Clean transition!
Lap 11 → 12 at frame 32040
...
Lap 19 → 20 at frame 51995
Lap 20 → 21 at frame 54505  ← Clean transition!
Lap 21 → 22 at frame 56999
```

**All oscillations eliminated!** ✅

## Technical Details

### Why Laps 10, 11, 20, 21 Were Affected

These specific lap numbers are vulnerable because:
- **Two-digit numbers**: More complex to detect than single digits (laps 1-9)
- **Shared digits**: "10" and "11" both start with "1", so if "0" detection fails, it becomes "1"
- **Similar appearance**: Templates for "0" and "1" can partially match each other depending on video compression/noise

### Why Temporal Smoothing Works

The key insight: **genuine lap transitions last 1-2 seconds (~24-48 frames), but misdetections last only 1-3 frames**.

- Real lap change: HUD displays new lap number for entire lap duration (2-3 minutes = ~3000 frames)
- False detection: Template matcher finds wrong digit for 1-2 frames due to noise/compression

By requiring 3 out of 5 frames to agree, we filter out brief misdetections while allowing real transitions (which persist for many frames).

### Performance Impact

The fix adds minimal overhead:
- History tracking: O(1) append, O(1) pop
- Majority voting: O(n) where n=5, done once per frame
- Total added latency: ~0.01ms per frame (negligible)

Template matching remains **67x faster than OCR** (1.5ms vs 100ms per frame).

## Testing

Verified fix with 69,699-frame video (2907 seconds):
- ✅ No lap oscillations at lap 10/11
- ✅ No lap oscillations at lap 20/21
- ✅ All other laps (1-27) detected correctly
- ✅ Lap times correctly captured
- ✅ Visualization clean without false lap markers

## Lessons Learned

1. **Template matching needs temporal filtering**: Computer vision detections are noisy frame-to-frame
2. **Majority voting is powerful**: Simple technique that dramatically improves robustness
3. **Validation logic matters**: Preventing backward jumps eliminated a whole class of bugs
4. **Test with edge cases**: Multi-digit numbers revealed issues that single digits didn't show

## Future Improvements

Potential enhancements (not needed now, but possible):
1. **Adaptive threshold**: Lower threshold when confidence is consistently high
2. **Digit spacing validation**: Check that "1" and "0" in "10" are properly spaced
3. **Confidence scoring**: Weight majority voting by template match confidence
4. **Lap prediction**: Use lap time history to predict when next lap should occur

For now, the temporal smoothing solution is robust and efficient. ✅

