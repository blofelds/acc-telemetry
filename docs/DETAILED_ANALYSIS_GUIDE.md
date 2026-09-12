# Detailed Telemetry Analysis Guide

> **Historical / deprecated:** The standalone scripts `generate_detailed_analysis.py` and `src/detailed_visualizer.py` are **no longer in this repository**. Prefer interactive HTML from `python main.py` and methods on `InteractiveTelemetryVisualizer` (see [INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md) and [USER_GUIDE.md](USER_GUIDE.md)). This document is preserved for historical context about the old static PNG analysis workflow.

This guide explains how the (removed) detailed visualization tools analyzed ACC driving performance.

## Quick Start (current workflow)

```bash
# Extract telemetry → interactive HTML + CSV
python main.py
```

For position-based comparison:

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

## Former workflow (removed)

```bash
# These commands no longer work — scripts were removed
# python generate_detailed_analysis.py
```

## Generated Visualizations (historical)

The detailed analysis previously generated **4 high-resolution PNG files** (300 DPI):

### 1. **Comprehensive Overview** (`telemetry_detailed_*.png`)
**What it shows**: 6-panel layout with multiple detail levels

**Panels**:
- **Complete Lap Overview**: Full lap with all three inputs overlaid
- **Throttle Input Detail**: Zoomed throttle with 25%, 50%, 75%, 100% reference lines + statistics
- **Brake Input Detail**: Zoomed brake with statistics and braking event count
- **Steering Input Detail**: Color-coded steering (blue=right, orange=left) with statistics
- **Pedal Overlay**: Throttle and brake together with **yellow highlighting** where both pedals are pressed (trail braking or mistakes)
- **Telemetry Statistics**: Complete lap stats in an easy-to-read table

**Use this for**: Overall lap analysis, identifying problem areas, comparing your inputs to ideal lines

---

### 2. **Zoomed Sections** (`telemetry_sections_*.png`)
**What it shows**: Your lap divided into 6 equal time sections, each shown in detail

**Each section displays**:
- Time range covered (e.g., "Section 1: 0.00s - 8.16s")
- All three inputs (throttle, brake, steering) with high resolution
- Enough detail to see individual frames and input changes

**Use this for**:
- Finding specific corners or track sections
- Analyzing complex sequences (e.g., chicanes, esses)
- Studying transitions between inputs
- Frame-by-frame analysis of technique

**Pro tip**: If you know which section a problem occurs in (e.g., "around 25 seconds"), this makes it easy to zoom in on that area.

---

### 3. **Braking Zones Analysis** (`telemetry_braking_zones_*.png`)
**What it shows**: Every braking event isolated with context before/after

**For each braking zone**:
- **Yellow highlight**: The actual braking period
- **Context area**: 30 frames before and after to see approach and exit
- **Statistics box**:
  - Duration: How long you braked
  - Max brake: Peak brake pressure
  - Avg brake: Average pressure during braking
  - From throttle: Throttle % just before braking
- **Steering overlay**: See if you're trail braking into the corner

**Use this for**:
- Comparing brake points across laps
- Analyzing brake pressure consistency
- Identifying late/early braking
- Studying trail braking technique
- Finding where you're coasting (low throttle but not braking)

**What to look for**:
- ✅ **Good**: Smooth brake application, consistent max pressure, steering increases as brake decreases (trail braking)
- ❌ **Bad**: Sudden brake spikes, multiple brake applications, braking while full throttle

---

### 4. **Throttle Application Analysis** (`telemetry_throttle_analysis_*.png`)
**What it shows**: 3-panel deep dive into how you apply throttle

**Panels**:
1. **Throttle with Color Gradient**: 
   - **Green dots**: Increasing throttle (accelerating)
   - **Red dots**: Decreasing throttle (lifting)
   - Shows how aggressively you get on/off the gas
   
2. **Throttle vs Steering Correlation**:
   - Compares throttle with absolute steering angle
   - Reveals if you're using proper "slow in, fast out" technique
   - High steering with high throttle = potential oversteer risk
   
3. **Throttle Application Rate**:
   - **Green line**: Acceleration (adding throttle)
   - **Red line**: Deceleration (lifting throttle)
   - Shows smoothness of throttle control

**Use this for**:
- Checking throttle smoothness (jerky inputs = lost time)
- Analyzing corner exit technique
- Identifying where you're lifting mid-corner (bad) vs. building throttle progressively (good)
- Comparing throttle confidence between corners

