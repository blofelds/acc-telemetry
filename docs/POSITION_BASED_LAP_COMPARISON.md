# Position-Based Lap Comparison

## Overview

The **Position-Based Lap Comparison** tool allows you to compare multiple laps by **track position** rather than time. This is the gold standard for analyzing racing performance because it shows exactly where on the track you gain or lose time.

### Why Position-Based Comparison?

**Problem with time-based comparison:**
- If you brake earlier or later, the rest of the lap is out of sync
- Can't see exactly where you gained/lost time around the track
- Hard to identify specific corners that need improvement

**Solution with position-based comparison:**
- Aligns laps by track position (0% = start/finish line, 50% = halfway around track)
- Shows time delta at each position: where you're ahead (green) or behind (red)
- Directly compare throttle/brake/steering inputs at the same corners
- Immediately identify problematic sections of the track

## Features

✅ **Interactive Dropdown Menu** - Select which two laps to compare  
✅ **5 Synchronized Plots** - All aligned by track position (0-100%)  
  1. Throttle comparison overlay
  2. Brake comparison overlay
  3. Steering comparison overlay
  4. Speed comparison overlay
  5. **Time Delta** - Shows exactly where time is gained or lost

✅ **Smart Interpolation** - Resamples data at fixed position intervals (every 0.5%)  
✅ **Accurate Time Delta** - Calculates frame-based time differences at each position  
✅ **Unified Hover** - See all values at once when you hover  
✅ **Interactive Zoom/Pan** - Click and drag to zoom, pan to navigate  
✅ **Range Slider** - Quick navigation at bottom of chart  

## Requirements

Your telemetry CSV must have:
- `lap_number` column (integer lap numbers)
- `track_position` column (0.0-100.0% around track)
- At least 2 complete laps with position data

To generate this data, run `main.py` with track position tracking enabled (requires minimap ROI configuration).

## Usage

### Basic Usage

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

The visualizer will:
1. Load the CSV and validate it has position data
2. Generate pairwise comparisons between laps
3. Create an interactive HTML file under `data/output/`
4. Return the path to the saved file

> **Note:** The former standalone script `compare_laps_by_position.py` has been removed. Use `InteractiveTelemetryVisualizer.plot_position_based_comparison()` as shown above to write the HTML file. The web API `POST /api/telemetry/compare` returns JSON lap arrays for a client to plot; it does not generate that HTML.

### Output

The tool generates an HTML file in `data/output/` named:
```
lap_comparison_position_YYYYMMDD_HHMMSS.html
```

Open this file in any web browser for interactive analysis.

## Understanding the Visualization

### The Dropdown Menu
Located at the top-left of the chart. Select which two laps to compare:
- **"Lap 22 vs Lap 23"** - Compare lap 22 (green) against lap 23 (red)
- Switch between comparisons instantly without regenerating

### The Plots

#### 1-4: Telemetry Overlays (Throttle, Brake, Steering, Speed)
- **X-axis**: Track position (0% = start/finish line, 100% = back to start)
- **Y-axis**: Input value (%, steering angle, km/h)
- **Green line**: First lap (baseline)
- **Red line**: Second lap (comparison)

**How to use:**
- Look for differences in braking points (where brake line starts)
- Compare corner entry speed (speed at brake point)
- Check throttle application points (where throttle line rises)
- Examine steering smoothness (jagged = corrections, smooth = confident)

#### 5: Time Delta Plot
- **X-axis**: Track position (0-100%)
- **Y-axis**: Time difference in seconds
- **Interpretation**:
  - **Negative delta** (below zero): Lap A is FASTER (ahead) at this position
  - **Positive delta** (above zero): Lap A is SLOWER (behind) at this position
  - **Slope changes**: Where time is being gained or lost

**Example:**
```
Position:  0%    25%    50%    75%    100%
Delta:    0.0s  -0.5s  -1.2s  -0.8s   -1.5s
          │      │      │      │       │
          Start  Ahead  More   Lost    Final
                        ahead  some    delta
```
This shows Lap A is 1.5s faster overall, gained most time in the first half, lost a bit in the third quarter.

### Interactive Controls

**Zoom:**
- Click and drag to select an area → zooms into that region
- Great for analyzing specific corners in detail

**Pan:**
- While zoomed, drag the plot to move around
- Use range slider at bottom to jump to different sections

**Hover:**
- Move mouse over any plot to see exact values
- All 5 plots show values at the same position simultaneously

**Reset:**
- Double-click anywhere on the plot to reset zoom
- Or use the "Autoscale" button in the toolbar

## Practical Analysis Workflow

### 1. Identify Problem Areas
Look at the **Time Delta** plot first:
- Where does the delta increase (losing time)?
- Where does it decrease (gaining time)?

### 2. Zoom Into Problem Sections
- Click-drag on the time delta to zoom into losing sections
- All plots zoom together - now you can see the inputs

### 3. Compare Inputs at Problem Areas
**If losing time:**
- **Check brake plot**: Are you braking too early? Too much?
- **Check throttle plot**: Are you getting on throttle too late?
- **Check speed plot**: Is your minimum corner speed lower?
- **Check steering plot**: Are you making corrections? (jerky = corrections)

### 4. Repeat for Multiple Comparisons
Use the dropdown to compare different lap combinations:
- **Best lap vs Average lap**: What made the best lap special?
- **Early laps vs Late laps**: Are you getting better or worse?
- **Consecutive laps**: Which lap is more consistent?

