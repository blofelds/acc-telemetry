# Interactive Telemetry Visualization Guide

## Overview

Your ACC Telemetry Extractor now generates **interactive HTML visualizations** using Plotly instead of static PNG images. This gives you professional-grade telemetry analysis capabilities similar to MoTeC i2, but completely free and browser-based.

## What You Get

### 🎯 Interactive Features

1. **Zoom**: Click and drag to zoom into any region (braking zones, corner entries, etc.)
2. **Pan**: Drag the graph while zoomed to navigate
3. **Hover tooltips**: Hover over any point to see exact values
4. **Synchronized views**: All three plots (throttle, brake, steering) zoom together
5. **Range slider**: Quick navigation timeline at the bottom
6. **Export**: Download as PNG directly from the graph

### 📊 Output Files

When you run `python main.py`, you get:

- **CSV file**: `telemetry_YYYYMMDD_HHMMSS.csv` - Raw data for analysis
- **Interactive HTML**: `telemetry_interactive_YYYYMMDD_HHMMSS.html` - Open in any browser

## How to Use

### Basic Telemetry Extraction

```bash
# Activate virtual environment
source venv/bin/activate

# Run extraction (same as before)
python main.py
```

**Output**: 
- `data/output/telemetry_interactive_YYYYMMDD_HHMMSS.html`

**Open the HTML file** in any browser (Chrome, Firefox, Safari) - no software installation needed!

---

### Lap Comparison

Compare multiple laps from a session CSV using the visualizer API:

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')

# Time-based overlay of selected laps
viz.plot_lap_comparison(df, lap_numbers=[22, 23, 24])

# Position-aligned comparison (recommended)
viz.plot_position_based_comparison(df)
```

**What you see**:
- Laps overlaid on the same graph
- Color-coded traces
- Interactive zoom to compare braking points
- Hover to see exact differences

> **Note:** The former standalone script `compare_laps.py` has been removed. Use the methods above (or the web API).

---

## Interactive Controls

### Mouse Controls

| Action | Control |
|--------|---------|
| **Zoom in** | Click and drag to select region |
| **Zoom out** | Double-click anywhere |
| **Pan** | Click and drag (when zoomed) |
| **Reset view** | Click "Reset axes" button (top-right) |
| **Hover data** | Move mouse over graph |

### Toolbar (Top-Right Corner)

- 🏠 **Home**: Reset to default view
- 📷 **Camera**: Download as PNG (1920x1080, high-res)
- 🔍 **Zoom**: Toggle zoom mode
- ➕ **Pan**: Toggle pan mode
- 📏 **Box select**: Select data region
- ✏️ **Drawing tools**: Annotate graph

---

## Real-World Usage Examples

### Example 1: Find Optimal Braking Point

**Goal**: Compare two laps to see if you braked earlier or later

1. Call `plot_lap_comparison()` or `plot_position_based_comparison()` on your session CSV
2. Open the HTML file
3. **Zoom into** the braking zone (look for red brake spike)
4. **Hover** over both traces to see exact time difference
5. **Check** if Lap 2 braked earlier/later and how it affected corner exit (throttle)

### Example 2: Analyze Throttle Application

**Goal**: See if you're smooth on throttle or too aggressive

1. Open single lap HTML file
2. **Zoom into** throttle plot (green)
3. Look for:
   - ✅ **Smooth ramps**: Good throttle control
   - ❌ **Spikes/drops**: Traction control kicking in or wheel spin
4. Cross-reference with steering (bottom plot) to see if over-steering

### Example 3: Check Steering Smoothness

**Goal**: Identify jerky inputs that upset the car

1. Zoom into steering plot (blue, bottom)
2. Look for:
   - ✅ **Smooth curves**: Good steering technique
   - ❌ **Zig-zag pattern**: Jerky corrections (bad)
3. Compare with brake plot - jerky steering + braking = understeer/lockup

---

## Advantages Over MoTeC

| Feature | MoTeC i2 Pro | Your Tool |
|---------|--------------|-----------|
| **Cost** | ~4,000 zł license | Free (0 zł) |
| **Hardware requirement** | MoTeC ECU/logger | Just a video |
| **Console compatible** | ❌ No | ✅ Yes (PS5/Xbox) |
| **Interactive zoom** | ✅ Yes | ✅ Yes |
| **Lap comparison** | ✅ Yes | ✅ Yes |
| **Hover tooltips** | ✅ Yes | ✅ Yes |
| **Browser-based** | ❌ No (desktop app) | ✅ Yes (any browser) |
| **Shareable** | ❌ Needs license | ✅ Just send HTML file |
| **Data channels** | 1000+ | 3 (throttle/brake/steering) |

**Bottom line**: You get 80% of MoTeC's core visualization features for 0% of the cost, and it works with console gameplay!

---

## Technical Details

### File Format

**HTML file contains**:
- Full Plotly.js library (self-contained, works offline)
- Your telemetry data embedded as JSON
- Interactive controls and rendering engine

**File size**: ~4-5MB (larger than PNG, but includes all interactivity)

**Compatibility**: Works in:
- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Any modern browser (2020+)

### Data Structure

Same CSV format as before:

```csv
frame,time,throttle,brake,steering
0,0.00,0.0,0.0,0.00
1,0.03,23.5,0.0,0.12
2,0.07,45.8,0.0,0.23
...
```

---

## Next Steps & Future Features

### Phase 2: Enhanced Features (Planned)

- [ ] **Automatic lap splitting**: Detect lap start/end from video
- [ ] **Delta analysis**: Show time delta between laps
- [ ] **Track map overlay**: Plot telemetry on circuit layout
- [ ] **Gear detection**: Add gear info from HUD
- [ ] **Lap time OCR**: Extract lap times from video

### Phase 3: Web UI (Future)

- [ ] **Drag-and-drop upload**: Upload videos in browser
- [ ] **Cloud processing**: No local Python setup needed
- [ ] **YouTube integration**: Analyze any ACC video URL
- [ ] **Lap database**: Store and compare your entire lap history

---

## Troubleshooting

### HTML file won't open
- **Solution**: Right-click → Open with → Chrome/Firefox

### Graphs are blank
- **Check**: CSV file has data (not empty)
- **Check**: Browser console for JavaScript errors (F12)

### Slow performance
- **Cause**: Very long videos (10+ minutes)
- **Solution**: Trim video to specific laps before processing

### Comparison shows misaligned laps
- **Cause**: Laps start at different times
- **Future fix**: We'll add time alignment feature

---

## Sharing Telemetry

### Send to friends

1. Just send the HTML file (e.g., via Discord, email)
2. They open it in browser - no software needed!
3. They can zoom, compare, analyze just like you

### YouTube Analysis

1. Download ACC video from YouTube (e.g., top driver's lap)
2. Place it in `videos/` and run `python main.py`
3. Compare your lap vs theirs using `plot_position_based_comparison()` / `plot_lap_comparison()`
4. Learn from the differences!

---

## Summary

You now have **free, interactive telemetry visualization** that:

✅ Works with console gameplay (PS5/Xbox)  
✅ Provides zoom, pan, hover tooltips  
✅ Compares multiple laps  
✅ Exports to shareable HTML  
✅ Costs 0 zł (vs MoTeC's ~4,000 zł)  
✅ Doesn't require any additional software  

**Next time you race**: Record gameplay → Extract telemetry → Analyze in browser → Improve lap times! 🏁

---

**Questions?** Just ask or check the main README.md for more info.

