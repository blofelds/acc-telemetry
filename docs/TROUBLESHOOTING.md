# Troubleshooting Guide

This document consolidates solutions to common issues, bug fixes that were implemented, and lessons learned during development.

## Quick Diagnosis

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| All values 0% or 100% | ROI coordinates wrong | Check video resolution, adjust config |
| No lap numbers detected | ROI doesn't capture lap indicator | Verify lap_number ROI coordinates |
| Lap numbers oscillating | (Fixed) Temporal smoothing issue | Update to latest version |
| False throttle during braking | (Fixed) Pixel threshold too low | Update to latest version |
| Position jumps erratically | Red dot detection failing | Check track_map ROI, verify minimap visible |
| Slow processing | Using pytesseract | Install tesserocr for 29x speedup |
| Video file not found | Wrong path/name | Place `.mp4` files in `videos/` and select in `main.py` |

## Resolution and ROI Issues

### Problem: Wrong Video Resolution

**Symptoms:**
- Telemetry values stuck at 0% or 100%
- No data extracted
- ROI debug images show wrong parts of screen

**Root Cause:**
ROI coordinates in `config/roi_config.yaml` are calibrated for 1280×720 (720p) videos. If your video is a different resolution, coordinates won't match HUD elements.

**Solution:**

1. **Check your video resolution:**
```bash
python -c "import cv2; cap=cv2.VideoCapture('your_video.mp4'); print(f'{int(cap.get(3))}x{int(cap.get(4))}')"
```

2. **Scale ROI coordinates:**
   - **1920×1080 (1080p)**: Multiply all x, y, width, height by 1.5
   - **2560×1440 (1440p)**: Multiply by 2.0
   - **3840×2160 (4K)**: Multiply by 3.0

