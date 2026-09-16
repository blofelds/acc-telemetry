# ACC Telemetry Extractor - Technical Architecture

This document describes the technical architecture, implementation details, and the evolution of design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      main.py (Orchestrator)                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐   ┌──────────────────┐
│VideoProcessor│    │  LapDetector     │   │PositionTrackerV2 │
│ (Frame I/O)  │    │ (OCR/Templates)  │   │ (Minimap Track)  │
└──────────────┘    └──────────────────┘   └──────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                ┌──────────────────────────┐
                │  TelemetryExtractor      │
                │  (HSV Color Detection)   │
                └──────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────┐
                │ InteractiveTelemetry     │
                │ Visualizer (Plotly)      │
                └──────────────────────────┘
```

## Core Modules

### main.py - Orchestration Layer

**Purpose:** Coordinates all components and manages the extraction pipeline

**Responsibilities:**
1. Initialize all subsystems (video processor, lap detector, position tracker, telemetry extractor)
2. Process frames in sequence
3. Collect telemetry data
4. Generate visualizations
5. Performance tracking and reporting

**Key Design Decision - Sequential Processing:**

Why we don't use multiprocessing:
- **State dependencies**: Lap transitions require previous lap state
- **Position tracking**: Kalman filter (historical) and smoothing need sequential frames
- **Complexity vs benefit**: Multiprocessing adds significant complexity for marginal speedup
- **Bottleneck is OCR**: Parallelizing other operations wouldn't help much

Current performance (~5-10ms per frame) is acceptable for post-processing workflow (record first, process later).

### src/video_processor.py - Frame Extraction

**Purpose:** Handle video I/O and ROI (Region of Interest) extraction

**Key Methods:**
- `process_frames()` - Generator yielding frames with ROI dict
- `extract_roi()` - Cuts ROI regions from frame based on coordinates

**Implementation Detail - Generator Pattern:**

```python
def process_frames(self):
    while self.cap.isOpened():
        ret, frame = self.cap.read()
        if not ret:
            break

        self.current_frame = frame  # Expose for OCR
        roi_dict = self.extract_roi(frame)

        yield frame_num, timestamp, roi_dict
```

**Why generators instead of loading all frames:**
- Memory efficiency: Only one frame in memory at a time
- Streaming: Can start processing immediately
- Scalability: Works with hours-long videos

**Design Evolution - ROI Configuration:**

Originally, ROI coordinates were hardcoded in Python files. This required code changes for different resolutions.

**Current approach:** External YAML configuration (`config/roi_config.yaml`)
- Easy to edit without touching code
- Clear separation of concerns
- Can have multiple configs for different resolutions
- Human-readable format

### src/telemetry_extractor.py - Computer Vision Core

**Purpose:** Extract throttle/brake/steering from HUD elements using color detection

**Core Technology: HSV Color Space**

**Why HSV instead of RGB/Grayscale?**

HSV separates color (hue) from brightness (value):
- **Hue**: The actual color (0-180° in OpenCV)
- **Saturation**: How pure the color is (0-255)
- **Value**: How bright it is (0-255)

Benefits:
- Robust to lighting variations (different graphics settings, time of day)
- Easy to define color ranges ("green = hue 35-85")
- Rejects similar colors automatically

**Color Detection Pipeline:**

```python
def extract_bar_percentage(roi, lower_colors, upper_colors, orientation='horizontal'):
    # 1. Convert to HSV
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # 2. Create color masks
    masks = []
    for lower, upper in zip(lower_colors, upper_colors):
        mask = cv2.inRange(hsv, lower, upper)
        masks.append(mask)

    # 3. Combine masks (for multi-color support)
    combined_mask = masks[0]
    for mask in masks[1:]:
        combined_mask = cv2.bitwise_or(combined_mask, mask)

    # 4. Validate pixel count (artifact filtering)
    total_pixels = np.count_nonzero(combined_mask)
    if total_pixels < MIN_PIXELS_THRESHOLD:
        return 0.0

    # 5. Calculate percentage
    # ... (find rightmost filled pixel, median across rows, etc.)
