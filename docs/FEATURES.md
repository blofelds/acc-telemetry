# ACC Telemetry Extractor - Features & Development Journey

This document describes the key features of the ACC Telemetry Extractor, explaining both what works today and the development journey that led to current implementations.

## Core Telemetry Extraction

### Throttle, Brake, and Steering Detection

**Current Implementation:** HSV color detection with multi-color support and pixel threshold filtering

The system extracts input data by analyzing colored bars in the ACC HUD:
- **Throttle**: Green/yellow horizontal bar (bottom-right HUD)
- **Brake**: Red/orange horizontal bar (below throttle)
- **Steering**: White dot indicator position

**Why HSV instead of RGB?**
- HSV separates color (hue) from brightness (value)
- More robust to lighting variations in gameplay footage
- Makes color detection consistent across different game graphics settings

**Development Journey - Multi-Color Detection:**

Early versions only detected single colors (green for throttle, red for brake). This failed when driver aids activated:
- **TC activation**: Throttle bar changes from green to yellow
- **ABS activation**: Brake bar changes from red to orange

**Solution:** Implemented multi-color masks with `cv2.bitwise_or`:
```python
mask_green = cv2.inRange(hsv, lower_green, upper_green)
mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
combined_mask = cv2.bitwise_or(mask_green, mask_yellow)
```

This detects the bar regardless of TC/ABS state.

**Development Journey - Pixel Threshold Filtering:**

**Problem discovered:** False throttle readings during braking
- Showed 65% throttle while brake was at 100%
- Only 10-19 pixels detected vs 300-1200 for real throttle

**Root cause:** UI text overlay (e.g., "TC: 37 10") created small green artifacts in the throttle ROI

**Solution implemented:** Minimum pixel threshold
- Started with 50 pixels (too low, still had false positives)
- Increased to 150 pixels (eliminated artifacts, preserved real signals)
- Real throttle bars have 300-700+ pixels
- UI artifacts have <100 pixels

This filter eliminated false readings while maintaining accuracy for actual throttle blips (e.g., rev-matching during downshifts).

**Key lesson learned:** Computer vision needs robust filtering - presence of colored pixels isn't enough, you need sufficient quantity to confirm signal validity.

## Lap Number Detection

**Current Implementation:** tesserocr (~2ms per frame) with temporal smoothing; pytesseract if tesserocr is unavailable

**Development Journey - OCR to Template Matching:**

The lap detection feature went through several iterations:

### Phase 1: pytesseract OCR (~100ms per frame)
- **Pros**: No calibration needed, works immediately
- **Cons**: 50-100ms per frame, too slow for real-time
- **Result**: Acceptable for post-processing but bottleneck

### Phase 2: Template Matching (~2ms per frame) - First Implementation
- **Achievement**: 50x speedup over OCR
- **How**: Pre-extracted digit templates (0-9), slide across ROI to find matches
- **Pros**: 67x faster than OCR, equal or better accuracy
- **Cons**: Requires one-time calibration (extract templates from video)

**Why template matching works so well:**
- Lap numbers use fixed font/size
- Sliding window algorithm handles ROI noise automatically
- OpenCV's `cv2.matchTemplate` is highly optimized C++ code

### Phase 3: tesserocr (~1.7ms per frame) - Current Default
- **Discovery**: pytesseract's slowness was process spawning overhead, not OCR itself!
- **Solution**: tesserocr uses direct C++ API, keeps Tesseract engine warm
- **Result**: 29x faster than pytesseract, faster than template matching
- **Pros**: No calibration needed, universally applicable
- **Cons**: Requires tesserocr installation (falls back to pytesseract if unavailable)

**Current approach:** tesserocr on every frame (pytesseract fallback). `TemplateMatcher` is still in the tree from Phase 2 but is not called by `extract_lap_number()`.

**Development Journey - Temporal Smoothing:**

**Problem:** Lap numbers oscillating between values (e.g., 10↔11, 20↔21)
- 89 false transitions detected instead of 27 actual laps
- Caused visualization artifacts (multiple lap markers in rapid succession)

**Root cause:** Template matching found partial matches frame-to-frame
- Frame N: Detects both "1" and "0" → Lap 10
- Frame N+1: Detects only "1" (high confidence) → Lap 1
- Frame N+2: Detects "1" and "0" again → Lap 10

**Solutions implemented:**

1. **Increased matching threshold** from 0.6 to 0.65 (stricter matching)
2. **Added temporal smoothing** - majority voting over last 5 frames
   - Requires 60% agreement (3/5 frames) to accept lap number
   - Filters single-frame misdetections