3. **Manual calibration** (if scaling doesn't work):
```bash
# Extract a frame
python -c "import cv2; cap=cv2.VideoCapture('video.mp4'); ret,f=cap.read(); cv2.imwrite('frame.png',f)"
```
   - Open `frame.png` in image viewer with pixel coordinates (GIMP, Photoshop, Preview with Developer Tools)
   - Locate HUD elements (throttle bar bottom-right, lap number top-left)
   - Measure x, y, width, height for each element
   - Update `config/roi_config.yaml`

## Lap Detection Issues

### Historical Bug Fix: Lap Number Oscillations (Solved)

**Problem as it appeared:**
- Lap numbers flickering between values (10↔11, 20↔21)
- 89 lap transitions detected instead of 27 actual laps
- Visualization showed multiple lap markers in rapid succession
- Specific to two-digit numbers (10, 11, 20, 21)

**Real-world example from telemetry data:**
```
Frame 27096: Lap 11
Frame 27097: Lap 10  ← Oscillation!
Frame 27098: Lap 10
Frame 27230: Lap 11
Frame 27242: Lap 10  ← Oscillation again!
```

**Root Cause Analysis:**

Template matching was finding partial matches:
1. Frame N: Detects "1" and "0" correctly → "10"
2. Frame N+1: Only finds "1" with high confidence → "1" (misdetected as single digit)
3. Frame N+2: Finds "1" and "0" again → "10"

Why this happened:
- Template matching threshold too low (0.6)
- No temporal smoothing (each frame independent)
- Validation allowed backward jumps (-1)

**Solutions Implemented:**

1. **Temporal Smoothing with Majority Voting:**
   - Track last 5 frame detections
   - Use Counter to find most common value
   - Require 60% agreement (3/5 frames) to accept
   - If no consensus, keep previous lap number

2. **Stricter Validation Logic:**
```python
# Before (broken):
if abs(lap_number - last_lap) > 1:
    return last_lap  # Reject jumps > 1

# After (fixed):
lap_diff = smoothed_lap - last_lap
if lap_diff == 0:
    return last_lap  # No change
elif lap_diff == 1:
    return smoothed_lap  # Normal progression
elif lap_diff > 1:
    return smoothed_lap  # Allow session resets
else:
    return last_lap  # Reject backward jumps (lap_diff < 0)
```

3. **Higher Template Matching Threshold:**
   - Increased from 0.6 to 0.65
   - More strict matching reduces false positives

**Result:**
- 31 oscillations eliminated
- Clean lap transitions at all lap numbers
- Accurate lap count (27 laps detected correctly)

**Key Lesson:** Temporal filtering is essential for computer vision. Single-frame detections are noisy - requiring consistency across multiple frames dramatically improves robustness.

**Test approach:** Inspect lap transitions in the exported CSV (or write a small script that flags where `lap_number` decreases). The former standalone `test_lap_stability.py` script is no longer in the repo.

### Historical Bug Fix: Lap 0 Rejection and Large Jumps (Solved)

**Problem as it appeared:**
- Only sporadic laps saved to CSV (1, 5, 23, 195)
- Missing continuous progression (0, 1, 2, 3...)
- Pre-race warmup lap (lap 0) never saved

**Root Causes:**

1. **Lap 0 Rejection:**
   - Validation only allowed 1-999, rejecting lap 0
   - Pre-race warmup lap was lost

2. **OCR Misreads Accepted:**
   - Old validation accepted large jumps (lap 1 → lap 5)
   - OCR occasionally misread digits (1 looked like 5)
   - Corrupted the lap sequence

3. **Insufficient Temporal Smoothing:**
   - 5-frame history with 60% consensus not enough
   - OCR inconsistently read similar digits

**Solutions Implemented:**

1. **Lap 0 Support:**
```python
# Before: if 1 <= lap_number <= 999:
# After:
if 0 <= lap_number <= 999:
```

2. **Stricter Validation:**
   - Only accept lap increments of exactly +1
   - Reject jumps > 1 (OCR errors)
   - Reject backward jumps completely

3. **Improved Smoothing:**
   - Increased history from 5 to 15 frames (~0.6s at 24fps)
   - Increased consensus from 60% to 70%
   - Requires 11 out of 15 frames to agree

**Result:**
- Laps 0-27 detected continuously
- All transitions smooth (0→1, 1→2, 2→3, etc.)
- No missing laps, no spurious jumps

**Why OCR Misreads Occur:**
- Video compression artifacts
- Motion blur during camera movement
- Similar digit shapes (1 vs 7, 3 vs 8, 0 vs 8)
- Anti-aliasing on white text against red background

**Key Lesson:** In racing, laps always increment by exactly 1. Use domain knowledge to validate data - impossible sequences should be rejected.

## Telemetry Extraction Issues

### Historical Bug Fix: False Throttle Readings (Solved)

**Problem as it appeared:**
- Throttle showing 65-67% during heavy braking (brake 99-100%)
- Expected 3 throttle blips during downshifting, detected 6 blips
- Only 10-19 pixels detected in throttle ROI

**Root Cause:**

Horizontal bar detection algorithm was detecting UI text artifacts:
- On-screen text overlay "TC: 37 10" (traction control indicator)
- Small amounts of green pixels from text characters
- Algorithm found pixels at column 66-67 and calculated:
  ```
  percentage = (67 / 103) * 100 = 65%
  ```
- Even though only 10-19 pixels detected (vs 600-1200+ for real throttle)

**Visual Evidence:**
Debug images showed tiny green pixels around text characters within the throttle ROI boundaries - not actual throttle bar, just UI overlay artifacts.

**Solutions Implemented:**

1. **Minimum Pixel Threshold (Initial):**
```python
total_detected_pixels = np.count_nonzero(mask)
min_pixels_threshold = 50  # Initial threshold

if total_detected_pixels < min_pixels_threshold:
    return 0.0  # Filter out noise
```
   - **Result**: Eliminated some false readings, still detected 6 blips instead of 3

2. **Increased Pixel Threshold (Final):**
```python
min_pixels_threshold = 150  # Increased from 50 to 150
```

**Rationale:**
| Detection Type | Pixel Count | Status |
|---------------|-------------|---------|
| Real throttle bar | 300-1200+ | Valid ✅ |
| Throttle blip (downshift) | 300-700 | Valid ✅ |
| UI text artifacts | 10-100 | Filtered ❌ |
| Partial throttle release | 200-400 | Valid ✅ |

**Result:**
- ✅ Eliminated false 65% throttle readings during pure braking
- ✅ Reduced 6 false blips to 3 real downshift blips
- ✅ Still captures actual throttle blips accurately

**Verification:**
```
Before Fix:
  Frame 61-63: Throttle 65% (10-12 pixels) - FALSE
  Frame 67-70: Throttle 65% (14-19 pixels) - FALSE
  Frame 94-105: Throttle 45% (50-67 pixels) - FALSE
  Total blips detected: 6

After Fix:
  Frame 61-63: Throttle 0% - CORRECT
  Frame 67-70: Throttle 0% - CORRECT
  Frame 94-105: Throttle 0% - CORRECT
  Total blips detected: 3 (matching actual downshifts)
```

**Note on Throttle Blipping:**
The 3 detected throttle blips during braking are **legitimate**:
- Console ACC (and PC ACC) applies automatic throttle blip during downshifts
- This matches rev-matching technique (heel-toe)
- Blips occur at ~0.15-0.2s intervals, matching human shift timing
- Peak throttle of 45-67% is appropriate for rev-matching

**Key Lesson:** Computer vision needs robust filtering. Presence of colored pixels isn't enough - you need sufficient quantity to confirm signal validity.

## Position Tracking Issues

### Problem: Position Always Returns 0.0

**Symptoms:**
- `track_position` column all zeros in CSV
- Position-based comparison fails
- No position data extracted

**Possible Causes & Solutions:**

**1. Track path extraction failed:**
- Verify `track_map` ROI in `config/roi_config.yaml` captures the minimap
- Check debug images under `debug/` if you save map samples during development
- Ensure the minimap is visible and not hidden by overlays
- Run unit tests: `python tests/test_position_tracker_v2.py`

**2. HSV color ranges need adjustment:**

If racing line is very dark or has unusual color:
```python
# In src/position_tracker_v2.py, adjust these values:
white_lower = np.array([0, 0, 180])  # Lower from 200 if line is dark
white_upper = np.array([180, 40, 255])  # Increase saturation tolerance if needed
```

**3. Frequency threshold too strict:**

The racing line extraction uses multi-frame frequency voting. Default threshold is 45% (pixel must be white in 45% of sampled frames).

If racing line has gaps:
```python
# In main.py or position_tracker_v2.py:
tracker.extract_track_path(map_rois, frequency_threshold=0.40)  # Lower from 0.45
```

**Historical Context:**
- Original threshold was 60% (too strict, missed darker sections)
- Lowered to 45% to capture full racing line including dark segments
- Still effectively filters red dot (<10% per position) and backgrounds

### Problem: Position Jumps Erratically

**Symptoms:**
- Large jumps in position between consecutive frames
- Time delta spikes in comparison graphs
- Unreliable position data

**Root Causes & Solutions:**

**1. Red dot detection unreliable:**
- Save minimap ROI crops to `debug/` and inspect whether the red dot is visible
- Check if the minimap is obscured
- Adjust HSV ranges for red detection in `src/position_tracker_v2.py` if needed
- Run: `python tests/test_position_tracker_v2.py`

**2. Path is incomplete (gaps in racing line):**

Check `extracted_path.png` - does path cover full track?

If there are gaps:
- Increase number of sampled frames for path extraction
- Lower frequency threshold (currently 45%)
- Sample more frames: Edit `sample_frames` list in main.py

**3. Single-frame glitches:**

**Historical Context:** This was a major issue that led to two solutions being tried:

**Solution 1 (Implemented, then replaced): Kalman Filtering**

We implemented industry-standard Kalman filtering using FilterPy:
- Model: 1D Kalman filter tracking [position, velocity]
- Outlier rejection: Reject measurements with >10% innovation
- **Result**: Successfully eliminated glitches ✅

**Why it was replaced:**
- Worked perfectly but added unnecessary complexity
- Required FilterPy dependency
- Required understanding of state estimation, covariance matrices
- For post-processing video, a simpler solution was sufficient

**Solution 2 (Current): Simple Forward-Progress Validation**

```python
# In src/position_tracker_v2.py:
max_jump_per_frame = 1.0  # Maximum 1% position change per frame

if abs(new_position - last_position) > max_jump_per_frame:
    return last_position  # Use last valid value
else:
    return new_position
```

**Result**: Equally effective at rejecting glitches, much simpler ✅

**Key Lesson:** Sometimes the sophisticated solution (Kalman filtering) works great, but a simpler solution achieving the same practical goal is preferable. The Kalman implementation is preserved in git history as a learning artifact.

### Problem: Position Doesn't Reset at Lap Transitions

**Symptoms:**
- Position goes from ~100% to ~0% at lap transitions
- Looks like it doesn't "reset"

**Explanation:**
This is **expected behavior**, not a bug!

Position algorithm handles wraparound automatically:
- When car crosses start/finish, position naturally progresses from 99.x% to 0.x%
- The `reset_for_new_lap()` method exists for reference but doesn't need to do anything
- No manual reset required

## Performance Issues

### Problem: Slow Processing

**Symptoms:**
- Processing takes much longer than video duration
- CPU usage high for extended periods
- Progress bar moves slowly

**Diagnosis:**

Check console output for performance breakdown:
```
⏱️ Performance Breakdown:
   Speed Extraction: 50.2ms avg (70% of total)  ← BOTTLENECK
   Telemetry Extraction: 4.1ms avg
```

**Common Causes & Solutions:**

**1. Using pytesseract instead of tesserocr:**

pytesseract spawns new process for each OCR call (~50ms overhead).

**Solution**: Install tesserocr for 29x speedup:
```bash
# macOS
brew install tesseract
pip install tesserocr

# Linux
sudo apt-get install tesseract-ocr libtesseract-dev
pip install tesserocr

# Windows
# Download tesseract installer from https://github.com/UB-Mannheim/tesseract/wiki
pip install tesserocr
```

**Performance comparison:**
- tesserocr: ~2ms per frame (29x faster)
- pytesseract: ~50ms per frame
- template matching: ~2ms per frame (but requires calibration)

**2. Very long videos:**

30+ minute videos with 40,000+ frames will take time even with optimal performance.

**Expected processing times** (with tesserocr):
- 10-minute video: ~1-2 minutes
- 30-minute video: ~5-8 minutes
- 60-minute video: ~10-15 minutes

**3. System resource constraints:**

- Close other applications
- Ensure adequate RAM (4GB+ recommended)
- Check CPU isn't thermal throttling

**Alternative: Template Matching for Lap Numbers**

If you process many videos regularly, template matching is fastest option:

1. **One-time calibration** (~20 minutes):
   - Extract digit templates from your video
   - Save to `templates/lap_digits/0-9.png`

2. **Use template matching** (automatic if templates exist):
   - Same 2ms performance as tesserocr
   - No dependencies needed
   - Works offline

See `TEMPLATE_MATCHING.md` for calibration guide.

## Visualization Issues

### Problem: HTML File Won't Open

**Symptoms:**
- Double-clicking HTML does nothing
- Browser shows blank page
- JavaScript errors in console

**Solutions:**

1. **Open with specific browser:**
   - Right-click → Open with → Chrome/Firefox
   - Some systems default to text editors for .html files

2. **Check file permissions:**
```bash
chmod 644 data/output/*.html
```

3. **Try different browser:**
   - Recommended: Chrome, Firefox
   - Safari works but may have minor rendering differences
   - Avoid Internet Explorer (not supported)

### Problem: Graphs Are Blank

**Symptoms:**
- HTML opens but no graphs visible
- Console shows JavaScript errors

**Diagnosis:**

1. **Check CSV has data:**
```bash
head data/output/telemetry_YYYYMMDD_HHMMSS.csv
wc -l data/output/telemetry_YYYYMMDD_HHMMSS.csv
```
Should show header + data rows, not empty.

2. **Check browser console** (F12 → Console tab):
   - Look for JavaScript errors
   - Plotly library errors indicate corruption

**Solutions:**

- Re-run `main.py` to regenerate files
- Try opening in different browser
- Check if antivirus is blocking JavaScript

### Problem: Slow Graph Performance

**Symptoms:**
- Graphs lag when zooming/panning
- Browser becomes unresponsive
- High CPU usage

**Cause:**
Very long videos (10+ minutes) have 18,000+ data points, which can stress browser rendering.

**Solutions:**

1. **Trim video to specific laps:**
```bash
# Extract 2-minute section starting at 1:30
ffmpeg -i videos/full_lap.mp4 -ss 00:01:30 -t 00:02:00 videos/clip.mp4
```

2. **Use faster browser:**
   - Chrome generally fastest for Plotly
   - Close other tabs to free resources

3. **Reduce data points** (advanced):
   - Downsample CSV to every Nth frame
   - Trade some resolution for performance

## Installation Issues

### Problem: Module Not Found

**Symptoms:**
```
ModuleNotFoundError: No module named 'cv2'
ModuleNotFoundError: No module named 'plotly'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import cv2; import plotly; print('OK')"
```

### Problem: tesserocr Installation Fails

**Symptoms:**
```
ERROR: Could not build wheels for tesserocr
```

**Solution (macOS):**
```bash
# Install tesseract first
brew install tesseract

# Then install tesserocr
pip install tesserocr
```

**Solution (Linux):**
```bash
sudo apt-get install tesseract-ocr libtesseract-dev
pip install tesserocr
```

**Fallback:**
If tesserocr won't install, the tool automatically falls back to pytesseract (slower but works):
```bash
pip install pytesseract
```

## Getting Help

If you encounter issues not covered here:

1. **Check console output** for error messages and stack traces
2. **Run with debug logging** (if available)
3. **Check file permissions** for input video and output directory
4. **Verify video file** is not corrupted (can you play it normally?)
5. **Review git history** for similar issues that were fixed
6. **Document your findings** - add to this troubleshooting guide!

## Summary of Historical Bug Fixes

This section chronicles major bugs that were discovered and fixed during development:

1. **Lap Number Oscillations** (Oct 2024)
   - Problem: Flickering between consecutive lap numbers
   - Solution: Temporal smoothing + stricter validation
   - Status: ✅ Fixed

2. **False Throttle Readings** (Oct 2024)
   - Problem: UI text artifacts detected as throttle input
   - Solution: Minimum pixel threshold (150 pixels)
   - Status: ✅ Fixed

3. **Lap 0 Rejection** (Oct 2024)
   - Problem: Pre-race warmup lap never saved
   - Solution: Allow lap numbers 0-999 (was 1-999)
   - Status: ✅ Fixed

4. **Position Glitches** (Oct 2024)
   - Problem: Single-frame position jumps causing time delta spikes
   - Solutions Tried: Kalman filtering (worked but complex)
   - Current Solution: Simple max_jump_per_frame threshold
   - Status: ✅ Fixed

5. **Incomplete Racing Line** (Oct 2024)
   - Problem: 60% frequency threshold missed dark track sections
   - Solution: Lowered to 45% threshold
   - Status: ✅ Fixed

All of these issues are resolved in the current version. The documentation preserves the journey to help understand why certain approaches were chosen.