```

**Historical Bug Fix - Pixel Threshold:**

See TROUBLESHOOTING.md for complete history. Key lesson:
- Presence of colored pixels ≠ valid signal
- Need sufficient quantity (150+ pixels) to confirm
- Eliminates UI text artifacts while preserving real signals

**Design Decision - Multi-Color Detection:**

TC/ABS activation changes bar colors:
- Throttle: Green → Yellow
- Brake: Red → Orange

**Evolution of approach:**

1. **Single color detection** (original)
   - Only detected green/red
   - Failed when TC/ABS active (bars changed color)

2. **Multi-color with bitwise_or** (current)
   - Detects all color variations
   - Combines masks: `cv2.bitwise_or(green_mask, yellow_mask)`
   - Bonus: TC/ABS activation detected automatically!

**Why bitwise_or works:**
- Logical OR: pixel is white if green OR yellow
- Handles color transitions smoothly
- No branching logic needed

### src/lap_detector.py - OCR and Template Matching

**Purpose:** Extract lap numbers, speed, gear, and lap times from HUD

**Architecture - Hybrid Approach:**

```
Lap Numbers → Competizione: tesserocr / pytesseract
              Assetto Corsa: assetto_corsa glyph templates (leading digits)
Speed       → Competizione: tesserocr / pytesseract
              Assetto Corsa: assetto_corsa glyph templates
Gear        → Competizione: tesserocr / pytesseract
              Assetto Corsa: assetto_corsa glyph templates (large digit; Neutral→0)
Lap Times   → pytesseract (only at transitions, ~1-2 times per minute)
```

**Why different approaches for different elements:**

| Element | Method | Reason |
|---------|--------|--------|
| Lap numbers (ACC) | tesserocr | Every frame; plain Competizione flag digits |
| Lap numbers (AC) | glyph templates | Same block font as AC speed; OCR misreads it |
| Speed (ACC) | tesserocr | Every frame; plain face |
| Speed (AC) | glyph templates | Block font; shared `0.png`–`9.png` with lap |
| Gear (ACC) | tesserocr | Every frame; plain face (1-6) |
| Gear (AC) | glyph templates | Large block digit; own `templates/gear_digits/` (`N`→0) |
| Lap times | pytesseract | Only at transitions, complex format (MM:SS.mmm) |

**Historical note:** An older ACC `TemplateMatcher` path for lap numbers remains in the tree but is not used when `reader` is omitted (Competizione default).

**Historical Evolution - OCR Performance:**

The journey from 100ms to 2ms per frame:

**Phase 1: pytesseract (~100ms per frame)**
```python
# Spawns new tesseract process each call
import pytesseract
result = pytesseract.image_to_string(roi, config='--psm 8')
# Overhead: ~50ms process spawn + ~50ms OCR = 100ms total
```

**Phase 2: Template Matching (~2ms per frame)**
- 50x speedup
- But requires calibration for each video resolution

**Phase 3: tesserocr (~1.7ms per frame) - Current Default**
```python
# Reuses tesseract engine (no process spawn)
from tesserocr import PyTessBaseAPI
with PyTessBaseAPI() as api:
    api.SetImage(pil_image)
    result = api.GetUTF8Text()
# Overhead: ~0ms process (reused) + ~1.7ms OCR = 1.7ms total
```

**Key insight:** pytesseract's slowness was process spawning, not Tesseract itself!

**Temporal Smoothing - Critical for Robustness:**

```python
# Track last N detections
self._lap_number_history = []  # Last 15 frames

def _get_smoothed_lap_number(self, raw_lap_number):
    # Add to history
    self._lap_number_history.append(raw_lap_number)
    if len(self._lap_number_history) > 15:
        self._lap_number_history.pop(0)

    # Majority voting
    counter = Counter(self._lap_number_history)
    most_common, count = counter.most_common(1)[0]

    # Require 70% consensus (11 out of 15 frames)
    if count >= len(self._lap_number_history) * 0.7:
        return most_common
    else:
        return None  # No consensus
```

**Why temporal smoothing is essential:**

OCR is noisy frame-to-frame:
- Single-frame misreads (1 → 7, 0 → 8)
- Video compression artifacts
- Motion blur

**Real-world impact:**
- Before smoothing: 89 lap transitions (many false)
- After smoothing: 27 lap transitions (all correct)

See TROUBLESHOOTING.md for detailed bug fix history.

**Design Decision - Validation Logic:**

```python
# Lap numbers can only:
# 1. Stay same (0)
# 2. Increase by 1 (normal progression)
# 3. Jump significantly (session reset)