## Example Interpretation

### Scenario: Lap 3 is 2 seconds slower than Lap 2

**Step 1: Load comparison**
```python
viz.plot_position_based_comparison(df)  # then open the generated HTML
```
Select "Lap 2 vs Lap 3" from dropdown.

**Step 2: Check Time Delta**
- Notice delta increases from 45% to 55% (losing ~1 second here)
- This is Turn 7 based on track knowledge

**Step 3: Zoom to 45-55%**
- Click-drag on time delta from 45% to 55%

**Step 4: Analyze Inputs**
- **Brake**: Lap 3 brakes at 46%, Lap 2 brakes at 48% → braking too early!
- **Speed**: Lap 3 minimum speed is 85 km/h, Lap 2 is 92 km/h → carrying less speed
- **Throttle**: Lap 3 gets on throttle at 52%, Lap 2 at 50% → late on gas
- **Steering**: Lap 3 shows corrections, Lap 2 is smooth → not confident

**Conclusion**: Turn 7 issue
- Brake later (2% position later = ~20 meters at 250 km/h)
- Carry more speed through apex (work on line and confidence)
- Get on throttle earlier (smoother exit = earlier throttle)

**Action**: Next session, focus on Turn 7 braking point and apex speed.

## Tips & Best Practices

### Data Quality
- **Full laps only**: Incomplete laps will have gaps in position coverage
- **Clean laps**: Avoid laps with incidents or off-track excursions
- **Multiple laps**: More data = more comparisons = better insights

### Analysis Tips
1. **Compare adjacent laps first** (22 vs 23, 23 vs 24)
   - Shows immediate improvement or regression
   - Easier to remember what you changed

2. **Compare best vs worst**
   - Identify largest differences
   - Shows your maximum potential vs bad execution

3. **Look for patterns**
   - If you always lose time in the same section, that's your weak point
   - If time delta is consistent, you're making the same mistake repeatedly

4. **Use position percentages as reference**
   - Learn what % corresponds to each corner
   - Makes it easier to discuss with coaches or teammates
   - "I'm losing 0.5s at 35%" = specific actionable feedback

### Performance Notes
- Tool handles 10+ laps easily (generates all pairwise comparisons)
- HTML file size: ~500KB per lap comparison
- Loads instantly in modern browsers
- No server required - works offline

## Technical Details

### Position Resampling
The tool resamples telemetry at fixed position intervals (default: 0.5%):
- Creates 201 data points per lap (0%, 0.5%, 1.0%, ..., 100%)
- Uses linear interpolation between actual frame positions
- Ensures both laps have data at identical positions for comparison

### Time Delta Calculation
```
time_delta[position] = (time_lap_a[position] - time_lap_a[0%]) - (time_lap_b[position] - time_lap_b[0%])
```
- Subtracts start time to get relative lap time at each position
- Positive delta = Lap A is slower (behind)
- Negative delta = Lap A is faster (ahead)

### FPS Detection
Automatically detects video FPS from data:
```
fps = (total_frames) / (total_time_seconds)
```
Used for accurate time calculations.

## Comparison: Time-Based vs Position-Based

### Time-Based Comparison (`plot_lap_comparison()`)
**Use when:**
- Comparing laps from the same session CSV by elapsed time
- Analyzing overall consistency over time
- Looking at lap time trends

**Limitations:**
- Can't show WHERE on track time is gained/lost
- Out of sync after first difference
- Hard to identify specific problem corners

### Position-Based Comparison (`plot_position_based_comparison()`)
**Use when:**
- Analyzing WHERE on track you gain/lose time
- Comparing driving technique at specific corners
- Identifying weak points in your lap
- Training to improve specific sections

**Requires:**
- Track position data (minimap tracking)
- Multiple laps in a single session CSV

## Troubleshooting

### "No track_position data found"
**Problem**: CSV doesn't have position tracking  
**Solution**: 
1. Ensure minimap is visible in video
2. Configure `track_map` ROI in `config/roi_config.yaml`
3. Re-run `main.py` to regenerate CSV with position data

### "Need at least 2 laps for comparison"
**Problem**: Only 1 lap has position data  
**Solution**: Record longer video with multiple laps

### "Lap has gaps in position coverage"
**Problem**: Red dot not detected in some frames (occluded by UI)  
**Solution**: Normal - interpolation fills small gaps automatically

### Dropdown doesn't show all expected comparisons
**Problem**: Some laps filtered out due to incomplete data  
**Solution**: Check console output for which laps were skipped

## Future Enhancements

Potential improvements:
- [ ] Color-code time delta (green = gaining, red = losing)
- [ ] Add sector analysis (split track into sectors)
- [ ] Overlay both laps on track map visualization
- [ ] Export comparison data to CSV
- [ ] Add throttle/brake traces on time delta plot
- [ ] Support comparing more than 2 laps simultaneously
- [ ] Add statistical comparison (best/average/worst per section)

## Related Documentation

- [TRACK_POSITION_TRACKING.md](TRACK_POSITION_TRACKING.md) - How position tracking works
- [INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md) - General visualization features
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Overall project overview

## Feedback

This tool was built to solve a real problem for console sim racers who can't access native telemetry. If you have suggestions for improvements or find issues, please let the developer know!

---

**Remember**: The goal isn't just to be faster - it's to understand WHY you're faster in some laps and not others. Position-based comparison gives you that insight! 🏁

