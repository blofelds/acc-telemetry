# Lap Detection Fix - October 22, 2024

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Problem
Lap numbers were not being saved correctly in the CSV output. Only sporadic laps appeared (1, 5, 23, 195) instead of continuous progression (0, 1, 2, 3...).

## Root Causes

### 1. Lap 0 Rejection
- **Issue**: Validation only allowed lap numbers 1-999, rejecting lap 0
- **Impact**: Pre-race warmup lap (lap 0) was never saved
- **Fix**: Changed validation to allow 0-999

### 2. OCR Misreads Being Accepted
- **Issue**: Old validation logic accepted large jumps (e.g., lap 1 → lap 5)
- **Impact**: OCR errors were saved as valid lap numbers, corrupting the sequence
- **Fix**: Only accept lap increments of exactly +1 (reject jumps > 1 and backward jumps)

### 3. Insufficient Temporal Smoothing
- **Issue**: 5-frame history with 60% consensus wasn't enough to filter OCR noise
- **Impact**: OCR inconsistently read digits (e.g., "1" sometimes read as "5")
- **Fix**: Increased to 15-frame history with 70% consensus requirement

## Changes Made

### src/lap_detector.py

1. **Lap 0 Support** (line 165):
   ```python
   # Before: if 1 <= lap_number <= 999:
   # After:
   if 0 <= lap_number <= 999:
   ```

2. **Stricter Validation** (lines 177-194):
   - Only accept lap_diff == 1 (normal progression)
   - Reject lap_diff > 1 (OCR errors like 1→5)
   - Reject lap_diff < 0 (backward jumps like 3→2)

3. **Improved Smoothing** (lines 63, 229):
   ```python
   # Before: _history_size = 5, 60% consensus
   # After:
   _history_size = 15  # ~0.6 seconds at 24fps
   if count >= max(len(self._lap_number_history) * 0.7, 3):  # 70% consensus
   ```

4. **Removed Debug Logging**:
   - Cleaned up verbose OCR and validation debug prints
   - Kept performance stats functionality intact

## Results

### Before Fix
```
Lap 1.0: 2,118 frames
Lap 5.0: 3,429 frames
Lap 23.0: 491 frames
Lap 25.0: 31 frames
Lap 195.0: 61,071 frames
```

### After Fix
```
Laps 0-27 detected continuously
All transitions smooth (0→1, 1→2, 2→3, etc.)
No missing laps, no spurious jumps
```

## Technical Details

### How Smoothing Works
1. OCR runs on every frame (~24 fps)
2. Each OCR result is added to a 15-frame rolling history
3. Majority voting: take the most common value in history
4. Require 70% agreement (11 out of 15 frames) to accept new value
5. This filters out temporary OCR misreads while allowing genuine lap transitions

### Why OCR Misreads Occur
- Video compression artifacts
- Motion blur during camera movement
- Similar digit shapes (1 vs 7, 3 vs 8, 0 vs 8)
- Lighting changes on the HUD
- Anti-aliasing on white text against red background

### Why Stricter Validation is Safe
- In racing, laps always increment by exactly 1
- You cannot skip laps (1 → 3 is impossible)
- Laps never go backward (3 → 2 is impossible)
- Session resets would start from lap 0 again (handled separately if needed)

## Performance Impact
- Processing time: ~same (OCR already ran on every frame)
- Accuracy: Significantly improved
- Stability: Much more robust to OCR noise

## Future Improvements
- Consider using template matching instead of OCR for lap numbers (100x faster, more accurate)
- Add session detection (practice → qualifying → race transitions)
- Implement lap time validation (reject impossible lap times)