# Lap numbers CANNOT:
# - Decrease (3 → 2)
# - Jump by small amounts (1 → 3, OCR error)

lap_diff = smoothed_lap - last_valid_lap

if lap_diff == 0:
    return last_valid_lap  # No change
elif lap_diff == 1:
    return smoothed_lap  # Normal progression ✅
elif lap_diff > 1:
    return smoothed_lap  # Allow session resets (20 → 1) ✅
else:
    return last_valid_lap  # Reject backward jumps ❌
```

**Why this works:** Use domain knowledge (racing rules) to validate data. Impossible sequences are rejected.

### src/position_tracker_v2.py - Minimap Analysis

**Purpose:** Extract car position around track (0-100%) from minimap HUD

**Two-Phase Architecture:**

**Phase 1: Track Path Extraction** (one-time, at startup)
```
Sample 50+ frames → Extract white pixels → Frequency voting → Filter artifacts → Store path
```

**Phase 2: Position Tracking** (every frame)
```
Detect red dot → Find closest path point → Calculate arc length → Convert to percentage
```

**Innovation - Multi-Frame Frequency Voting:**

The core algorithm that makes position tracking work:

```python
def extract_track_path(self, map_rois, frequency_threshold=0.45):
    # 1. Sample 50+ frames (red dot in different positions)
    # 2. Extract white pixels from each frame
    white_masks = []
    for roi in map_rois:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, white_lower, white_upper)
        white_masks.append(mask)

    # 3. Calculate pixel-wise frequency
    mask_stack = np.stack(white_masks, axis=2).astype(np.float32)
    white_frequency = np.sum(mask_stack > 0, axis=2) / len(white_masks)

    # 4. Threshold by frequency (default 45%)
    racing_line = (white_frequency >= frequency_threshold).astype(np.uint8) * 255

    # 5. Remove small artifacts (dilate-filter-erode)
    # ... morphological operations ...

    return extracted_path
```

**Why this works:**

| Element | Frequency | Result |
|---------|-----------|--------|
| Racing line (white) | ~100% (constant position) | ✅ Kept |
| Red dot | ~5-10% per position (moves) | ❌ Filtered |
| Background | ~0-30% (varies) | ❌ Filtered |
| Car cage | ~100% but tiny area | ❌ Removed by size filter |

**Temporal analysis separates static features from dynamic occlusions!**

**Historical Evolution - Frequency Threshold:**

- **Original:** 60% threshold
  - Problem: Missed darker sections of racing line
  - Dark track sections showed ~87-90% consistency (below 60%)

- **Current:** 45% threshold
  - Captures full racing line including dark segments
  - Still filters red dot (<10% per position)
  - More complete path, better position accuracy

**Design Decision - Simple Outlier Rejection vs Kalman Filtering:**

See FEATURES.md for complete journey. Summary:

**Approach 1 (implemented, then replaced): Kalman Filtering**
- Industry-standard state estimation
- Tracks [position, velocity]
- Rejects outliers based on innovation threshold
- Result: Worked perfectly ✅
- Why replaced: Unnecessary complexity for the use case

**Approach 2 (current): Simple threshold**
```python
max_jump_per_frame = 1.0  # Maximum 1% position change per frame

if abs(new_position - last_position) > max_jump_per_frame:
    return last_position  # Use last valid value
else:
    return new_position  # Accept measurement
```
- Much simpler to understand and maintain
- No external dependencies (FilterPy)
- Equally effective for post-processing video
- Result: Same practical outcome ✅

**Key lesson:** "Good enough" with lower complexity beats "perfect" with high complexity.

**Position Calculation - Path-Following Algorithm:**

```python
def calculate_position(self, dot_x, dot_y):
    # 1. Find closest point on racing line to red dot
    distances = [np.sqrt((x - dot_x)**2 + (y - dot_y)**2)
                 for x, y in self.path_points]
    closest_idx = np.argmin(distances)

    # 2. Calculate arc length from start to closest point
    arc_length = 0.0
    for i in range(closest_idx):
        x1, y1 = self.path_points[i]
        x2, y2 = self.path_points[i+1]
        segment_length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        arc_length += segment_length

    # 3. Convert to percentage
    position = (arc_length / self.total_path_length) * 100.0

    # 4. Clamp to 0-100 range
    return np.clip(position, 0.0, 100.0)