**What to look for**:
- ✅ **Good**: Smooth gradual throttle increases, early throttle application on corner exit
- ❌ **Bad**: Sharp throttle drops mid-corner, on-off throttle oscillations, late throttle application

---

## How to Analyze Your Driving

### Workflow 1: Find Problem Areas
1. Open **Comprehensive Overview**
2. Look at the **Pedal Overlay** panel - yellow areas mean both pedals pressed
3. Look for sections where throttle/brake look "messy" (lots of small changes)
4. Note the time where problems occur
5. Open **Zoomed Sections** to see that time period in detail

### Workflow 2: Compare Laps
1. Run `main.py` on multiple lap videos (rename the input video each time)
2. (Historical) Previously ran `generate_detailed_analysis.py` — use interactive HTML instead
3. Open the same type of graph (e.g., braking zones) from each lap side-by-side
4. Compare:
   - Brake point timing
   - Brake pressure consistency
   - Throttle application timing
   - Steering smoothness

### Workflow 3: Master a Specific Corner
1. Identify the corner's time range in **Zoomed Sections**
2. Find the corresponding braking zone in **Braking Zones Analysis**
3. Check the **Throttle Application Analysis** for exit technique
4. Look at the **Statistics** to see if you're losing time on throttle or braking

### Workflow 4: Improve Consistency
1. Record 5 laps of the same track/car
2. Extract and analyze all 5
3. Compare the **Statistics** panel - look for variations in:
   - Full throttle time (should be consistent)
   - Number of braking events (should match corner count)
   - Max steering angles (should be similar)
4. Use **Braking Zones** to find which corners have the most variation

---

## Understanding the Statistics Panel

Located at the bottom of the **Comprehensive Overview**:

```
Duration: 48.97s  |  Frames: 1467  |  FPS: 30.0
```
- Total lap time (or video segment length)
- Number of frames processed
- Video frame rate

```
THROTTLE:  Avg: 74.6%  |  Max: 100.0%  |  Full throttle: 29.04s (59.3%)
```
- **Avg**: Average throttle across entire lap (higher = more time accelerating)
- **Max**: Should almost always be 100%
- **Full throttle time**: How long you were at 100% throttle (track-dependent, but more is usually better)

```
BRAKE:  Avg: 14.1%  |  Max: 100.0%  |  Braking time: 9.51s (19.4%)  |  Events: 7
```
- **Avg**: Average brake pressure (accounts for time not braking = lower number)
- **Max**: Should be 100% in most corners
- **Braking time**: Total time spent braking (>10% threshold)
- **Events**: Number of distinct braking zones (should roughly match corner count)

```
STEERING:  Avg abs: 0.90  |  Max left: -1.00  |  Max right: 0.93
```
- **Avg abs**: Average steering angle (ignoring direction) - track-dependent
- **Max left/right**: Peak steering angles (-1.0 to +1.0 range)

---

## Pro Tips

### Reading the Graphs
- **Zoom in**: These are 300 DPI images - zoom to 200-300% in your image viewer to see fine details
- **Print them**: High resolution makes them suitable for printing and annotating with a pen
- **Side-by-side**: Open multiple graphs on different monitors for comparison

### What "Good" Looks Like
1. **Throttle**: Long green sections, smooth transitions, early application on exit
2. **Brake**: Sharp initial application, smooth trail-off, no pumping
3. **Steering**: Smooth curves, no sudden changes, minimal corrections
4. **Pedal Overlay**: Minimal yellow (except intentional trail braking), clear separation between throttle and brake phases

### Common Issues to Spot
- **Yellow in pedal overlay** (unexpected): You're stepping on both pedals - usually a mistake
- **Multiple brake spikes in one zone**: You're pumping the brakes - commit to one brake application
- **Throttle drops mid-corner**: You're lifting due to oversteer or lack of confidence - work on car setup or entry speed
- **Jagged steering**: Making lots of corrections - sign of unstable car or wrong line
- **Low full throttle %**: Not using enough of the track's potential - later braking or earlier acceleration needed

### Comparing to Fast Laps
If you have telemetry from a faster driver:
1. **Braking points**: Are they braking later than you?
2. **Brake pressure**: Are they using more initial brake pressure?
3. **Throttle timing**: Are they getting on throttle earlier?
4. **Minimum speed**: Check where their throttle starts climbing vs. yours

---

## Customization

