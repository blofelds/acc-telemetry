# Template Matching Guide

> **Historical document:** Describes an intermediate ACC lap-number template path. Competizione `extract_lap_number()` uses **tesserocr** (pytesseract fallback). Assetto Corsa original uses `reader: assetto_corsa` glyph templates for speed and lap (`templates/speed_digits/`) and gear (`templates/gear_digits/`). Prefer [USER_GUIDE.md](USER_GUIDE.md) and [FEATURES.md](FEATURES.md).

## Summary: OCR Replacement Complete!

**Template matching** has replaced Tesseract OCR for lap number detection:
- **Speed**: ~1.5ms vs ~100ms = **67x faster** ⚡
- **Accuracy**: Equal or better (templates are exact matches)
- **Reliability**: No more OCR sampling issues or hash detection problems

## What is Template Matching?

Template matching is like "Where's Waldo?" for computers:

1. **Template**: Small reference image of what you're looking for (e.g., digit "2")
2. **Search**: Slide the template across target image pixel-by-pixel
3. **Compare**: Calculate similarity at each position
4. **Match**: Highest similarity = best match

```
Template (digit "2"):     Target (lap "22"):      Result:
  ████                      ████  ████              Found "2" + "2"
  ████                      ████  ████              = Lap 22!
      █         →slide          █      █            Confidence: 0.95
  ████          across      ████  ████              Time: 1.5ms
  ████                      ████  ████
```

## Architecture: One Core, Multiple Uses

```
TemplateMatcher (universal core class)
    │
    ├── templates/lap_digits/      → Lap numbers (DONE ✅)
    ├── templates/speed_digits/    → Speed detection (FUTURE)
    ├── templates/gear_digits/     → Gear detection (FUTURE)
    └── templates/time_digits/     → Lap times (FUTURE)
```

**Key insight**: Same matching logic, different template sets!

Different HUD elements use different fonts/sizes, so you need separate templates, but the **matching code is reusable**.

## Current Implementation

### Files:
- **`src/template_matcher.py`**: Universal template matching core
- **`src/lap_detector.py`**: Uses TemplateMatcher for lap numbers, OCR for lap times

### What Changed:
1. ❌ **Removed**: Tesseract OCR for lap numbers (slow, unreliable)
2. ✅ **Added**: Template matching for lap numbers (fast, accurate)
3. ✅ **Kept**: OCR for lap times (only runs on transitions, so performance is fine)

### Performance Comparison:

| Method | Time per Frame | Notes |
|--------|---------------|-------|
| **Old (OCR)** | ~100ms | Way too slow |
| **New (Template)** | ~1.5ms | **67x faster!** ⚡ |

For a 30-minute video (54,000 frames):
- **Old**: 54,000 × 100ms = 90 minutes processing
- **New**: 54,000 × 1.5ms = **81 seconds** (1.3 minutes)

## How to Use

### Step 1: Create Templates (One-Time Calibration)

You need to extract digit images (0-9) from your video and save them as templates.

#### Method A: Automatic Extraction Helper

```bash
cd /Users/jakub.cieply/Personal/acc-telemetry
python -m src.template_matcher
```

This will:
1. Extract frames you specify
2. Save debug images to `templates/debug_lap/`
3. You manually crop individual digits
4. Save to `templates/lap_digits/[0-9].png`

#### Method B: Manual Extraction

1. **Find frames with different lap numbers:**
```python
import cv2

cap = cv2.VideoCapture('videos/your_video.mp4')

# Frame 150 shows lap 22
cap.set(cv2.CAP_PROP_POS_FRAMES, 150)
ret, frame = cap.read()

# Extract lap number ROI
lap_roi = frame[71:108, 237:284]
cv2.imwrite('lap_22.png', lap_roi)

# Manually crop and save each digit
# lap_22.png → crop left half → save as templates/lap_digits/2.png
#           → crop right half → save as templates/lap_digits/2.png
```

2. **Find frames covering all digits 0-9:**

| Digit | Example Lap | Where to Find |
|-------|-------------|---------------|
| 0 | 10, 20, 30 | Most races |
| 1 | 1, 10-19, 21, 31 | Early laps |
| 2 | 2, 12, 20-29, 32 | Common |
| 3 | 3, 13, 23, 30-39 | Mid race |
| 4 | 4, 14, 24, 34, 40+ | Common |
| 5 | 5, 15, 25, 35, 45+ | Common |
| 6 | 6, 16, 26, 36, 46+ | Later laps |
| 7 | 7, 17, 27, 37, 47+ | Later laps |
| 8 | 8, 18, 28, 38, 48+ | Later laps |
| 9 | 9, 19, 29, 39, 49+ | Later laps |

3. **Save templates:**
```
templates/
  └── lap_digits/
      ├── 0.png  (white digit on black background)
      ├── 1.png
      ├── 2.png
      ├── 3.png
      ├── 4.png
      ├── 5.png
      ├── 6.png
      ├── 7.png
      ├── 8.png
      └── 9.png
```

### Step 2: Run Telemetry Extraction

```bash
python main.py
```

