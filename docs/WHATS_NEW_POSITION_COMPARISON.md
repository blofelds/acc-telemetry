# What's New: Position-Based Lap Comparison

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## Summary

Added **position-based lap comparison** - the gold standard for racing telemetry analysis. This feature allows you to compare laps by track position (not time) to see exactly where you gain or lose time around the track.

## What Was Added

### New Files

1. **~~`compare_laps_by_position.py`~~** (removed) — use `InteractiveTelemetryVisualizer.plot_position_based_comparison()`
   - Loads telemetry CSV with multiple laps
   - Validates data has position information
   - Generates interactive HTML comparison
   - Automatically opens in browser

2. **`docs/POSITION_BASED_LAP_COMPARISON.md`** - Comprehensive user guide
   - Complete explanation of position-based comparison
   - Usage instructions and examples
   - Analysis workflow and interpretation guide
   - Troubleshooting section

### Modified Files

1. **`src/interactive_visualizer.py`** - Added three new methods:
   - `_resample_lap_by_position()` - Interpolates telemetry at fixed position intervals
   - `_calculate_time_delta()` - Computes time differences between laps
   - `plot_position_based_comparison()` - Generates interactive comparison with dropdown

2. **`README.md`** - Updated to highlight new feature
   - Added position-based comparison to feature list
   - Updated quick start guide
   - Added new section explaining the feature
   - Updated project structure
   - Updated roadmap (marked time delta analysis as complete)

3. **~~`compare_laps.py`~~** (removed) — documentation updated to point at visualizer APIs
   - Clarified it's for time-based comparison
   - Added pointer to position-based tool

## Key Features

### Interactive Dropdown Menu
- Select which two laps to compare from dropdown
- Switches comparison instantly without regenerating
- Supports all pairwise combinations (Lap 1 vs 2, 1 vs 3, 2 vs 3, etc.)

### 5 Synchronized Plots
All aligned by track position (0-100%):
1. **Throttle comparison** - Overlay of both laps
2. **Brake comparison** - Overlay of both laps
3. **Steering comparison** - Overlay of both laps
4. **Speed comparison** - Overlay of both laps
5. **Time Delta** - Shows where time is gained (negative) or lost (positive)

### Smart Position Alignment
- Resamples data at fixed position intervals (every 0.5% = 200 points per lap)
- Uses linear interpolation between actual frame positions
- Ensures both laps have data at identical positions for comparison

### Accurate Time Delta
- Calculates relative lap time at each position
- Shows cumulative time difference as you progress around track
- Delta = time_lap_a - time_lap_b
  - Positive = Lap A slower (behind)
  - Negative = Lap A faster (ahead)

## Why This Matters

### Problem with Time-Based Comparison
If you brake earlier or later in one lap, the rest of the lap is out of sync:
- Can't directly compare corner entry technique
- Can't see exactly where time is gained/lost
- Hard to identify specific problem areas

### Solution with Position-Based Comparison
Aligns laps by track position, not time:
- ✅ Direct comparison of inputs at the same corners
- ✅ Time delta shows exactly where time is gained/lost
- ✅ Identify specific problem sections instantly
- ✅ Compare braking points at identical positions
- ✅ See if you're braking too early/late at each corner

## Usage Example

```bash
# 1. Run main.py to generate telemetry with position tracking
python main.py

# 2. Generate position-based comparison
# (removed) use InteractiveTelemetryVisualizer.plot_position_based_comparison(df)
```

Output:
```
======================================================================
ACC Position-Based Lap Comparison Tool
======================================================================

📁 Loading telemetry data from: telemetry_20251024_163152.csv
   ✅ Loaded 15423 frames

📊 Lap Data Summary:
   Lap      Frames     Duration     Position Coverage   
   ------------------------------------------------------------
   1        3028       126.25s      0.0% - 99.9%        
   2        3338       139.18s      0.0% - 99.8%        
   3        3001       125.12s      0.0% - 99.9%        

🎨 Generating position-based comparison visualization...
   Detected FPS: 23.98

📊 Generating position-based lap comparison...
   Found 3 laps
   Generating 3 pairwise comparisons...
   Resampling laps at 0.5% intervals...
      Lap 1: 201 position points
      Lap 2: 201 position points
      Lap 3: 201 position points
   ✅ Position-based comparison saved: data/output/lap_comparison_position_20251024_182513.html
```

