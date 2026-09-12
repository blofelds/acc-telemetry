# Lap Recognition Feature

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Overview

The lap recognition feature automatically detects lap numbers and lap times from ACC gameplay videos using OCR (Optical Character Recognition), enabling lap-by-lap analysis and comparison.

## How It Works

### 1. Lap Number Detection

The system extracts the lap number from the red flag icon in the top-left corner of the ACC HUD on every frame:

**ROI Configuration** (`config/roi_config.yaml`):
```yaml
lap_number:
  x: 237
  y: 71
  width: 47
  height: 37
```

- Uses **pytesseract** OCR with white text isolation
- Validates lap numbers (must be 1-999)
- Caches last valid lap number to handle OCR failures
- Detects transitions when lap number increases by 1

### 2. Lap Time Extraction

**Important**: The system extracts the **LAST lap time**, not the current lap time, because:
- Current lap time constantly changes during the lap
- LAST lap time only appears after completing a lap (in the first frames of the next lap)
- This gives us the accurate completed lap time

**ROI Configuration**:
```yaml
last_lap_time:
  x: 119
  y: 87
  width: 87
  height: 20
```

**Workflow**:
1. Detect lap transition (lap number changes from N to N+1)
2. Extract LAST lap time from the timing panel
3. Associate that lap time with the completed lap (N)

### 3. Data Structure

**CSV Output** includes new columns:
- `lap_number`: Integer lap number for each frame
- `lap_time`: Completed lap time in "MM:SS.mmm" format (only for completed laps)

**Example**:
```csv
frame,time,lap_number,lap_time,throttle,brake,steering
0,0.0,21,,45.2,0.0,0.12
100,3.34,21,,78.3,0.0,-0.24
...
3000,100.2,21,01:44.643,32.1,85.2,0.05  # Lap 21 complete, time captured
3001,100.23,22,,89.4,0.0,0.18            # Now in lap 22
...
```

## Usage

### Running Telemetry Extraction with Lap Detection

```bash
python main.py
```

The main pipeline now automatically:
1. Extracts lap numbers every frame
2. Detects lap transitions
3. Captures completed lap times
4. Adds lap information to CSV output
5. Shows lap statistics in summary

### Example Output

```
🏁 Detected 3 lap transitions:
   Lap 21 → 22 at 105.3s (time: 01:44.643)
   Lap 22 → 23 at 208.7s (time: 01:43.891)
   Lap 23 → 24 at 311.2s (time: 01:42.502)

🏁 Lap Summary:
   Total laps detected: 3
   Lap details:
      Lap 21: 105.30s
      Lap 22: 103.40s
      Lap 23: 102.50s
```

### Lap Comparison Visualization

Use the new `plot_lap_comparison()` method to overlay multiple laps:

```python
from src.interactive_visualizer import InteractiveTelemetryVisualizer
import pandas as pd

# Load telemetry data with lap numbers
df = pd.read_csv('data/output/telemetry_20251022_123456.csv')

# Create visualizer
viz = InteractiveTelemetryVisualizer()

# Compare laps 22, 23, and 24
viz.plot_lap_comparison(df, lap_numbers=[22, 23, 24])
```

**Features**:
- Each lap normalized to start at time=0
- Direct lap-to-lap comparison aligned by lap time
- Color-coded for easy identification
- Shows lap times in legend
- Interactive zoom/pan/hover

### Interactive Visualization with Lap Separators

The standard `plot_telemetry()` now automatically adds:
- **Vertical dashed lines** at lap transitions
- **Lap annotations** showing lap numbers
- Works with the full session view

## Files Modified/Created

### New Files
- `src/lap_detector.py` - LapDetector class with OCR logic
- `docs/LAP_RECOGNITION_FEATURE.md` - This documentation

### Modified Files
- `main.py` - Integrated LapDetector into processing pipeline
- `config/roi_config.yaml` - Added lap_number and last_lap_time ROIs
- `src/video_processor.py` - Exposes current_frame for OCR
- `src/interactive_visualizer.py`:
  - Enhanced `generate_summary()` with per-lap statistics
  - Added lap separators to `plot_telemetry()`
  - Added `plot_lap_comparison()` method
- `requirements.txt` - Added pytesseract==0.3.10

