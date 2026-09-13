# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

The only GitHub remote for this project is [blofelds/acc-telemetry](https://github.com/blofelds/acc-telemetry).

- Push, pull, and open pull requests only against `origin` (`blofelds/acc-telemetry`).
- Do not fetch, pull, push, or open issues or pull requests against `KubaC701/acc-telemetry`. That remote is not this project's upstream.

## Commit messages

Use Conventional Commits, then a body that explains why. Full rules are in [.cursor/rules/commit-messages.mdc](.cursor/rules/commit-messages.mdc).

```
type(scope): imperative description

What was wrong before, and what to use instead. Wrap at 72 characters.
No trailing period on the subject.
```

## Project Overview

ACC Telemetry Extractor is a **computer vision tool** that extracts detailed telemetry data from Assetto Corsa Competizione gameplay videos. Designed for **console players (PS5/Xbox)** who lack native telemetry export, it analyzes on-screen HUD elements frame-by-frame to extract:

- Throttle/brake inputs (0-100%)
- Steering position (-1.0 to +1.0)
- Speed (km/h) and gear (1-6)
- Lap numbers and lap times
- Track position (0-100% via minimap analysis with Kalman filtering)
- TC/ABS activation status

**Core principle**: If you can see it on screen, we can extract it.

## Project Goals and Vision

### User Background
The user is a sim racing enthusiast who races ACC on **console (PS5)**. They are a self-described "data freak" who loves to compare lap times and analyze driving performance, but console platforms have severe limitations compared to PC:

- **No telemetry export**: PC players can export detailed telemetry data, console players cannot
- **No third-party tools**: Console ecosystem is closed, preventing use of professional telemetry analysis software
- **Limited data access**: Only what's visible on-screen during gameplay

### Project Motivation
This project was born from **necessity and passion**:
1. **Personal need**: Fill the telemetry gap for console sim racers
2. **Learning opportunity**: Explore computer vision and Python as a beginner backend/Python developer
3. **Data analysis**: Enable lap comparison and driving improvement through data
4. **Fun side project**: Combine racing hobby with coding skills

### Target Use Cases

#### Primary: Personal Lap Analysis
- Record gameplay footage from console
- Extract telemetry from video
- Compare multiple laps to find improvements
- Identify braking points, throttle application, steering smoothness
- Analyze corner entry/apex/exit techniques

#### Future: Community Tool
- Share with other console sim racers facing same limitations
- Compare driving styles between different drivers
- Learn from faster drivers by analyzing their YouTube videos
- Build a library of telemetry from various tracks and cars

### Design Principles

#### 1. Accessibility
This tool should be usable by sim racers who aren't programmers:
- Clear installation instructions
- Minimal configuration required
- Helpful error messages
- Example videos and outputs

#### 2. Accuracy Over Speed
It's acceptable to process slowly if results are accurate:
- Console players record footage, then process later (not real-time)
- Better to take 5 minutes for perfect data than 30 seconds for noisy data
- Use robust algorithms (median filtering, multi-color detection)

#### 3. Extensibility
Design with future enhancements in mind:
- Modular architecture (separate video processing, extraction, visualization)
- Configuration-driven (YAML for easy tweaks)
- Well-documented code for contributions

#### 4. Educational Value
The user is learning Python through this project:
- Comprehensive docstrings explaining what code does
- Comments on complex computer vision logic
- Documentation that teaches concepts (HSV color space, ROI extraction, etc.)

## Essential Commands

### Setup and Running
```bash
# Initial setup
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Place videos in videos/, then extract (interactive selection)
# Generates CSV + interactive HTML in data/output/
python main.py

# Optional: start the FastAPI web backend
python run_server.py
```

### Position-based lap comparison
After extraction, use the visualizer API (standalone CLI scripts were removed):

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)   # position-aligned comparison
# viz.plot_lap_comparison(df, lap_numbers=[22, 23])  # time-based overlay
```

### Video Configuration
Place `.mp4` files in `videos/`. `main.py` interactively selects the video and an ROI profile from [config/roi_config.yaml](config/roi_config.yaml).

## Project Structure

### Entry Point
[main.py](main.py) - Main orchestrator that:
- Loads ROI configuration from [roi_config.yaml](config/roi_config.yaml)
- Initializes VideoProcessor, TelemetryExtractor, LapDetector, PositionTrackerV2
- Processes video frame-by-frame
- Exports CSV and generates visualization graphs

### Core Modules (src/)

1. **[video_processor.py](src/video_processor.py)** - VideoProcessor class
   - Opens video files using OpenCV
   - Extracts ROI (Region of Interest) regions from frames
   - Yields frame data via generator pattern
   - Handles video metadata (FPS, frame count, duration)

2. **[telemetry_extractor.py](src/telemetry_extractor.py)** - TelemetryExtractor class
   - Computer vision core: analyzes ROI images using HSV color space
   - `extract_bar_percentage()`: Measures throttle/brake bars (green, yellow, red, orange detection)
   - `extract_steering_position()`: Finds white dot position on steering indicator
   - Bar orientation comes from the ROI profile (`orientation: horizontal` by default; Assetto Corsa original uses `vertical`)
   - Handles color changes when TC/ABS activate (green→yellow, red→orange)

3. **[lap_detector.py](src/lap_detector.py)** - LapDetector class
   - Fast lap number and OCR detection
   - tesserocr for lap numbers, speed, and gear: Direct C++ API, ~2ms per frame
   - pytesseract fallback: lap times at transitions, and if tesserocr is unavailable
   - Temporal smoothing: Majority voting across recent frames

4. **[position_tracker_v2.py](src/position_tracker_v2.py)** - PositionTrackerV2 class
   - Minimap-based track position tracking
   - Extracts white racing line from minimap using multi-frame frequency voting
   - Detects red position dot and calculates track position (0-100%)
   - Kalman filtering: Smooths position, rejects outliers (>10% jumps)
   - Resets on lap transitions to maintain accuracy

5. **[interactive_visualizer.py](src/interactive_visualizer.py)** - InteractiveTelemetryVisualizer class
   - Browser-based interactive Plotly graphs with zoom, pan, hover tooltips
   - Multi-lap overlay with dropdown selector
   - Synchronized plots (throttle, brake, steering, speed, position)

### Configuration
- **[roi_config.yaml](config/roi_config.yaml)** - Named ROI profiles (resolution- and source-specific)
  - Examples: `my_ps5_1080p`, `twitch_720p`, `go_setups_720p`, `assetto_corsa_1080p`
  - Each ROI defined as: `{x, y, width, height}` in pixels
  - **Resolution dependency**: Pick or add a matching profile; do not assume a single 720p layout

### Output Directory
- `data/output/` - Generated files:
  - `telemetry_YYYYMMDD_HHMMSS.csv` - Frame-by-frame raw data (`main.py`)
  - `telemetry_interactive_YYYYMMDD_HHMMSS.html` - Interactive Plotly graphs (`main.py`)
  - `lap_comparison_position_YYYYMMDD_HHMMSS.html` - Position-based comparison (`plot_position_based_comparison()`, not `main.py`)

### Debug Directory
- `debug/` - Temporary debugging workspace (git-ignored)
  - **Purpose**: Store temporary files, test images, debug scripts during development
  - **Workflow**:
    1. Agent creates task-specific subfolder (e.g., `debug/roi_calibration/`, `debug/color_analysis/`)
    2. Store temporary debug artifacts (frame captures, test outputs, analysis scripts)
    3. After task completion, the task-specific subfolder can be safely deleted
  - **Important**: Contents are temporary and should not be committed to version control

### Key Technologies
- **OpenCV** (cv2): Video processing and computer vision
- **NumPy**: Array operations and image manipulation
- **Pandas**: Data structuring and CSV export
- **Matplotlib/Plotly**: Telemetry visualization
- **PyYAML**: Configuration file parsing
- **tesserocr**: Fast OCR for lap numbers and speed/gear
- **pytesseract**: Fallback OCR for lap times

## Architecture Overview

### Processing Pipeline
```
main.py (orchestrator)
  └─> VideoProcessor: Extract frames and ROI regions
  └─> TelemetryExtractor: Analyze ROI images using HSV color detection
  └─> LapDetector: Extract lap numbers, speed, gear, lap times
  └─> PositionTrackerV2: Track position on minimap (with Kalman filtering)
  └─> InteractiveTelemetryVisualizer: Generate CSV + interactive HTML graphs