## Technical Implementation

### Position Resampling Algorithm
```python
# Create target positions (0.0%, 0.5%, 1.0%, ..., 100.0%)
target_positions = np.arange(0.0, 100.0 + 0.5, 0.5)

# Interpolate telemetry at each target position
throttle_resampled = np.interp(target_positions, 
                               actual_positions, 
                               actual_throttle)
```

### Time Delta Calculation
```python
# Get relative lap times (subtract start time)
lap_a_relative = lap_a['time'] - lap_a['time'][0]
lap_b_relative = lap_b['time'] - lap_b['time'][0]

# Calculate delta at each position
time_delta = lap_a_relative - lap_b_relative
```

### Dropdown Implementation
Uses Plotly `updatemenus` with visibility control:
- All comparison traces are generated upfront
- Dropdown toggles visibility of trace groups
- Instant switching between comparisons

## Requirements

Your telemetry CSV must have:
- `lap_number` column (integer lap numbers)
- `track_position` column (0.0-100.0% around track)
- `throttle`, `brake`, `steering`, `speed`, `time`, `frame` columns
- At least 2 laps with valid position data

To generate this data:
1. Configure `track_map` ROI in `config/roi_config.yaml`
2. Ensure minimap is visible in video
3. Run `main.py` - it will extract position automatically

## Analysis Workflow

### 1. Generate Comparison
```bash
# (removed) use InteractiveTelemetryVisualizer.plot_position_based_comparison(df)
```

### 2. Open HTML in Browser
File opens automatically (or open manually)

### 3. Select Laps to Compare
Use dropdown menu: "Lap 22 vs Lap 23"

### 4. Analyze Time Delta
Look at bottom plot (Time Delta):
- Where does delta increase? (losing time)
- Where does it decrease? (gaining time)
- What's the final delta? (total lap time difference)

### 5. Zoom Into Problem Areas
Click-drag on time delta to zoom into sections where you're losing time

### 6. Compare Inputs
With zoomed view, check throttle/brake/steering/speed plots:
- Are you braking too early?
- Is minimum corner speed lower?
- Are you getting on throttle later?
- Is steering smooth or jerky (corrections)?

### 7. Repeat for Other Comparisons
Switch dropdown to compare other lap combinations

## Example Analysis

**Scenario**: Comparing Lap 1 (126.25s) vs Lap 2 (139.18s)

**Observations from time delta plot:**
- Delta increases from 0s to +5s at 20% position → losing 5s in first sector
- Delta stable from 20-60% → matching pace in middle sector
- Delta increases from +5s to +13s at 60-80% → losing 8s in third sector
- Delta stable from 80-100% → matching pace in final sector

**Action**: Zoom to 0-20% and 60-80% to analyze problem areas

**Findings at 15% position (Turn 3):**
- Lap 2 brakes 2% earlier (at 14% vs 16%)
- Lap 2 minimum speed is 10 km/h slower
- Lap 2 gets on throttle 1% later
- **Conclusion**: Braking too early, not carrying enough speed

**Next Session**: Focus on Turn 3 - brake later, carry more speed

## Performance

- Handles 10+ laps easily (all pairwise comparisons)
- Generation time: ~2-3 seconds for 5 laps
- HTML file size: ~500KB per lap comparison (5MB for 10 comparisons)
- Loads instantly in modern browsers
- No server required - works offline

## Future Enhancements

Planned improvements:
- Color-coded time delta (green/red gradient)
- Overlay both laps on track map
- Sector-based analysis
- Export comparison data to CSV
- Statistical comparison (best/average/worst per section)

## Related Features

This feature builds on:
- Track position tracking (`position_tracker_v2.py`)
- Lap detection (`lap_detector.py`)
- Interactive visualization (`interactive_visualizer.py`)

## Documentation

Complete guides available:
- **[POSITION_BASED_LAP_COMPARISON.md](POSITION_BASED_LAP_COMPARISON.md)** - Full user guide
- **[TRACK_POSITION_TRACKING.md](TRACK_POSITION_TRACKING.md)** - How position tracking works
- **[INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md)** - General visualization features

---

**This is the most powerful analysis feature in the toolset!** 🏁

Position-based comparison is what professional race teams use to analyze telemetry. Now console sim racers have access to the same analysis tools! 🎮🏎️