3. **Stricter validation** - rejects backward jumps completely
   - Only allows lap progression: N → N+1
   - Rejects jumps > 1 (OCR errors)
   - Rejects backward movement

**Result:** 31 oscillations eliminated, clean lap transitions

**Key lesson learned:** Computer vision detections are noisy frame-to-frame. Temporal filtering (requiring consistency across multiple frames) dramatically improves robustness.

## Track Position Tracking

**Current Implementation:** Multi-frame frequency voting + simple outlier rejection

Position tracking extracts the car's location around the track (0-100%) from the minimap HUD.

**Development Journey - Racing Line Extraction:**

### Challenge: Red dot occlusion problem
- Minimap shows white racing line + red position dot
- Red dot moves across the track, covering parts of white line
- Single-frame extraction gives incomplete line

### Solution 1: Simple OR (bitwise_or all frames)
- **Approach**: Combine white pixels from all frames
- **Problem**: Includes all red dot positions, bright backgrounds
- **Result**: Too noisy ❌

### Solution 2: Multi-Frame Frequency Voting - CURRENT
- **Insight**: Racing line is white in ~100% of frames, red dot only ~5-10% per position
- **Algorithm**:
  1. Sample 50+ frames evenly across lap
  2. For each pixel, count how often it appears white
  3. Keep pixels white in ≥45% of frames
  4. Dilate-filter-erode to remove small artifacts
- **Result**: Clean, complete racing line ✅

**Threshold evolution:**
- Started with 60% (too strict, missed darker track sections)
- Lowered to 45% (captures full line including dark sections)
- Still effectively filters red dot (<10% per position) and backgrounds

**Why this works:** Temporal analysis naturally separates static features (racing line) from dynamic occlusions (moving red dot).

**Development Journey - Position Filtering:**

### Phase 1: Kalman Filtering (Implemented but Later Replaced)

**Problem:** Single-frame position glitches causing false time delta spikes
- Position jumps from 49% to 71% for one frame
- Created -32 second time delta spike in comparison graphs

**Solution attempted:** Industry-standard Kalman filtering
- **Implementation**: Used FilterPy library
- **Model**: 1D Kalman filter tracking [position, velocity]
- **Outlier rejection**: Reject measurements with >10% innovation
- **Result**: Successfully eliminated glitches ✅

**Why it was replaced:**
- Kalman filtering worked perfectly but added complexity
- Required FilterPy dependency
- Required understanding of state estimation, covariance matrices, etc.
- Marginal benefit over simpler approaches

### Phase 2: Simple Forward-Progress Validation - CURRENT

**Simpler solution:** `max_jump_per_frame` threshold
- **Default**: 1.0% maximum position change per frame
- **Logic**: Reject position jumps exceeding threshold, use last valid value
- **Result**: Equally effective at rejecting glitches ✅

**Why we switched:**
- Much simpler to understand and maintain
- No external dependencies needed
- Equally effective for post-processing video telemetry
- "Simplicity is the ultimate sophistication"

**Key lesson learned:** Sometimes the sophisticated solution (Kalman filtering) works great, but a simpler solution achieving the same practical goal is preferable. The development process helped us understand the problem deeply enough to find the simpler approach.

**Historical note:** The Kalman filtering implementation is preserved in git history and documentation as a learning artifact. It was production-ready and worked well - we just found something better (simpler).

## Interactive Visualization

**Current Implementation:** Plotly-based interactive HTML with synchronized plots

**Development Journey - From Static to Interactive:**

### Phase 1: Static PNG graphs (matplotlib)
- **Tool**: matplotlib with 3-panel layout
- **Pros**: Simple, works everywhere
- **Cons**: Can't zoom, can't see exact values, hard to analyze details

### Phase 2: Detailed Static Analysis (300 DPI)
- **Added**: 4 high-res PNG visualizations
  - Comprehensive overview (6 panels)
  - Zoomed sections (lap divided into 6 segments)
  - Braking zones analysis
  - Throttle application analysis
- **Pros**: Much more detail, printable
- **Cons**: Still static, multiple files to manage

### Phase 3: Interactive Plotly Visualizations - CURRENT
- **Breakthrough**: Replace static PNGs with interactive HTML
- **Features**:
  - Zoom by click-drag
  - Pan while zoomed
  - Hover tooltips with exact values
  - Synchronized views (all plots zoom together)
  - Range slider navigation
  - Export to PNG from browser
