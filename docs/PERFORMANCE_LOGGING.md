# Performance Logging Feature

## Overview
Added comprehensive performance tracking to `main.py` to monitor the execution time of each processing step. This helps identify bottlenecks and optimize the video processing pipeline.

## What's Measured

### Per-Frame Operations (tracked every frame):
1. **Telemetry Extraction** - Throttle, brake, steering bar analysis
2. **Lap Number Detection** - Competizione OCR (tesserocr / pytesseract) or AC glyph templates
3. **Speed Extraction** - Competizione OCR or AC glyph templates
4. **Gear Extraction** - OCR for current gear
5. **Lap Transition Detection** - Logic to detect lap changes
6. **Lap Time Extraction** - OCR for lap times (only on transition frames)
7. **Data Storage** - Appending data to Python list
8. **Frame Processing** - Total time per frame (sum of all above)

### Output Generation:
- DataFrame creation
- CSV export
- Interactive HTML graph generation

### Overall:
- Total execution time (wall clock)

## Performance Report Format

The tool now outputs a detailed performance breakdown:

```
⏱️  Performance Breakdown:
   Operation                      Total (s)    Avg (ms)     Min (ms)     Max (ms)     % of Total  
   ----------------------------------------------------------------------------------------------------
   Frame Processing               45.23        15.08        12.34        89.45        100.0%      
   Telemetry Extraction           12.34        4.11         3.45         12.23        27.3%       
   Lap Number Detection           8.56         2.85         2.10         45.67        18.9%       
   Speed Extraction               15.67        5.22         4.89         23.45        34.6%       
   Gear Extraction               6.78         2.26         1.98         15.34        15.0%       
   Lap Transition Detection       0.12         0.04         0.02         0.15         0.3%        
   Lap Time Extraction           0.45         0.15         0.10         0.89         1.0%        
   Data Storage                  1.31         0.44         0.38         1.23         2.9%        
   ----------------------------------------------------------------------------------------------------
   TOTAL                          45.23

   Per-frame average: 15.08ms
   Frames processed: 3000
   Actual FPS: 66.33
```

## Key Metrics Explained

### Average Time per Frame
- Shows typical processing time for one frame
- Lower is better
- Compare against video FPS to determine if real-time processing is possible

### Min/Max Times
- **Min**: Fastest frame processed (best case)
- **Max**: Slowest frame processed (worst case, often when OCR operations occur)
- Large variance indicates inconsistent performance

### Percentage of Total
- Shows which operation takes most time
- Helps prioritize optimization efforts
- Example: If "Speed Extraction" is 40%, optimizing OCR will have biggest impact

### Actual FPS
- Processing speed in frames per second
- If Actual FPS > Video FPS (30): Can process in real-time
- If Actual FPS < Video FPS: Processing takes longer than video playback

## Output Generation Summary
```
Output Generation Summary:
   DataFrame creation: 125.3ms
   CSV export: 45.2ms
   Graph generation: 2.34s
   Total: 2.51s
```

Shows time spent creating outputs after video processing is complete.

## Total Execution Time
```
⏱️  Total Execution Time: 47.74s (0.8 minutes)
```

Wall-clock time from start to finish, including initialization and cleanup.

## Usage

Performance logging is **always enabled** - no configuration needed. Just run:

```bash
python main.py
```

The performance report automatically appears after video processing completes.

## Interpreting Results

### Good Performance Indicators:
- ✅ Frame processing < 33ms average (can process 30 FPS video in real-time)
- ✅ Low variance between min/max times (consistent performance)
- ✅ Telemetry extraction < 30% of total time (efficient CV operations)
- ✅ Data storage < 5% of total time (minimal overhead)

### Performance Issues:
- ⚠️ Speed/Gear extraction > 50% of total time (OCR bottleneck)
- ⚠️ Max time >> Avg time (occasional slowdowns, likely OCR warmup)
- ⚠️ Actual FPS < 10 (very slow processing)

### Optimization Targets:
1. **If OCR is slow**: Consider caching, template matching instead of OCR
2. **If telemetry extraction is slow**: Review HSV color detection, optimize ROI sizes
3. **If frame processing overhead is high**: Optimize video reading, reduce copies

## Example Analysis

From typical run:
```
Speed Extraction: 5.22ms avg, 34.6% of total
Telemetry Extraction: 4.11ms avg, 27.3% of total
```

**Interpretation**: OCR operations (speed) take more time than computer vision (telemetry bars). This is expected since OCR is more complex than color detection.

## Future Enhancements

Possible additions:
- [ ] JSON export of performance data for analysis
- [ ] Performance comparison between runs
- [ ] Real-time performance dashboard during processing
- [ ] Automatic bottleneck detection with suggestions
- [ ] Per-operation breakdown (e.g., HSV conversion, masking, median calculation)



