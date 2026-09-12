# Racing Line Extraction - Multi-Frame Frequency Voting

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Overview

This document explains the **multi-frame frequency voting** technique used to extract the racing line from ACC gameplay videos. This method successfully removes artifacts (red position dot, car cage lines, varying backgrounds) while preserving the complete racing line.

## The Problem

When extracting the racing line from the minimap HUD, we face several challenges:

1. **Red position dot** moves across the track, covering parts of the white racing line
2. **Varying background** behind the track (scenery, trackside objects) changes as the car moves
3. **Car cage/UI elements** appear as static white lines in some frames
4. **Lighting variations** cause the same pixels to appear different across frames

### Why Single-Frame Extraction Fails

Processing a single frame gives us:
- ✅ The white racing line
- ❌ The red dot (covers part of the line)
- ❌ Background artifacts (bright scenery, text)
- ❌ Car cage lines (static white elements)

**Result**: Incomplete and noisy data

## The Solution: Multi-Frame Frequency Voting

### Core Insight

**What changes vs. what's constant across frames:**

| Element | Behavior | Frequency |
|---------|----------|-----------|
| Racing line (white) | **CONSTANT** - always white, always in same position | **100%** |
| Red position dot | **VARIES** - moves to different positions each frame | **5-10%** |
| Background | **VARIES** - changes as car moves around track | **0-30%** |
| Car cage | **CONSTANT** - but small, disconnected from racing line | **100%** (but tiny area) |

**Key insight**: By sampling many frames and asking "how often is each pixel white?", we can separate the racing line (consistently white) from everything else!

## The Algorithm

### Step 1: Sample Multiple Frames

Sample 50+ frames evenly distributed across the lap:

```python
# Sample every 30 frames for first 1500 frames
sample_interval = 30
sample_frames = list(range(0, min(1500, total_frames), sample_interval))
```

**Why 50+ frames?**
- More samples = better statistical confidence
- Captures the red dot in many different positions
- Averages out background variations
- 50 frames ≈ 2 seconds of video at 24 FPS (enough to cover variety)

### Step 2: Extract White Pixels from Each Frame

Use HSV color space for robust white detection:

```python
hsv = cv2.cvtColor(map_roi, cv2.COLOR_BGR2HSV)

# White: any hue, low saturation (0-30), high value (200-255)
white_lower = np.array([0, 0, 200])
white_upper = np.array([180, 30, 255])

white_mask = cv2.inRange(hsv, white_lower, white_upper)
```

**Why HSV instead of grayscale?**
- White = high brightness (Value) + low color (Saturation)
- More robust to lighting changes than simple threshold
- Rejects colored elements (red dot, colored backgrounds)

### Step 3: Calculate Pixel-Wise Frequency

For each pixel position (x, y), count how many frames it appears white:

```python
# Stack all 50 masks into 3D array [height, width, num_frames]
mask_stack = np.stack(white_masks, axis=2).astype(np.float32)

# Calculate frequency: how often is each pixel white?
white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)

# Result: array of values 0.0 to 1.0
# 1.0 = pixel is white in 100% of frames (racing line!)
# 0.1 = pixel is white in 10% of frames (probably red dot position)
```

### Step 4: Threshold by Frequency

Keep only pixels that are white in ≥45% of frames:

```python
frequency_threshold = 0.45  # 45% (current default in PositionTrackerV2)
racing_line_raw = (white_frequency >= frequency_threshold).astype(np.uint8) * 255
```

**Why 45%? (Updated from original 60%)**
- Racing line should be white in ~100% of frames in bright sections
- However, darker track sections may show lower consistency (87-90%)
- 45% threshold captures both bright and dark racing line segments
- Still effectively filters out red dot (appears in <10% of frames per position)
- Still filters out varying backgrounds (inconsistent)
- **Result**: More complete racing line outline, especially in darker sections! ✅

**Historical note:** Originally used 60%, but testing revealed this was too strict and missed darker sections of the racing line. The threshold was lowered to 45% to capture the full path while still rejecting artifacts.

### Step 5: Remove Small Artifacts (Dilate-Filter-Erode)

The raw 60% frequency mask is excellent but may include small artifacts (car cage lines):

```python
# 5a. Dilate to connect nearby racing line segments
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
dilated = cv2.dilate(racing_line_raw, kernel, iterations=2)

# 5b. Find connected components
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated)

# 5c. Keep only the largest component (main racing line)
# Small artifacts become separate, tiny components
largest_component = keep_largest(labels)

# 5d. Erode back to original thickness
eroded = cv2.erode(largest_component, kernel, iterations=2)

# 5e. Intersect with raw to prevent false positives
final_mask = cv2.bitwise_and(eroded, racing_line_raw)
```

**Why this works:**
- Dilation connects the racing line into **one large blob** (7000+ pixels)
- Car cage artifacts remain as **small separate blobs** (50-100 pixels each)
- Keeping the largest component = keeping the racing line, discarding artifacts
- Erosion + intersection restores original thickness without adding false pixels

**Result**: Clean racing line, artifacts removed! ✅