- **Result**: Professional-grade analysis comparable to MoTeC i2

**Why Plotly?**
- Pure JavaScript, works in any browser
- Offline-capable (data embedded in HTML)
- Shareable (send HTML file to teammates)
- No server required
- Beautiful, professional appearance

**Comparison to MoTeC i2 Pro:**
- MoTeC cost: ~4,000 zł, requires hardware logger, PC only
- Our tool: Free, works with console footage, browser-based, shareable

**Key lesson learned:** Interactive visualization transforms the user experience. The ability to zoom into specific sections and see exact values makes analysis 10x more effective than static graphs.

## Position-Based Lap Comparison

**Current Implementation:** The gold standard for racing telemetry analysis

**Development Journey - Time-Based vs Position-Based:**

### Phase 1: Time-Based Lap Comparison
- **Approach**: Overlay laps by time (0s, 1s, 2s, etc.)
- **API**: `InteractiveTelemetryVisualizer.plot_lap_comparison()`
- **Problem**: Out of sync after first difference
  - If you brake earlier in Lap 1, rest of lap is offset
  - Can't compare corner entry technique directly
  - Can't see WHERE on track time is gained/lost

### Phase 2: Position-Based Comparison - CURRENT
- **Breakthrough**: Align laps by track position instead of time
- **API**: `InteractiveTelemetryVisualizer.plot_position_based_comparison()`
- **Approach**:
  1. Resample both laps at fixed position intervals (every 0.5%)
  2. Compare telemetry at same track positions
  3. Calculate time delta at each position
- **Result**: Direct comparison of inputs at same corners ✅

**Why position-based is superior:**
- Shows exactly WHERE on track you gain/lose time
- Time delta plot: negative = gaining time, positive = losing time
- Can zoom to specific corners and compare braking points
- Professional racing teams use this approach

**Implementation details:**
- Uses linear interpolation to resample at 0.5% intervals
- Creates 201 data points per lap (0.0%, 0.5%, 1.0%, ..., 100.0%)
- Dropdown menu to select which laps to compare
- All pairwise combinations generated automatically

**Example analysis workflow:**
1. Load comparison → shows all available lap pairs
2. Select "Lap 22 vs Lap 23" from dropdown
3. Time delta shows losing 1.5s from 45-55% position
4. Zoom to that section
5. See: braked earlier, lower minimum speed, later on throttle
6. Action: Next session, focus on that corner

**Key lesson learned:** Position-based comparison is transformative for racing analysis. It's the difference between "I was slower" (time-based) and "I was slower because I braked too early at Turn 7" (position-based).

## Speed and Gear Detection

**Current Implementation:** tesserocr OCR (~2ms per frame) with pytesseract fallback

Uses OCR to read numeric values from HUD:
- **Speed**: 3-digit number inside rev meter
- **Gear**: Single digit (1-6) in center of rev meter

**Why OCR instead of template matching here:**
- Speed changes constantly (0-300+ km/h)
- Would need 300+ templates vs 10 for lap numbers
- tesserocr is fast enough (~2ms) for per-frame extraction
- OCR flexibility outweighs template matching's marginal speed advantage

**Preprocessing:** Minimal - tesserocr handles raw BGR ROI effectively
- No HSV conversion needed
- No thresholding needed
- Tesseract handles white-on-dark text natively

**Performance:** Total OCR overhead (speed + gear) is ~4ms per frame, acceptable for post-processing workflow.

## TC/ABS Detection

**Current Implementation:** Derivative feature from multi-color detection

TC/ABS activation is detected by observing color changes:
- **TC active**: Throttle bar is yellow (vs green normally)
- **ABS active**: Brake bar is orange (vs red normally)

This is a byproduct of the multi-color detection system - no additional processing required!

**Key insight:** Sometimes features come "for free" when you solve a different problem. We added multi-color detection to accurately measure throttle/brake during aid activation, and got TC/ABS detection as a bonus.

## Summary of Development Philosophy

Throughout this project, we've followed several key principles:

1. **Try sophisticated solutions first to understand the problem deeply** (Kalman filtering, complex preprocessing)
2. **Then simplify to the minimum that works** (simple thresholds, direct OCR)
3. **Preserve the journey** (document what was tried and why it was kept/replaced)
4. **Performance matters, but not at the cost of complexity** (tesserocr is good enough; template matching was an optional experiment and is unused today)
5. **User experience is paramount** (interactive visualizations, position-based comparison)

The features described here represent the current state after multiple iterations. The git history and documentation preserve the experiments, failures, and learnings that led here.