```

**Why arc length instead of straight-line distance:**
- Track is curved, not circular
- Arc length gives true position along racing line
- Handles tracks with irregular shapes (figure-8, etc.)

### src/interactive_visualizer.py - Data Presentation

**Purpose:** Generate interactive HTML visualizations using Plotly

**Why Plotly instead of matplotlib:**

| Feature | matplotlib | Plotly |
|---------|-----------|--------|
| Output | Static PNG | Interactive HTML |
| Zoom | ❌ No | ✅ Yes (click-drag) |
| Hover | ❌ No | ✅ Yes (exact values) |
| Pan | ❌ No | ✅ Yes |
| Shareable | Image file | HTML file (works offline) |
| File size | ~200KB | ~4-5MB (includes library + data) |
| Professional feel | Basic | Advanced |

**Design Decision - Self-Contained HTML:**

Plotly HTML files are completely self-contained:
- Full Plotly.js library embedded
- All telemetry data embedded as JSON
- Works offline (no CDN dependencies)
- Send to teammates who can interact without software

**Key Features - Position-Based Lap Comparison:**

**The Challenge:** Align laps by position (not time) for direct comparison

**Solution - Resampling Algorithm:**

```python
def _resample_lap_by_position(self, lap_data, target_positions):
    # Target: Fixed positions (0.0%, 0.5%, 1.0%, ..., 100.0%)
    # Input: Actual frame positions (varying, non-uniform)

    # Use linear interpolation
    throttle_resampled = np.interp(
        target_positions,
        lap_data['track_position'],
        lap_data['throttle']
    )

    # Repeat for all telemetry channels
    # Result: Both laps have data at identical positions
    return resampled_data
```

**Why 0.5% intervals (201 points)?**
- High enough resolution to capture corner details
- Low enough for good performance
- ~200 points per lap is standard in professional telemetry

**Time Delta Calculation:**

```python
def _calculate_time_delta(self, lap_a, lap_b):
    # Get relative lap times (subtract start time)
    lap_a_relative = lap_a['time'] - lap_a['time'].iloc[0]
    lap_b_relative = lap_b['time'] - lap_b['time'].iloc[0]

    # Calculate delta at each position
    time_delta = lap_a_relative - lap_b_relative

    # Interpretation:
    # Negative = Lap A faster (ahead)
    # Positive = Lap A slower (behind)
    return time_delta
```

**Dropdown Menu Implementation:**

Uses Plotly's `updatemenus` feature:
```python
# Generate all lap comparison traces upfront
# Use visibility toggles to switch between comparisons
# Instant switching without regeneration

updatemenus = [{
    'buttons': [
        {'label': 'Lap 22 vs Lap 23',
         'method': 'update',
         'args': [{'visible': visibility_pattern_22_23}]},
        {'label': 'Lap 23 vs Lap 24',
         'method': 'update',
         'args': [{'visible': visibility_pattern_23_24}]},
        # ... all pairwise combinations
    ]
}]
```

**Key design decision:** Precompute all comparisons
- Slower initial generation (~2-3s for 5 laps)
- But instant switching once loaded
- Better UX than on-demand generation

## Configuration System

### config/roi_config.yaml - ROI Coordinates

**Design Philosophy: External Configuration**

Originally hardcoded → Now external YAML
- Easy to edit without code changes
- Clear separation: code (logic) vs config (data)
- Can have multiple configs for different resolutions
- Human-readable format
- Comments explain what each ROI is for

**ROI Structure:**

Coordinates live under **named profiles** (resolution- and source-specific), not a single flat 720p block:

```yaml
my_ps5_1080p:
  throttle:
    x: 1758      # X position from left edge
    y: 1008      # Y position from top edge
    width: 143   # ROI width in pixels
    height: 15   # ROI height in pixels
  # brake, steering, lap_number, track_map, ...

twitch_720p:
  throttle:
    x: 1172
    y: 670
    width: 102
    height: 14
```

`main.py` prompts for a profile. The web API picks one from video height (`720p` / `1080p` in the profile name).

**Scaling for a new resolution:**

```python
# Start from a known profile, then:
# new_value = original_value * (new_height / profile_height)

