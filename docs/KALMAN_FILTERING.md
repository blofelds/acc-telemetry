# Kalman Filtering for Position Tracking - [DEPRECATED]

> **Historical document:** Describes a past feature announcement or diagnostic session. Some referenced standalone scripts (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, various `test_*.py` / `debug_*.py` helpers) are **no longer in this repository**. Prefer current workflows in [USER_GUIDE.md](USER_GUIDE.md) / [README.md](../README.md): `python main.py` and `InteractiveTelemetryVisualizer` APIs.


## ⚠️ IMPORTANT: This Approach Was Abandoned

**Status:** This document describes an experimental Kalman filtering implementation that was **later replaced** with a simpler approach.

**Current implementation:** The project now uses basic forward-progress validation (`max_jump_per_frame` threshold) instead of Kalman filtering. See `PositionTrackerV2` class for the current implementation.

**Why abandoned:** Kalman filtering added unnecessary complexity for minimal benefit. A simple outlier rejection based on maximum allowed jump per frame proved sufficient and more maintainable.

**Historical context:** This document is preserved to document the development process and explain why this approach was tried and ultimately discarded.

---

## Overview (Historical)

An experimental implementation included **Kalman filtering** to eliminate glitches and smooth position data. This was intended to address single-frame position errors that cause false spikes in lap comparison visualizations.

## The Problem

### Position Tracking Glitches

When tracking position via red dot detection on the minimap:
- **Single-frame errors** can occur (red dot occluded, misdetected, etc.)
- Example: Position jumps from 49% to 71% for one frame
- Causes **false time delta spikes** in position-based lap comparison
- Makes analysis unreliable

### Example from Real Data
```
Frame 14776: Position = 48.99% ❌ (should be ~71%)
Frame 14777: Position = 71.02% ✓ (correct)
```

This creates a 22% gap in position data, causing artificial time delta of -32 seconds!

## The Solution: Kalman Filtering

Kalman filters are the **gold standard** for sensor fusion and noise rejection in tracking systems. Used in:
- GPS navigation
- Aircraft autopilots
- Robot localization
- Autonomous vehicles

### How It Works

1. **Predict**: Estimate next position based on current position + velocity
2. **Measure**: Get actual position from red dot detection
3. **Compare**: Calculate "innovation" (difference between prediction and measurement)
4. **Decide**: 
   - If innovation is small → trust measurement, update filter
   - If innovation is large (>10%) → **reject as outlier**, use prediction
5. **Output**: Smooth, reliable position

### Mathematical Model

**State vector:** `[position, velocity]`
- Position: 0-100% around track
- Velocity: %/frame (how fast position changes)

**Prediction:**
```
position_new = position_old + velocity * dt
velocity_new = velocity_old
```

**Measurement:**
- We only measure position (from red dot)
- Velocity is estimated by the filter

**Outlier Detection:**
```
innovation = |measured_position - predicted_position|
if innovation > 10%:
    reject measurement (use prediction)
else:
    accept measurement (update filter)
```

## Implementation

### FilterPy Library