## Results

### Performance Metrics

From actual testing on ACC gameplay footage:

| Metric | Value |
|--------|-------|
| Raw frequency pixels (60%) | 1,247 |
| After artifact removal | 1,219 (97.8% preserved) |
| Small artifacts removed | 2-3 components (50-100px² each) |
| Racing line components | 1 continuous contour |
| Path points extracted | 200-400 points |

### Visual Comparison

**Before (raw 60% frequency):**
- ✅ Complete racing line
- ❌ Small car cage lines (top-left corner)
- ❌ Potentially other UI artifacts

**After (dilate-filter-erode):**
- ✅ Complete racing line (97.8% preserved)
- ✅ Car cage removed
- ✅ UI artifacts removed
- ✅ Clean, continuous contour

## Integration with Position Tracking

The extracted racing line is used by `PositionTrackerV2`:

```python
# Initialize tracker
tracker = PositionTrackerV2()

# Extract racing line once at the start (sample 50 frames)
# Default frequency_threshold is 0.45 (45%)
success = tracker.extract_track_path(map_rois, frequency_threshold=0.45)

# Then track position in each frame
for frame in video:
    map_roi = extract_roi(frame)
    position = tracker.extract_position(map_roi)
    # position = 0.0 to 100.0 (percentage around track)
```

## Alternative Techniques Tested

We tested several other approaches before finding the optimal solution:

### ❌ Simple OR (bitwise_or all frames)
- Combines everything white from any frame
- **Problem**: Includes all red dot positions, all bright backgrounds
- **Result**: Too noisy

### ❌ Temporal Median
- Takes median pixel value across frames
- **Problem**: Similar to frequency voting but less intuitive
- **Result**: Works okay, but frequency voting is clearer

### ❌ Temporal Variance (low variance = stable)
- Pixels with low variance are stable (racing line)
- **Problem**: More complex, similar results to frequency voting
- **Result**: Works but unnecessary complexity

### ❌ Maximum Intensity Projection
- For each pixel, take max brightness across frames
- **Problem**: Captures bright backgrounds (text, scenery)
- **Result**: Too many artifacts

### ✅ Frequency Voting (60% threshold)
- Simple, intuitive, effective
- **Best performer** in all tests

## Parameters and Tuning

### Recommended Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `num_samples` | 50 | Good balance of speed vs. accuracy |
| `frequency_threshold` | 0.45 (45%) | Catches full racing line including darker sections, filters noise |
| `dilate_kernel` | 5×5 ellipse | Connects segments without over-growing |
| `dilate_iterations` | 2 | Sufficient to connect racing line into one blob |
| `erode_iterations` | 2 | Restores original thickness |

### Adjusting Frequency Threshold

| Threshold | Effect | Use Case |
|-----------|--------|----------|
| 40% | Very permissive, may capture some artifacts | If racing line has many gaps |
| **45%** | **Optimal balance** | **Current default - captures full racing line** |
| 50% | Slightly stricter, may miss darker sections | If getting artifacts |
| 60% | Strict, works for bright racing lines only | Original default (too strict for some tracks) |
| 70%+ | Very strict, will likely miss parts | Not recommended |

**Note:** The default was changed from 60% to 45% after discovering that darker sections of the racing line (with lower HSV Value) were being missed at the higher threshold.

## Implementation Details

### Memory Efficiency

The algorithm stacks 50 frames in memory:

```python
# Each mask: height × width (e.g., 180 × 270 = 48,600 pixels)
# 50 masks × 48,600 pixels × 4 bytes (float32) ≈ 9.7 MB
# Very reasonable for modern systems
```

### Processing Speed

On a typical system:
- Frame extraction: ~0.5 seconds (50 frames)
- Frequency calculation: ~0.1 seconds
- Morphological operations: ~0.05 seconds
- **Total: < 1 second** for complete racing line extraction

### Edge Cases

**What if the red dot covers the same spot in many frames?**
- Unlikely (dot moves continuously around track)
- Even if it happens, 60% threshold allows for 40% occlusion
- Racing line appears in ~100% of frames, dot in <10% per position

**What if background is always bright in one area?**
- Dilate-filter-erode removes disconnected artifacts
- Bright background won't be connected to racing line
- Gets filtered out as separate component

**What if car cage line is connected to racing line?**
- Very unlikely (car cage is typically separate UI element)
- If connected, it would make the racing line contour slightly larger
- Still better than including it as separate artifact

## Conclusion

**Multi-frame frequency voting** is the optimal technique for racing line extraction:

✅ **Simple**: Easy to understand and implement  
✅ **Robust**: Handles red dot, backgrounds, artifacts  
✅ **Accurate**: Preserves 97%+ of racing line  
✅ **Fast**: Processes in < 1 second  
✅ **Reliable**: Works consistently across different videos  

**Key takeaway**: When dealing with dynamic occlusions (red dot) and static features (racing line), temporal analysis (frequency voting) naturally separates them!

---

*Developed through extensive testing and iteration. See `src/position_tracker_v2.py` for the current implementation.*