```

## ROI Configuration Guidelines

### Configuration Structure
The [config/roi_config.yaml](config/roi_config.yaml) file defines where to look for telemetry UI elements in the video.

Coordinates are grouped into **named profiles**. `main.py` prompts for one; the web API matches `720p` / `1080p` in the profile name to video height.

ROI regions defined per profile:
- `throttle`: Horizontal green/yellow bar (bottom-right)
- `brake`: Horizontal red/orange bar (below throttle)
- `steering`: White dot indicator (above throttle)
- `speed`: Speed display (inside rev meter)
- `gear`: Gear number (center of rev meter)
- `lap_number`: Lap flag with number (top-left)
- `last_lap_time`: Completed lap time (top-left)
- `track_map`: Circular minimap (top-left)

Each ROI is defined as:
```yaml
my_ps5_1080p:
  throttle:
    x: 1758        # Left edge position (pixels from left)
    y: 1008        # Top edge position (pixels from top)
    width: 143     # ROI width in pixels
    height: 15     # ROI height in pixels
```

### Resolution Dependency and Scaling

#### Scaling for a new profile
Start from a known profile, then multiply by (new height / profile height):
- **720p → 1080p**: Multiply all values by 1.5
- **720p → 1440p**: Multiply by 2.0
- **720p → 4K**: Multiply by 3.0

Save the result as a **new named profile** rather than overwriting an existing one.

### Finding ROI Coordinates
If the default coordinates don't work for your video:

1. **Extract a test frame**:
   ```bash
   mkdir -p debug
   python -c "import cv2; cap=cv2.VideoCapture('videos/your_video.mp4'); _,f=cap.read(); cv2.imwrite('debug/frame.png',f); cap.release()"
   ```

2. **Open `debug/frame.png` in an image viewer** that shows pixel coordinates (GIMP, Photoshop, Preview with developer tools)

3. **Locate ACC HUD elements** (usually bottom-right corner):
   - Throttle bar: Green/yellow horizontal bar
   - Brake bar: Red/orange horizontal bar below throttle
   - Steering indicator: White dot or scale above bars

4. **Measure coordinates**:
   - Note the top-left corner pixel (x, y)
   - Measure width and height of the element
   - Add 1-2 pixels margin on each side

5. **Update roi_config.yaml** with new values

6. **Test and iterate** until extraction works correctly

### ROI Validation Checklist
- ROI should fully contain the UI element
- Small margin (1-3 pixels) on all sides
- ROI shouldn't overlap with adjacent UI elements
- Width and height should match bar dimensions
- Coordinates should be within video dimensions

### Troubleshooting ROI Issues

#### Symptom: All values are 0% or 100%
**Cause**: ROI is not capturing the correct UI element
**Solution**: ROI coordinates are wrong. Re-extract test frame and verify positions.

#### Symptom: Values fluctuate wildly
**Cause**: ROI is too large and capturing neighboring elements
**Solution**: Reduce ROI width/height to isolate the specific bar.

#### Symptom: Correct values but occasional spikes
**Cause**: ROI edges capturing anti-aliasing artifacts or compression artifacts
**Solution**: This is normal. The median-based detection handles this. If persistent, slightly reduce ROI size.

#### Symptom: Brake detection shows throttle values (or vice versa)
**Cause**: Throttle and brake ROI y-coordinates are swapped
**Solution**: Verify which bar is which in your video. Throttle is usually above brake.

## Computer Vision Guidelines

### Color Space Conversion and HSV Detection

All telemetry extraction uses **HSV color space** instead of BGR:
```python
hsv = cv2.cvtColor(roi_image, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, lower_bound, upper_bound)
```

#### Why HSV?
- Separates color (hue) from brightness (value)
- More robust to lighting variations
- Easier to define color ranges (e.g., "all greens" = H: 35-85)

#### HSV Ranges in Use
See [src/telemetry_extractor.py](src/telemetry_extractor.py) for current values:

- **Green (throttle)**: H: 35-85, S: 50-255, V: 50-255
- **Yellow (TC active)**: H: 15-35, S: 100-255, V: 100-255
- **Red (brake)**: H: 0-10 OR 170-180, S: 100-255, V: 100-255
- **Orange (ABS active)**: H: 10-40, S: 100-255, V: 100-255
- **White/Gray (steering)**: H: any, S: 0-50, V: 100-255

### ROI (Region of Interest) Extraction Pattern

ROI coordinates define where to look on screen:
```python
roi = frame[y:y+height, x:x+width]
```

- **Coordinate system**: (0,0) is top-left corner
- **Units**: Pixels
- **Resolution dependency**: ROI coords must be adjusted for different video resolutions
- **Best practice**: Keep ROI tight around UI element with small margin

### Bar Percentage Detection Strategy

#### Horizontal Bars (Current Implementation)
1. Convert ROI to HSV
2. Create color mask(s) for bar colors
3. Sample middle rows (avoid edge artifacts)
4. Find rightmost filled pixel in each row
5. Calculate median filled width
6. Convert to percentage: `(filled_width / total_width) * 100`

#### Vertical Bars (Alternative)
1. Sample middle columns
2. Find topmost filled pixel (bars fill from bottom)
3. Calculate filled height from bottom
4. Use median to handle outliers

### Multi-Color Detection for TC/ABS
Bars change color when driver aids activate:
- **Throttle**: Green normally → Yellow when TC active
- **Brake**: Red normally → Orange when ABS active

Handle by combining color masks:
```python
mask_green = cv2.inRange(hsv, lower_green, upper_green)
mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
combined_mask = cv2.bitwise_or(mask_green, mask_yellow)
```

### Steering Detection
Uses brightness thresholding to find white indicator dot:

1. Convert to grayscale
2. Threshold at high value (200) to isolate bright pixels
3. Find contours
4. Get largest contour (the steering dot)
5. Calculate centroid position
6. Normalize to -1.0 (left) to +1.0 (right)

### Common Pitfalls

#### Red Color Detection
Red wraps around in HSV (0° and 180° are both red). Must detect in **two ranges**:
- Lower red: H: 0-10
- Upper red: H: 170-180

```python
lower_red1 = np.array([0, 100, 100])    # Lower red
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 100, 100])  # Upper red
upper_red2 = np.array([180, 255, 255])
mask = cv2.bitwise_or(mask_red1, mask_red2)
```

#### Edge Artifacts
ROI edges may have anti-aliasing or compression artifacts. Always sample middle portions:
```python
middle_rows = mask[height//3:2*height//3, :]
```

#### Outlier Handling
Use median instead of mean for robustness:
```python
filled_width = np.median(filled_widths)
```

### OCR Strategy

The project uses **tesserocr** (fast C++ API) for extracting lap numbers and lap times from the HUD.

#### Why tesserocr over pytesseract?
- **Performance**: tesserocr is 25x faster (~2ms vs ~50ms per frame)
- **Direct API**: Uses Tesseract C++ API directly, no subprocess overhead
- **Same accuracy**: Both use same Tesseract engine, just different Python bindings

#### Minimal Preprocessing Approach
We found that **raw images work best** with tesserocr. No preprocessing overhead needed!

```python
# Extract ROI
roi = frame[y:y+height, x:x+width]

# Direct OCR on raw image - works great!
pil_image = Image.fromarray(roi)
tesserocr_api.SetImage(pil_image)
text = tesserocr_api.GetUTF8Text()
```

**Key insight**: Modern Tesseract LSTM models handle raw images better than preprocessed ones.
- Don't: Apply thresholding, morphology, or complex preprocessing
- Do: Extract tight ROI and feed directly to tesserocr
- Do: Use proper PSM (Page Segmentation Mode) for your text type

#### Tesseract Configuration
Configure tesserocr with appropriate PSM for your use case:

```python
# For isolated lap numbers (single digits like "21")
api = tesserocr.PyTessBaseAPI(
    psm=tesserocr.PSM.SINGLE_WORD,      # PSM 8: Single word
    oem=tesserocr.OEM.LSTM_ONLY         # OEM 3: LSTM neural network
)
api.SetVariable("tessedit_char_whitelist", "0123456789")

# For lap times (format: "01:44.643")
api = tesserocr.PyTessBaseAPI(
    psm=tesserocr.PSM.SINGLE_LINE,      # PSM 7: Single line of text
    oem=tesserocr.OEM.LSTM_ONLY
)
api.SetVariable("tessedit_char_whitelist", "0123456789:.")
```

**PSM modes reference**:
- PSM 8 (`SINGLE_WORD`): Best for isolated numbers (lap count)
- PSM 7 (`SINGLE_LINE`): Best for single line text (lap times)
- PSM 6 (`SINGLE_BLOCK`): Default, but slower for small ROIs

**Character whitelisting**: Always limit to expected characters for better accuracy

#### Installation Notes
```bash
# Install tesserocr (requires Tesseract to be installed first)
brew install tesseract  # macOS
pip install tesserocr

# Verify tesseract installation
tesseract --version

# Common tessdata path on macOS (homebrew)
/opt/homebrew/share/tessdata/
```

### Template Matching (historical)
Lap numbers previously used template matching. `extract_lap_number()` now runs **tesserocr** (pytesseract fallback). `src/template_matcher.py` is unused on that path. See [docs/TEMPLATE_MATCHING_GUIDE.md](docs/TEMPLATE_MATCHING_GUIDE.md).

### Kalman Filtering for Position Tracking
Position tracking includes outlier rejection:
- 1D Kalman filter tracks `[position, velocity]`
- Rejects measurements with >10% innovation (likely detection errors)
- Prevents false spikes in lap comparison graphs
- Enabled by default in [PositionTrackerV2](src/position_tracker_v2.py:33)

### Temporal Smoothing
OCR results smoothed using majority voting:
```python
# Track last 5 detections
lap_number_history = [20, 21, 20, 21, 21]

# Count occurrences
from collections import Counter
lap_counts = Counter(lap_number_history)
most_common = lap_counts.most_common(1)[0]  # (21, 3)

# Use if at least 40% agreement (2/5 frames)
if most_common[1] >= max(2, len(history) * 0.4):
    smoothed_lap = most_common[0]
```

This prevents flip-flopping between adjacent numbers (e.g., 20 ↔ 21) due to OCR noise.

## Data Formats and Telemetry Structure

### Telemetry Data Structure

#### Internal Format (Python Dictionary)
During processing, each frame produces:
```python
{
    'frame': 733,           # Frame number (0-indexed)
    'time': 24.49,          # Timestamp in seconds
    'throttle': 67.8,       # Throttle percentage (0.0 - 100.0)
    'brake': 0.0,           # Brake percentage (0.0 - 100.0)
    'steering': 0.45,       # Steering position (-1.0 to +1.0)
    'speed': 142,           # Speed in km/h
    'gear': 4,              # Current gear (1-6)
    'lap': 3,               # Current lap number
    'position': 47.5        # Track position percentage (0-100)
}
```

#### Value Ranges
- **frame**: Integer, 0 to (frame_count - 1)
- **time**: Float, seconds from video start
- **throttle**: Float, 0.0% (no throttle) to 100.0% (full throttle)
- **brake**: Float, 0.0% (no brake) to 100.0% (full brake)
- **steering**: Float, -1.0 (full left) to +1.0 (full right), 0.0 is center
- **speed**: Integer, km/h
- **gear**: Integer, 1-6
- **lap**: Integer, current lap number
- **position**: Float, 0-100% track position

### CSV Output Format

Generated in `data/output/telemetry_YYYYMMDD_HHMMSS.csv`:

```csv
frame,time,throttle,brake,steering,speed,gear,lap,position
0,0.00,0.0,0.0,0.02,45,2,1,5.2
1,0.03,15.4,0.0,0.03,48,2,1,5.8
2,0.07,34.8,0.0,0.05,52,3,1,6.4
```

#### CSV Specifications
- **Header row**: Required (includes all telemetry channels)
- **Delimiter**: Comma
- **Decimal separator**: Period (.)
- **Encoding**: UTF-8
- **Line endings**: Platform default (LF on Unix, CRLF on Windows)
- **Precision**: Floats rounded to 1-2 decimal places

#### Usage Examples
- Open in Excel/Google Sheets for manual analysis
- Import into data analysis tools (Python pandas, R, MATLAB)
- Use with racing telemetry software (MoTeC, RaceStudio, etc.)
- Sync with video using frame numbers or timestamps

### Interactive HTML Visualizations

Generated by InteractiveTelemetryVisualizer in `data/output/telemetry_interactive_YYYYMMDD_HHMMSS.html`:

- Browser-based Plotly graphs with zoom, pan, hover tooltips
- Multi-lap overlay with dropdown selector
- Synchronized plots showing:
  - Throttle (0-100%)
  - Brake (0-100%)
  - Steering (-1.0 to +1.0)
  - Speed (km/h)
  - Track position (0-100%)
- Interactive features: click to isolate traces, double-click to reset

### Lap Comparison Output

Generated in `data/output/lap_comparison_position_YYYYMMDD_HHMMSS.html`:

- Position-based comparison (gold standard - shows where time is gained/lost)
- Aligns laps by track position instead of time
- Reveals braking points, corner entry/exit differences
- Color-coded lap traces

### File Naming Convention
All output files use timestamp-based naming:
- **Pattern**: `telemetry_YYYYMMDD_HHMMSS.{csv,html}`
- **Example**: `telemetry_20251021_235757.csv`
- **Purpose**: Prevents overwriting previous analyses

### Data Interpretation Tips

#### Normal Driving Patterns
- **Straight**: High throttle, low brake, steering near 0.0
- **Braking zone**: Decreasing throttle, increasing brake, steering transitions
- **Apex**: Low/no throttle, no brake, maximum steering input
- **Exit**: Increasing throttle, no brake, steering returns to center

#### Identifying Driving Issues
- **Simultaneous throttle + brake**: Trail braking (normal) or input error
- **Rapid steering oscillations**: Oversteer correction or instability
- **Low peak throttle values**: Conservative driving or traction control intervention
- **Extended brake applications**: Late braking or poor corner entry

#### TC/ABS Detection
Color changes in video aren't directly captured in telemetry data, but you can infer:
- **TC intervention**: Throttle drops despite input (or plateaus below 100%)
- **ABS intervention**: Brake percentage fluctuates rapidly

## Python Coding Conventions

### Code Style
- Follow PEP 8 conventions
- Use type hints for function parameters and return values (typing module)
- Add comprehensive docstrings for all classes and methods (Google style)
- Keep functions focused and single-purpose

### Naming Conventions
- Classes: PascalCase (e.g., `TelemetryExtractor`, `VideoProcessor`)
- Functions/methods: snake_case (e.g., `extract_bar_percentage`, `process_frames`)
- Constants: UPPER_SNAKE_CASE (e.g., `VIDEO_PATH`, `CONFIG_PATH`)
- Private methods: prefix with underscore (e.g., `_internal_method`)

### Error Handling
- Check for None/empty arrays before processing images
- Validate video file existence before processing
- Use try-finally blocks for resource cleanup (video capture release)
- Return sensible defaults (0.0) when detection fails rather than crashing

### Computer Vision Patterns
- Always convert BGR to HSV for color detection (OpenCV uses BGR by default)
- Use `cv2.inRange()` for color masking
- Combine multiple color masks with `cv2.bitwise_or()` for multi-color detection
- Sample middle portions of ROIs to avoid edge artifacts
- Use median instead of mean to handle outliers in bar detection
- Clamp values to valid ranges (0-100 for percentages, -1 to +1 for steering)

### Resource Management
- Always call `VideoProcessor.close()` to release video capture
- Use context managers or try-finally for cleanup
- Create output directories with `mkdir(parents=True, exist_ok=True)`

### Performance Considerations
- Use generator pattern for frame processing to avoid loading entire video into memory
- Process frames sequentially (current design optimized for accuracy over speed)
- Consider progress indicators for long-running operations

### Testing Approach
- Validate ROI extraction by checking image dimensions
- Test color detection with sample frames from different lighting conditions
- Verify telemetry values are within expected ranges (0-100%, -1 to +1)
- Test with different video resolutions

## Common Development Tasks

### Debugging Incorrect Telemetry Values

**Debug Steps:**
1. Write a script in the `/debug` folder
2. **Extract and inspect ROI images**:
   ```python
   cv2.imwrite(f'debug_throttle_frame{frame_num}.png', roi_dict['throttle'])
   ```

3. **Save color masks**:
   ```python
   cv2.imwrite(f'debug_mask_frame{frame_num}.png', mask)
   ```

4. **Print color statistics**:
   ```python
   print(f"ROI shape: {roi_image.shape}")
   print(f"Min HSV: {hsv.min(axis=(0,1))}")
   print(f"Max HSV: {hsv.max(axis=(0,1))}")
   ```

5. **Verify ROI coordinates visually**:
   ```python
   cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
   cv2.imwrite('debug_frame_with_roi.png', frame)
   ```

### Tuning HSV Color Ranges
Edit ranges in [src/telemetry_extractor.py](src/telemetry_extractor.py):
```python
# Make green detection more permissive
lower_green = np.array([30, 40, 40])  # Lower saturation threshold
upper_green = np.array([90, 255, 255])  # Wider hue range
```

Save intermediate masks for debugging:
```python
cv2.imwrite('debug_mask.png', mask)
```

### Calibrating for Different Video Resolutions

#### Extract Test Frame
```bash
mkdir -p debug videos
python -c "import cv2; cap=cv2.VideoCapture('videos/your_video.mp4'); _,f=cap.read(); cv2.imwrite('debug/frame.png',f); cap.release()"
```

This saves a frame to `debug/frame.png` for inspecting ROI positions.

#### Verify ROI Coordinates
1. Open extracted frame in image viewer
2. Identify throttle/brake/steering UI elements
3. Note pixel coordinates
4. Update a profile in [config/roi_config.yaml](config/roi_config.yaml)
5. Re-run `python main.py` and select that profile

#### Quick Test on Short Clip
For faster iteration, test on a short video clip:
```bash
# Extract 10-second clip using ffmpeg into videos/
ffmpeg -i videos/full_lap.mp4 -t 10 videos/test_clip.mp4
python main.py  # select test_clip.mp4 when prompted
```

### Adding New Telemetry Channel
1. Add ROI coordinates to [config/roi_config.yaml](config/roi_config.yaml)
2. Update `VideoProcessor.extract_roi()` to include new ROI
3. Add extraction method in [src/telemetry_extractor.py](src/telemetry_extractor.py)
4. Update `extract_frame_telemetry()` to call new method
5. Modify [src/interactive_visualizer.py](src/interactive_visualizer.py) to plot new channel

### Adding Progress Visualization
Current implementation prints progress every 10%. To show every frame:
```python
print(f"Frame {frame_num}/{video_info['frame_count']}", end='\r')
```

### Optimizing Performance
- **Sample fewer frames**: Process every Nth frame
  ```python
  if frame_num % 2 == 0:  # Process every other frame
      # ... extraction logic
  ```
- **Reduce resolution**: Resize frame before processing (may affect accuracy)
- **Parallel processing**: Use multiprocessing for frame batches (complex)

### Video Processing Errors

**Common Causes:**
- Video codec not supported by OpenCV → Re-encode with H.264
- Corrupted video file → Verify with VLC or other player
- Incorrect video path → Ensure the file is under `videos/` and selected correctly

**Test Video Opening:**
```python
cap = cv2.VideoCapture('videos/your_video.mp4')
print(f"Video opened: {cap.isOpened()}")
print(f"Frame count: {cap.get(cv2.CAP_PROP_FRAME_COUNT)}")
cap.release()
```

## Performance Benchmarks

### Per-Frame Processing Times
- **Throttle/Brake detection** (HSV color masking): ~0.5ms per bar
- **Steering detection** (contour finding): ~1ms
- **Lap number OCR** (tesserocr): ~2ms per frame
- **Speed/Gear OCR** (tesserocr): ~2ms per frame
- **Lap time OCR** (pytesseract fallback): ~50ms per transition (only when lap changes)
- **Position tracking**: ~1-2ms per frame
- **Total per-frame processing**: ~5-10ms (can process 100-200 FPS)

### Bottlenecks
1. **Video I/O**: Reading frames from disk (OpenCV handles efficiently)
2. **OCR**: Lap time extraction (~50ms) - only runs at lap transitions
3. **Visualization**: Plotly graph generation (~2-5s) - only at end

### Optimization Notes
- tesserocr (~2ms) is the current lap-number path; template matching is unused leftover
- Kalman filter adds <1ms overhead per frame
- Multi-frame track path extraction runs once at startup (not per-frame)
- Use generator pattern for frame processing to avoid loading entire video into memory
- Process frames sequentially (current design optimized for accuracy over speed)

## Important Notes

### ROI Extraction Strategy
- Keep ROIs **tight around UI elements** with 1-3px margin
- Sample **middle portions** of bars to avoid edge artifacts
- Use **median** instead of mean for robustness against outliers

### Position Tracking
- Requires `track_map` ROI in config
- Extracts white racing line from multiple frames (avoids red dot occlusion)
- Samples frames: [0, 50, 100, 150, 200, 250, 500, 750, 1000, 1250, 1500]
- Resets Kalman filter on lap transitions for accuracy

### Debugging Tips
1. Save intermediate images (ROI crops, masks) for visual inspection
2. Print min/max color values in ROI to tune HSV ranges
3. Test with frames where TC/ABS are active vs. inactive
4. Verify ROI coordinates by overlaying rectangles on original frame
5. Check that masks have expected white regions (use cv2.imshow in debug mode)
6. For OCR debugging: save ROI images and test with `tesseract` CLI directly
7. Check tesserocr timing: should be ~1-2ms per frame (vs 50ms for pytesseract)

## Testing and Validation

### Quick Test Workflow
```bash
# Extract 10-second clip for fast iteration
ffmpeg -i videos/full_lap.mp4 -t 10 videos/test_clip.mp4

# Select test_clip.mp4 when main.py prompts
python main.py
```

### Verification Checklist
- [ ] All telemetry values in expected ranges (0-100%, -1.0 to +1.0)
- [ ] No sustained 0% or 100% values (indicates ROI misconfiguration)
- [ ] Lap transitions detected correctly
- [ ] Position tracking shows smooth progression (0% → 100%)
- [ ] TC/ABS activation correlates with visible HUD color changes

## Known Limitations

1. **Resolution-dependent**: ROI coordinates must be recalibrated for different video resolutions
2. **HUD-dependent**: Requires default ACC HUD to be visible (custom HUDs unsupported)
3. **Post-processing only**: Not real-time (but console players record first anyway)
4. **Console-focused**: PC players have native telemetry export options