# From a 720p profile to 1080p: multiply by 1.5
# From a 720p profile to 1440p: multiply by 2.0
```

**Why tight ROI regions are important:**
- Minimize background noise
- Faster processing (smaller image to analyze)
- More accurate (less chance of artifacts)
- Sample middle portions of bars (avoid edge artifacts)

## Data Flow

### Complete Extraction Pipeline

```
1. main.py initializes all components
   ├─> VideoProcessor opens video file
   ├─> LapDetector prepares OCR (tesserocr)
   ├─> PositionTrackerV2 extracts racing line (one-time)
   └─> TelemetryExtractor sets up color ranges

2. For each frame:
   ├─> VideoProcessor extracts ROI dict
   ├─> LapDetector extracts lap number (OCR or AC glyphs + smoothing)
   ├─> LapDetector checks for lap transition
   │   └─> If transition: extract lap time (pytesseract)
   ├─> PositionTracker extracts position (red dot + path following)
   ├─> TelemetryExtractor extracts throttle/brake/steering (HSV + pixel filtering)
   ├─> LapDetector extracts speed/gear (OCR, or AC glyphs when configured)
   └─> Data appended to list

3. After all frames processed (`main.py`):
   ├─> Convert list to pandas DataFrame
   ├─> Export to CSV
   └─> Generate interactive HTML visualization (`plot_telemetry`)

4. Output files from `main.py` in data/output/:
   ├─> telemetry_YYYYMMDD_HHMMSS.csv
   └─> telemetry_interactive_YYYYMMDD_HHMMSS.html

   Position-based HTML (`lap_comparison_position_*.html`) is **not**
   written by `main.py`. Call
   `InteractiveTelemetryVisualizer.plot_position_based_comparison()`
   on the CSV after extraction.