That's it! If templates exist, lap detection will automatically use them.

### Example Output:

```
⚡ Lap Detection Performance:
   Method: Template Matching
   Total frames: 54000
   Recognition calls: 54000
   Avg time per frame: 1.5ms
   Speedup vs OCR: 67x faster
```

## Troubleshooting

### No templates found

**Symptom:**
```
⚠️  Warning: No lap number templates found in templates/lap_digits/
   Run calibration first: python -m src.template_matcher
```

**Solution:** Create templates following Step 1 above.

### Lap numbers not detected

**Symptom:** `lap_number` column is all None

**Causes & Solutions:**

1. **Templates don't match video:**
   - Different resolution → recreate templates for your resolution
   - Different video quality → lower recognition threshold in `template_matcher.py`

2. **ROI coordinates wrong:**
   - Verify lap number ROI in `config/roi_config.yaml`
   - Extract a test frame and check coordinates

3. **Templates not preprocessing correctly:**
   - Templates should be white digits on black background
   - Check threshold value (currently 180) in `save_template()`

### Low accuracy

**Symptom:** Recognizes wrong numbers or None frequently

**Solutions:**

1. **Lower threshold:**
```python
# In src/lap_detector.py, line ~101
lap_number = self.lap_matcher.recognize_number(white_mask, max_digits=2)

# Change to more lenient threshold:
lap_number = self.lap_matcher.recognize_number(white_mask, max_digits=2, threshold=0.5)
```

2. **Better templates:**
   - Extract from clearer frames
   - Use multiple samples per digit
   - Ensure templates are sharp and high-contrast

3. **Adjust preprocessing:**
```python
# In src/lap_detector.py, lines 90-93
# Try different threshold values
lower_white = np.array([0, 0, 170])  # Lower from 180
upper_white = np.array([180, 60, 255])  # Increase saturation tolerance
```

## Future: Speed & Gear Detection (historical)

> **Note:** Assetto Corsa original speed and gear already use glyph templates
> (`AcSpeedReader` / `AcGearReader`). Competizione speed and gear stay on
> tesserocr. The sketch below was an earlier ACC plan and is not the current path.

The same template matching approach will work for speed and gear:

### Speed Detection (3 digits, e.g., "240"):
```python
speed_matcher = TemplateMatcher('templates/speed_digits/')
speed = speed_matcher.recognize_number(speed_roi, max_digits=3)
```

### Gear Detection (1 digit, 1-6):
```python
gear_matcher = TemplateMatcher('templates/gear_digits/')
gear = gear_matcher.recognize_digit(gear_roi)
```

### Steps:
1. Find ROI coordinates for speed/gear in HUD
2. Extract digit templates from frames
3. Create `SpeedDetector` and `GearDetector` classes in `main.py`
4. Extract on every frame (now fast enough!)

## Template Requirements

### Good Template:
```
✅ White digit on black background
✅ Clean edges, no artifacts
✅ Consistent size (~20-40px wide)
✅ High contrast
✅ Centered in image
```

### Bad Template:
```
❌ Gray/colored digit
❌ Noisy background
❌ Too small (<15px) or too large (>60px)
❌ Low contrast
❌ Off-center or cropped
```

## Technical Details

### Preprocessing Pipeline:

1. Extract ROI from frame
2. Convert BGR → HSV color space
3. Isolate white pixels (value > 180, saturation < 50)
4. Apply morphological operations (remove noise)
5. Template matching on cleaned binary image

### Matching Algorithm:

- **Method**: `cv2.TM_CCOEFF_NORMED` (Normalized Cross-Correlation)
- **Threshold**: 0.6 (60% similarity required)
- **Multi-digit**: Tries whole ROI first, then splits if needed

### Why It's Fast:

- **Small ROI**: Only ~47×37 pixels for lap numbers
- **Binary images**: Simple black/white, no color processing
- **Optimized OpenCV**: Uses SIMD instructions, highly optimized C++ code
- **No AI/ML**: Direct pixel comparison, no neural networks

## Comparison: Template Matching vs OCR

| Aspect | Template Matching | Tesseract OCR |
|--------|------------------|---------------|
| **Speed** | ~1-2ms | ~50-200ms |
| **Accuracy** | 95-99% (with good templates) | 80-95% |
| **Setup** | One-time template creation | None |
| **Flexibility** | Fixed fonts only | Any text |
| **Dependencies** | OpenCV only | Tesseract + pytesseract |
| **Best for** | Simple digits/numbers | Complex text |

## When to Use Each:

### Use Template Matching:
- ✅ Simple digits (lap numbers, speed, gear)
- ✅ Fixed font/style
- ✅ Per-frame extraction needed
- ✅ Performance critical

### Use OCR:
- ✅ Complex text (lap times with colons/dots)
- ✅ Variable fonts
- ✅ Infrequent extraction (transitions only)
- ✅ Unknown text content

---

**Status (historical):** This guide described template matching as the ACC lap default. Competizione lap numbers now use tesserocr; Assetto Corsa original uses glyph templates for speed, lap, and gear.