Uses [FilterPy](https://github.com/rlabbe/filterpy) - a well-maintained Python Kalman filtering library.

```python
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
```

### Integration in PositionTrackerV2

**Initialization:**
```python
def __init__(self, fps=30.0, enable_kalman=True):
    # 1D Kalman filter for position
    self.kf = KalmanFilter(dim_x=2, dim_z=1)
    
    # State: [position, velocity]
    self.kf.x = np.array([[0.], [0.]])
    
    # State transition (constant velocity model)
    dt = 1.0 / fps
    self.kf.F = np.array([[1., dt],
                          [0., 1.]])
    
    # Measurement function (measure position only)
    self.kf.H = np.array([[1., 0.]])
    
    # Measurement uncertainty (2% position noise)
    self.kf.R = np.array([[2.0]])
    
    # Process noise (velocity changes)
    self.kf.Q = Q_discrete_white_noise(dim=2, dt=dt, var=1.0)
    
    # Outlier threshold (10% position jump)
    self.outlier_threshold = 10.0
```

**Position Extraction with Filtering:**
```python
def extract_position(self, map_roi):
    # 1. Detect red dot
    dot_position = self.detect_red_dot(map_roi)
    
    # 2. Calculate raw position
    raw_position = self.calculate_position(dot_x, dot_y)
    
    # 3. Apply Kalman filter
    return self._apply_kalman_filter(raw_position)

def _apply_kalman_filter(self, measurement):
    # Predict
    self.kf.predict()
    predicted = self.kf.x[0, 0]
    
    # Check for outlier
    innovation = abs(measurement - predicted)
    
    if innovation > self.outlier_threshold:
        # Reject outlier
        return predicted  # Use prediction
    else:
        # Accept measurement
        self.kf.update(measurement)
        return self.kf.x[0, 0]  # Use filtered value
```

## Results

### Test Case: Simulated Outlier

**Input:** Smooth 40% → 60% progression with 71% outlier at frame 50

```
Frame 50:
  Raw measurement: 71.0%
  Predicted: 50.0%
  Innovation: 21.0% (> 10% threshold)
  → Outlier REJECTED
  Filtered output: 50.0% ✓
```

**Result:** Outlier completely suppressed, smooth trajectory maintained.

### Real World Impact

**Before Kalman filtering:**
```
Lap 4 comparison:
  Frame 14776: 49% → 71% jump
  Time delta spike: -32.5 seconds
  Analysis: UNRELIABLE ❌
```

**After Kalman filtering:**
```
Lap 4 comparison:
  Frame 14776: Outlier rejected (71% → 49.2%)
  Time delta: Smooth, no spike
  Analysis: RELIABLE ✓
```

## Configuration

### Enable/Disable Kalman Filtering

```python
# Enable (default)
tracker = PositionTrackerV2(enable_kalman=True)

# Disable (use raw positions)
tracker = PositionTrackerV2(enable_kalman=False)
```

### Tuning Parameters

Located in `PositionTrackerV2.__init__()`:

**Outlier Threshold** (default: 10%)
```python
self.outlier_threshold = 10.0  # Reject jumps > 10%
```
- Lower = more aggressive filtering (rejects smaller jumps)
- Higher = more permissive (allows larger jumps)

**Measurement Noise** (default: 2%)
```python
self.kf.R = np.array([[2.0]])  # 2% uncertainty
```
- Lower = trust measurements more (less smoothing)
- Higher = trust measurements less (more smoothing)

**Process Noise** (default: 1.0)
```python
self.kf.Q = Q_discrete_white_noise(dim=2, dt=dt, var=1.0)
```
- Lower = assume smooth motion (slow velocity changes)
- Higher = allow jerky motion (rapid velocity changes)

## Advantages

✅ **Automatic outlier rejection** - No manual data cleaning needed  
✅ **Smooth tracking** - Eliminates single-frame glitches  
✅ **Handles missing data** - Prediction fills gaps when red dot not detected  
✅ **Velocity estimation** - Bonus: get speed around track (future feature)  
✅ **Minimal performance impact** - ~0.1ms per frame  
✅ **Battle-tested algorithm** - Used in professional tracking systems  

## Limitations

⚠️ **Assumes smooth motion** - Works best when car moves at roughly constant speed  
⚠️ **Threshold tuning** - May need adjustment for different tracks/driving styles  
⚠️ **Wraparound handling** - Special logic needed at 0%/100% boundary  

## Debug Information

Get Kalman filter status:
```python
debug_info = tracker.get_debug_info()

print(f"Kalman enabled: {debug_info['kalman_enabled']}")
print(f"Kalman initialized: {debug_info['kalman_initialized']}")
print(f"Current position: {debug_info['kalman_position']}")
print(f"Current velocity: {debug_info['kalman_velocity']}")
print(f"Outliers rejected: {debug_info['outlier_count']}")
```

## Testing

Run the test script to verify Kalman filtering:
```bash
# test_kalman_filtering.py removed — see tests/test_position_tracker_v2.py
```

This simulates position tracking with a known outlier and visualizes the filtering result.

## Future Enhancements

Potential improvements:
- [ ] Adaptive outlier threshold based on track section
- [ ] Extended Kalman Filter (EKF) for non-linear motion
- [ ] Multi-hypothesis tracking for ambiguous detections
- [ ] Velocity-based smoothing (use speed data from HUD)
- [ ] Track-specific tuning profiles

## References

- [FilterPy Documentation](https://filterpy.readthedocs.io/)
- [FilterPy GitHub](https://github.com/rlabbe/filterpy)
- [Kalman and Bayesian Filters in Python](https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python/) - Free online book

## Related Documentation

- [TRACK_POSITION_TRACKING.md](TRACK_POSITION_TRACKING.md) - How position tracking works
- [POSITION_BASED_LAP_COMPARISON.md](POSITION_BASED_LAP_COMPARISON.md) - Using position data for comparison
- [WHATS_NEW_POSITION_COMPARISON.md](WHATS_NEW_POSITION_COMPARISON.md) - Position comparison feature

---

## Final Note: Why This Approach Was Replaced

**Kalman filtering was successfully implemented and tested**, but ultimately replaced with a simpler approach in `PositionTrackerV2`.

**Current implementation:** Simple forward-progress validation using `max_jump_per_frame` threshold (default: 1.0%)
- Rejects position jumps larger than 1% per frame
- Much simpler than full Kalman filter (no state estimation, prediction, covariance matrices)
- Equally effective for rejecting single-frame glitches
- More maintainable and easier to understand

**What we learned:**
- Kalman filtering works well and is production-ready
- However, for post-processing video telemetry, simpler outlier rejection is sufficient
- The added complexity of Kalman filtering wasn't justified by the marginal improvement
- "Simplicity is the ultimate sophistication" - sometimes the simple solution is better

**This document is preserved** to show the development process and explain why various approaches were tried and what we learned from each experiment.