## Configuration

### ROI Coordinates (1280×720 video)

The default coordinates work for 1280×720 (720p) gameplay videos. If you have a different resolution:

**For 1920×1080 (1080p)**: Multiply all values by 1.5
```yaml
lap_number:
  x: 356    # 237 × 1.5
  y: 107    # 71 × 1.5
  width: 71  # 47 × 1.5
  height: 56 # 37 × 1.5
```

**For other resolutions**: Scale proportionally based on video dimensions.

### Finding ROI Coordinates

If OCR isn't working:

1. **Extract a frame**:
   ```python
   import cv2
   cap = cv2.VideoCapture('videos/your_video.mp4')
   ret, frame = cap.read()
   cv2.imwrite('test_frame.png', frame)
   cap.release()
   ```

2. **Open in image viewer** with pixel coordinates (GIMP, Photoshop, Preview)

3. **Locate elements**:
   - Lap number: Red flag with white number (top-left)
   - Last lap time: "LAST" timing text (below lap number)

4. **Update `config/roi_config.yaml`** with new coordinates

5. **Test and iterate** until OCR works reliably

## Edge Cases Handled

### Partial Laps
- **First lap**: May not have a completed lap time (video starts mid-lap)
- **Last lap**: Video might end before lap completes
- Both are included in data with `lap_time = None`

### OCR Failures
- Lap number caching: If OCR fails, uses last known good value
- Validation: Rejects unrealistic lap numbers or times
- Graceful degradation: If OCR completely fails, lap_number will be None

### Lap Time Mismatches
- Only extracts lap time at lap transitions
- Associates time with the **completed** lap, not the current lap
- Handles cases where LAST time isn't visible

## Performance Notes

- OCR adds ~10-15% overhead to processing time
- Lap number OCR runs every frame (necessary for transition detection)
- Lap time OCR only runs at transitions (minimal impact)
- Total processing time for 30-minute video: ~5-7 minutes

## Future Enhancements

### Planned Features
- [ ] Dropdown selector in HTML visualization to filter by lap
- [ ] Best lap highlighting in visualizations
- [ ] Sector time detection (if visible in HUD)
- [ ] Track map integration with lap position
- [ ] Automatic lap comparison (compare all laps to best lap)

### Known Limitations
- Requires consistent video resolution (can't mix different resolutions)
- Relies on ACC HUD being visible (won't work with HUD disabled)
- OCR accuracy depends on video quality (1080p recommended minimum)
- Only works with default ACC HUD layout

## Troubleshooting

### No lap numbers detected
**Symptom**: `lap_number` column is all None

**Solutions**:
1. Verify ROI coordinates with a test frame
2. Check video resolution matches configuration
3. Ensure ACC HUD is visible in video
4. Try increasing tesseract confidence thresholds

### Incorrect lap times
**Symptom**: Lap times don't match reality

**Solutions**:
1. Verify `last_lap_time` ROI captures only the LAST time display
2. Check OCR output with debug frames
3. Adjust OCR preprocessing (threshold, scale_factor)

### Missing lap transitions
**Symptom**: Lap number stays constant when it should change

**Solutions**:
1. Check if lap number ROI is correctly positioned
2. Increase OCR sampling frequency
3. Verify lap number validation isn't too strict

## Technical Details

### OCR Configuration

**Tesseract Settings**:
- Lap number: `--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789`
- Lap time: `--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789:.`

**Preprocessing**:
- HSV color space conversion for white text isolation
- Binary thresholding (threshold=200)
- 3x upscaling for better OCR accuracy
- Morphological operations to reduce noise

### Lap Time Format

Input: `"01:44.643"` (displayed in HUD)
Output: `"01:44.643"` (stored as string)

For calculations, use `LapDetector.get_lap_time_seconds()`:
```python
lap_time_seconds = lap_detector.get_lap_time_seconds("01:44.643")
# Returns: 104.643
```

## Dependencies

- **pytesseract** (Python wrapper for Tesseract OCR)
- **tesseract** (System-level OCR engine, installed via Homebrew on macOS)

Installation handled by:
```bash
brew install tesseract
pip install pytesseract==0.3.10
```

---

**Questions or issues?** Open an issue on the project repository or check the main README.md for contact information.