### Change Number of Sections
Edit settings (historical — script removed):

```python
# Default: 6 sections
sections_path = visualizer.plot_zoomed_sections(df, num_sections=6)

# Change to 10 sections for more detail:
sections_path = visualizer.plot_zoomed_sections(df, num_sections=10)
```

### Change Braking Threshold
By default, braking zones are detected at >10% brake pressure:

```python
# More sensitive (catches lighter braking):
braking_path = visualizer.plot_braking_zones(df, brake_threshold=5.0)

# Less sensitive (only hard braking):
braking_path = visualizer.plot_braking_zones(df, brake_threshold=20.0)
```

### Analyze Specific Time Range
You can modify the scripts to analyze only specific sections. For example, in a Python script:

```python
import pandas as pd
from src.detailed_visualizer import DetailedTelemetryVisualizer

# Load data
df = pd.read_csv('data/output/telemetry_XXXXX.csv')

# Filter to specific time range (e.g., 10-20 seconds)
df_section = df[(df['time'] >= 10) & (df['time'] <= 20)]

# Analyze just that section
visualizer = DetailedTelemetryVisualizer()
visualizer.plot_detailed_overview(df_section, filename='section_10_20_analysis.png')
```

---

## Technical Details

### Resolution
- **Standard graphs** (from `main.py`): 150 DPI
- **Detailed graphs** (historical `generate_detailed_analysis.py`): 300 DPI

### File Sizes
Detailed visualizations are larger due to high resolution:
- Comprehensive Overview: ~1.0 MB
- Zoomed Sections: ~1.3 MB (varies with number of sections)
- Braking Zones: ~2.0 MB (varies with number of zones)
- Throttle Analysis: ~0.9 MB

### Performance
- Processing time: 30-60 seconds for all 4 visualizations
- Depends on lap length (more frames = longer processing)
- High resolution rendering takes most of the time

---

## Troubleshooting

**Q: The graphs look blurry**
- A: You're viewing them at too low a zoom level. These are 300 DPI - zoom in to 100% or more in your image viewer.

**Q: No braking zones found**
- A: Either your telemetry has no braking data, or the threshold is too high. Try lowering the `brake_threshold` parameter.

**Q: Statistics show 0 frames**
- A: Your CSV file is empty or corrupted. Re-run `main.py` to regenerate telemetry data.

**Q: I want even more detail**
- A: Increase the DPI in the (removed) `detailed_visualizer.py` (change `dpi=300` to `dpi=600`), but file sizes will increase significantly.

**Q: Can I export to other formats?**
- A: Yes! Modify the file extension in the scripts:
  - `.png` - Best for viewing (default)
  - `.pdf` - Best for printing/documents
  - `.svg` - Best for editing in Illustrator/Inkscape

---

## Next Steps

1. **Learn your baseline**: Analyze your current fastest lap to understand your driving style
2. **Identify weak corners**: Find where you're losing the most time
3. **Practice specific techniques**: Focus on one corner type at a time (e.g., "trail braking into hairpins")
4. **Measure improvement**: Re-analyze after practice to see if your technique changed
5. **Compare to aliens**: If you can find YouTube videos of very fast laps, extract and compare their telemetry

**Remember**: Data is only useful if you act on it. Pick ONE thing to improve each session!

---

## Examples of What to Look For

### Example 1: Late Throttle Application
**Symptom**: Low "Full throttle %" in statistics (e.g., 45% when it should be 65%)
**Diagnosis**: Open Throttle Application Analysis → Check when throttle starts climbing after braking zones
**Fix**: Work on getting on throttle earlier on corner exit, even if it's just partial throttle

### Example 2: Inconsistent Braking
**Symptom**: Similar lap times but very different "feel" each lap
**Diagnosis**: Compare Braking Zones Analysis from multiple laps → Check if brake points vary by >0.5s
**Fix**: Use visual references on track (brake boards, trackside objects) for consistent brake points

### Example 3: Understeer Mid-Corner
**Symptom**: Throttle drops mid-corner, steering increases mid-corner
**Diagnosis**: Zoomed Sections → Find the corner → See throttle dip with steering spike
**Fix**: Either enter slower (earlier/harder braking) or adjust car setup for more front grip

---

*Happy racing! 🏁*

**Remember**: The fastest drivers aren't necessarily the most talented - they're the ones who analyze and improve systematically. This tool gives you console racers the same advantage PC racers have had for years.