```

### Performance Characteristics

**Per-Frame Processing Time Breakdown** (typical):

```
Frame I/O:              ~0.5ms  (video decoding)
ROI Extraction:         ~0.1ms  (array slicing)
Telemetry Extraction:   ~2.0ms  (HSV + masking)
Lap Number Detection:   ~2.0ms  (tesserocr OCR or AC glyphs)
Speed Detection:        ~2.0ms  (tesserocr OCR or AC glyphs)
Gear Detection:         ~2.0ms  (tesserocr OCR or AC glyphs)
Position Tracking:      ~0.5ms  (red dot + path following)
Data Storage:           ~0.1ms  (list append)
─────────────────────────────────────────
Total per frame:        ~9.2ms  (≈110 FPS processing speed)
```

**For 30-minute video (54,000 frames at 30fps):**
- Processing: ~8.3 minutes (at 110 FPS)
- CSV export: ~0.1 seconds
- HTML generation: ~2-3 seconds
- **Total: ~8-9 minutes**

**Bottlenecks:**
1. Digit reads (OCR or AC glyphs for speed/gear/lap) = ~6ms (~65% of time)
2. Telemetry extraction (HSV color) = ~2ms (~22% of time)
3. Everything else = ~1.2ms (~13% of time)

**Why OCR is acceptable bottleneck:**
- tesserocr is already optimized (direct C++ API)
- Alternative (template matching) same speed but requires calibration
- Post-processing workflow (record first, process later) tolerates this

## Design Principles & Lessons Learned

### 1. Prefer Simplicity Over Sophistication

**Example: Kalman filtering vs simple threshold**
- Kalman: Industry-standard, mathematically elegant, perfect results
- Simple threshold: 5 lines of code, same practical result
- **Lesson:** Choose the simplest solution that solves the problem

### 2. Temporal Analysis for Robustness

**Pattern used throughout:**
- Lap number detection: 15-frame majority voting
- Template matching: 5-frame smoothing
- Position tracking: Multi-frame frequency voting

**Why it works:**
- Real signals persist across frames
- Noise/errors are transient (1-3 frames)
- Requiring consistency dramatically improves accuracy

### 3. Domain Knowledge for Validation

**Racing rules as validation logic:**
- Laps can only increase by 1 (or reset)
- Position can only change by ~1% per frame
- Speed changes gradually (not 100→200 instantly)

**Lesson:** Use what you know about the problem domain to reject impossible data.

### 4. External Configuration

**Evolution:**
- Hardcoded coordinates → External YAML
- Magic numbers → Named constants
- Implicit assumptions → Documented configuration

**Benefits:**
- Easy to adapt to different videos
- Clear separation of concerns
- No code changes for common adjustments

### 5. Progressive Enhancement

**Development pattern:**
1. Get basic version working (single-color detection)
2. Discover edge cases (TC/ABS color changes)
3. Enhance to handle them (multi-color support)
4. Discover new edge cases (UI text artifacts)
5. Add filtering (pixel threshold)
6. Repeat

**Lesson:** Don't try to design perfect solution upfront. Build, test, learn, improve.

### 6. Preserve the Journey

**Why this documentation exists:**
- Shows what was tried and why it was kept/replaced
- Helps future developers understand design decisions
- Prevents repeating past mistakes
- Learning artifact for computer vision / signal processing

## Testing and Validation

### Manual Testing Approach

The project uses manual testing with real gameplay footage:

1. **Extract telemetry** from known-good lap
2. **Verify values** match actual gameplay:
   - Throttle 0-100% during acceleration
   - Brake application at known corners
   - Steering matches remembered inputs
   - Lap times match in-game times
3. **Check visualizations** for sanity:
   - No sustained 0% or 100% (indicates failure)
   - Smooth curves (no glitches)
   - Lap transitions align with known lap times
4. **Compare to expected behavior**:
   - Throttle blips during downshifts
   - Trail braking (both pedals pressed)
   - TC/ABS activation in expected situations

### Test Scripts

Available tests in `tests/`:

- `tests/test_position_tracker_v2.py` - Position tracker behavior
- `tests/test_position_smoothing.py` - Position smoothing

Historical standalone scripts (`test_lap_stability.py`, `test_position_tracking.py`, `test_kalman_filtering.py`) were removed from the repo.

### Validation Checklist

Before considering extraction successful:

- [ ] All telemetry values in expected ranges
- [ ] No sustained 0% or 100% values
- [ ] Lap transitions detected correctly
- [ ] Position tracking shows smooth progression
- [ ] Visualization shows realistic driving behavior
- [ ] CSV data imports correctly into Excel/analysis tools

## Future Architecture Considerations

### Potential Enhancements

**1. Real-Time Mode:**
- Process video stream instead of file
- Lower latency for live analysis
- Challenges: Harder to optimize, less tolerance for slowness

**2. Multi-Resolution Support:**
- Auto-detect video resolution
- Auto-scale ROI coordinates
- Template matching for ROI detection
- Challenge: Requires robust template matching for HUD elements

**3. Track Detection:**
- Identify which track is being driven
- Load track-specific optimizations
- Sector analysis using known track map
- Challenge: Requires track database and detection algorithm

**4. Web UI:**
- Drag-and-drop video upload
- Browser-based processing (WebAssembly?)
- Cloud processing option
- Challenge: Large file uploads, processing infrastructure

**5. Machine Learning:**
- CNN for HUD element detection (vs template matching)
- Semantic segmentation for minimap
- Anomaly detection for data validation
- Challenge: Training data collection, model size, complexity

### Architecture Scalability

Current architecture scales well for:
- ✅ Single video processing (optimized for this)
- ✅ Multiple videos sequentially (just run multiple times)
- ⚠️ Batch processing (no parallelization built-in)
- ❌ Real-time processing (post-processing focused)

**To scale to batch processing:**
- Add multiprocessing support for independent videos
- Challenge: State management, resource allocation

**To scale to real-time:**
- Optimize critical path (OCR is bottleneck)
- Consider GPU acceleration (for future ML approaches)
- Reduce per-frame work (frame skipping, adaptive sampling)

## Conclusion

The ACC Telemetry Extractor architecture reflects an iterative development process:
- Started simple (basic color detection)
- Added sophistication when needed (multi-color, temporal filtering)
- Simplified when possible (Kalman → simple threshold)
- Focused on user experience (interactive visualizations, position-based comparison)

The code is production-ready for post-processing ACC gameplay videos from consoles, providing analysis capabilities comparable to professional tools at zero cost.

The journey from "let's extract some data" to "professional-grade telemetry analysis" is documented in git history and preserved in this documentation for learning and reference.
