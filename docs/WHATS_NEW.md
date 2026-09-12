# 🎉 What's New: Interactive Telemetry Visualization

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Major Update: Plotly Integration

Your ACC Telemetry Extractor now has **professional-grade interactive visualization** built-in!

---

## What Changed?

### ✅ New Features

1. **Interactive HTML Graphs** (replaces static PNG)
   - Zoom by clicking and dragging
   - Pan when zoomed in
   - Hover to see exact values
   - Synchronized views across all three plots
   - Range slider for quick navigation
   - Built-in export to high-res PNG

2. **Lap Comparison Tool** (historically `compare_laps.py`; now `InteractiveTelemetryVisualizer.plot_lap_comparison()`)
   - Overlay multiple laps on same graph
   - Color-coded traces
   - Interactive analysis of differences
   - Find where you gained/lost time

3. **Browser-Based** (no additional software needed)
   - Works in Chrome, Firefox, Safari, Edge
   - Shareable HTML files (just send to friends)
   - Offline-capable (full data embedded)

### 📦 New Files

- `src/interactive_visualizer.py` - Plotly visualization engine
- ~~`compare_laps.py`~~ — removed; use `InteractiveTelemetryVisualizer.plot_lap_comparison()`
- `INTERACTIVE_VISUALIZATION_GUIDE.md` - Full usage guide
- Output: `telemetry_interactive_*.html` files

### 🔧 Technical Changes

- Added Plotly dependency (`pip install plotly`)
- `main.py` now uses `InteractiveTelemetryVisualizer` by default
- CSV export unchanged (still works)
- Old static graphs via `generate_detailed_analysis.py` — **removed**; use interactive HTML from `main.py`

---

## How to Use

### Quick Start

```bash
# Same as before - but now generates interactive HTML!
python main.py
```

**Output**: 
- `telemetry_interactive_YYYYMMDD_HHMMSS.html` ← Open this in browser!
- `telemetry_YYYYMMDD_HHMMSS.csv` (unchanged)

### New: Compare Laps

```bash
# Compare 2+ laps
# (removed) use InteractiveTelemetryVisualizer.plot_lap_comparison(df, lap_numbers=[...])
```

**Output**:
- `telemetry_comparison_YYYYMMDD_HHMMSS.html` ← Interactive overlay

---

## What You Get vs MoTeC i2 Pro

| Feature | MoTeC i2 Pro | Your Tool (Now!) |
|---------|--------------|------------------|
| Cost | ~4,000 zł | 0 zł |
| Interactive Zoom | ✅ | ✅ |
| Lap Comparison | ✅ | ✅ |
| Hover Tooltips | ✅ | ✅ |
| Browser-based | ❌ | ✅ |
| Console Compatible | ❌ | ✅ |
| Shareable | ❌ (needs license) | ✅ (send HTML) |

**You now have 80% of MoTeC's features for 0% of the cost!**

---

## Migration Guide

### If You Were Using Old Version

**Nothing breaks!** Your workflow stays the same:

```bash
# Old way (still works)
python main.py  # Now generates HTML instead of PNG

# CSV export unchanged
# Same telemetry_*.csv files as before
```

**Want old static graphs?**
```bash
# generate_detailed_analysis.py removed — use interactive HTML from main.py
```

### Update Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt  # Adds Plotly
```

---

## Examples

### Example 1: Analyze Single Lap

```bash
# Extract telemetry
python main.py

# Open the HTML file (or it auto-opens)
# You can now:
# - Zoom into braking zones
# - Check throttle smoothness
# - Measure exact steering angles
```

### Example 2: Compare Two Laps

```bash
# You have two lap videos
python main.py  # Process lap 1
# Replace video, then:
python main.py  # Process lap 2

# Now compare them:
# (removed) plot_lap_comparison() / plot_position_based_comparison()
# formerly: python compare_laps.py \
  data/output/telemetry_20251022_005324.csv \
  data/output/telemetry_20251022_010355.csv

# Opens comparison graph showing both laps overlaid
```

### Example 3: Learn from YouTube

```bash
# 1. Download fast driver's lap from YouTube
# 2. Extract their telemetry
python main.py

# 3. Extract your lap telemetry
# (replace video)
python main.py

# 4. Compare
# (removed) use InteractiveTelemetryVisualizer APIs instead of compare_laps.py

# See exactly where they brake earlier/later!
```

---

## New Capabilities

### 1. Deep Dive Analysis

**Before**: Static PNG, had to squint to see details
**Now**: Click-drag-zoom into any 0.5 second section!

### 2. Exact Measurements

**Before**: Estimate from graph lines
**Now**: Hover to see exact % at any frame

### 3. Lap Comparison

**Before**: Open two PNGs side-by-side, compare visually
**Now**: Overlay on same graph with synchronized zoom

### 4. Sharing

**Before**: Send screenshot of PNG
**Now**: Send HTML file - recipient can zoom/interact themselves!

---

## Performance Notes

- **HTML file size**: ~4-5MB (vs 200KB PNG)
- **Processing time**: Same as before
- **Browser performance**: Smooth on modern browsers
- **Offline**: Works without internet (data embedded)

---

## Next Steps

### Immediate
1. Read [INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md)
2. Run `python main.py` to see new visualizations
3. Try `plot_lap_comparison()` / `plot_position_based_comparison()` with existing CSV files

### Future Enhancements
- Time delta graphs (Lap 1 vs Lap 2 time difference)
- Track map overlay (plot telemetry on circuit layout)
- Real-time streaming (live telemetry during recording)
- Web UI (upload videos in browser)

---

## Feedback Welcome!

This is a major upgrade inspired by your request for "MoTeC-like" features. You now have:

✅ Interactive zoom/pan/hover  
✅ Lap comparison  
✅ Professional visualization  
✅ Free and open-source  
✅ Works with console gameplay  

**Cost**: 0 zł (vs MoTeC's ~4,000 zł license)

---

**Questions?** Check the guides:
- [INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md) - Full usage
- [README.md](README.md) - Updated with new features

**Happy racing! 🏁**

