# ACC Telemetry Extractor - User Guide

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Place gameplay video(s) in videos/
mkdir -p videos
cp /path/to/your/acc_video.mp4 videos/

# 3. Extract telemetry (select video + ROI profile when prompted)
python main.py
```

### Position-based lap comparison

After extraction, generate a comparison from the CSV using the visualizer API:

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

Time-based multi-lap overlay (same session CSV):

```python
viz.plot_lap_comparison(df, lap_numbers=[22, 23])
```

## Video Configuration

Place `.mp4` files in `videos/`. `main.py` interactively asks which video and which ROI profile (from `config/roi_config.yaml`) to use.

## What You Get

### Output Files (in data/output/)

1. **CSV File**: `telemetry_YYYYMMDD_HHMMSS.csv`
   - Frame-by-frame data: throttle, brake, steering, speed, gear, lap number, track position
   - Import into Excel, Google Sheets, or analysis tools

2. **Interactive HTML**: `telemetry_interactive_YYYYMMDD_HHMMSS.html`
   - Browser-based visualization with zoom, pan, hover tooltips
   - Synchronized plots (throttle, brake, steering, speed)
   - Works offline, shareable

3. **Position-Based Comparison** (via visualizer API): `lap_comparison_position_YYYYMMDD_HHMMSS.html`
   - Compare laps by track position (not time)
   - Shows time delta at each position
   - Interactive dropdown to select which laps to compare
   - **This is the gold standard for racing analysis**

## Interactive Visualization

### Features

The HTML visualizations provide professional-grade analysis:

- **Zoom**: Click and drag to zoom into any region
- **Pan**: Drag while zoomed to navigate
- **Hover**: See exact values at any point
- **Synchronized views**: All plots zoom together
- **Range slider**: Quick navigation timeline
- **Export**: Download as PNG from browser

### How to Use

1. **Open HTML file** in any modern browser (Chrome, Firefox, Safari, Edge)
2. **Explore the full lap**: Scroll through time using the range slider
3. **Zoom into sections**: Click-drag to select braking zones, corner entries
4. **Analyze technique**: Compare throttle/brake/steering smoothness

## Position-Based Lap Comparison

### Why Position-Based?

**Problem with time-based comparison:**
- If you brake earlier/later, the rest of the lap is out of sync
- Can't see WHERE on track you gain or lose time

**Solution with position-based:**
- Aligns laps by track position (0% = start/finish, 100% = back to start)
- Shows time delta at each position
- Directly compare inputs at the same corners

### Usage

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

Or use the web API `POST /api/telemetry/compare` when running `python run_server.py` (returns JSON lap arrays; see [QUICKSTART_WEB.md](../QUICKSTART_WEB.md)). For the Plotly HTML overlay, call `plot_position_based_comparison()` as shown above.

### The Visualization

**5 Synchronized Plots:**
1. Throttle overlay
2. Brake overlay
3. Steering overlay
4. Speed overlay
5. **Time Delta** - where you gain (negative) or lose (positive) time

**Dropdown Menu**: Select which two laps to compare

### Analysis Workflow

1. **Load comparison** - Generate from your multi-lap CSV
2. **Select laps** from dropdown (e.g., "Lap 22 vs Lap 23")
3. **Check time delta** - Where does it increase (losing time)?
4. **Zoom to problem areas** - Click-drag on the section
5. **Compare inputs** - Are you braking too early? Getting on throttle late?
6. **Repeat** - Try different lap combinations

### Example Analysis

**Time delta plot shows:**
- 0% position: 0.0s (equal start)
- 25% position: -0.5s (Lap A ahead)
- 50% position: -1.2s (Lap A more ahead)
- 75% position: -0.8s (Lap A lost some time)
- 100% position: -1.5s (Lap A 1.5s faster overall)

**Zoom to 50-75%** (where time was lost):
- Brake plot: Lap A braked earlier
- Speed plot: Lap A minimum corner speed lower
- Throttle plot: Lap A got on throttle later
- **Conclusion**: Braking too early, not carrying enough speed

## Understanding the Data

### CSV Columns

| Column | Range | Description |
|--------|-------|-------------|
| `frame` | 0-N | Frame number |
| `time` | 0.0-N.N | Time in seconds |
| `lap_number` | 1-99 | Current lap (from HUD) |
| `track_position` | 0.0-100.0 | Position around track (%) |
| `speed` | 0-300+ | Speed in km/h |
| `gear` | 1-6 | Current gear |
| `throttle` | 0.0-100.0 | Throttle input (%) |
| `brake` | 0.0-100.0 | Brake input (%) |
| `steering` | -1.0 to +1.0 | Steering (-1=full left, +1=full right) |
| `tc_active` | 0 or 1 | Traction control active |
| `abs_active` | 0 or 1 | ABS active |

### What "Good" Looks Like

**Throttle:**
- Long green sections (full throttle on straights)
- Smooth ramps (not jagged)
- Early application on corner exit

**Brake:**
- Sharp initial application
- Smooth trail-off
- No pumping (multiple spikes)

**Steering:**
- Smooth curves
- No sudden changes
- Minimal corrections (jagged = corrections = instability)

**Speed:**
- High minimum corner speeds
- Smooth acceleration/deceleration

## Common Use Cases

### 1. Find Your Braking Points

1. Open interactive HTML
2. Zoom into brake plot
3. Note where brake spikes occur (track position %)
4. Use these as reference points for next session

### 2. Improve Consistency

1. Extract telemetry from a multi-lap session
2. Use position-based comparison to overlay laps
3. Look for variations in braking points, min corner speed, throttle application
4. Focus on corners with most variation

### 3. Compare vs Faster Drivers

1. Download YouTube video of a fast lap into `videos/`
2. Extract their telemetry with `python main.py`
3. Extract your lap telemetry
4. Compare using `plot_position_based_comparison()` (or merge CSVs carefully for cross-session work)
5. Identify where they're different

### 4. Analyze Driving Style

1. Check full throttle % in statistics
2. Look for trail braking
3. Check steering smoothness
4. Analyze TC/ABS activation frequency

## Resolution Configuration

ROI coordinates in `config/roi_config.yaml` are organized as **named profiles**. Pick the matching profile when `main.py` prompts you.

Shipped profiles include `my_ps5_1080p`, `assetto_corsa_1080p`, `twitch_720p`, and `go_setups_720p`. There is no single default 720p layout.

`assetto_corsa_1080p` is for Assetto Corsa original, not Competizione. Select it by name in `main.py` (the web API will not pick it from video height). Its throttle and brake bars are vertical, so those ROIs set `orientation: vertical`. ACC profiles set `orientation: horizontal`, which is also the default when the key is omitted. The empty bar is transparent, so the car interior shows through and moves as the camera pitches. Vertical measurement only counts color anchored at the bottom of the bar.

### Scaling guidance (from a known base resolution)

**1920×1080 (1080p)**: Multiply 720p coordinates by 1.5  
**2560×1440 (1440p)**: Multiply by 2.0  
**3840×2160 (4K)**: Multiply by 3.0

**To recalibrate:**
1. Extract a frame:
   ```bash
   mkdir -p debug
   python -c "import cv2; cap=cv2.VideoCapture('videos/your_video.mp4'); _,f=cap.read(); cv2.imwrite('debug/frame.png',f); cap.release()"
   ```
2. Open in an image viewer with pixel coordinates (GIMP, Photoshop)
3. Locate HUD elements and measure coordinates
4. Update (or add) a profile in `config/roi_config.yaml`

## Performance Expectations

### Processing Speed

Typical performance on a modern CPU:
- ~5-10ms per frame
- 30 FPS video ≈ 100-200 FPS processing speed
- 10-minute video processes in ~1-2 minutes

**OCR Performance:**
- Template matching (lap numbers): ~2ms per frame
- tesserocr (speed/gear): ~2ms per frame
- pytesseract fallback: ~50ms per frame (if tesserocr unavailable)

### File Sizes

- CSV: ~1-2MB per 10 minutes of video
- Interactive HTML: ~4-5MB
- Position comparison HTML: ~500KB per lap comparison

## Tips & Best Practices

### Recording Tips

1. **Keep HUD visible**
2. **Stable camera** (cockpit/bumper view)
3. **Good lighting** so HUD is clear
4. **Full laps** for best results
5. **High quality** (1080p+) helps OCR

### Analysis Tips

1. Compare adjacent laps first
2. Use position percentages as corner references
3. Focus on one corner per session
4. Look for repeating weak sections
5. Share HTML files with coaches/teammates

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

**Quick fixes:**
- **No data extracted**: Check ROI profile matches your video resolution
- **Wrong values**: Verify HUD is visible
- **No lap numbers**: Ensure lap indicator is visible
- **No position data**: Configure `track_map` ROI and ensure minimap is visible

## Next Steps

1. Extract your first session: `python main.py`
2. Explore the interactive HTML
3. Run position-based comparison via the visualizer API
4. Identify weak points and practice
5. Re-analyze after practice to measure improvement

## Related Documentation

- [FEATURES.md](FEATURES.md) - Feature descriptions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical details
- [README.md](../README.md) - Project overview
