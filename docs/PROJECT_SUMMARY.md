# ACC Telemetry Extractor - Project Summary

## What We Built

We created a **Python tool that watches your ACC racing videos and automatically extracts telemetry data** (throttle, brake, steering) by "reading" the on-screen UI elements using computer vision. Think of it as a robot watching your gameplay and recording what the dashboard shows.

---

## How It Works (Simple Explanation)

### 1. **The Problem**
Your PS5/console doesn't let you export telemetry data from ACC like PC players can. But the game SHOWS this data on screen - those little bars in the bottom-right corner.

### 2. **The Solution**
We use **computer vision** (teaching computers to "see" images) to read those bars automatically:

```
Your Video → Computer reads it frame-by-frame → Extracts data → Creates graphs & CSV
```

### 3. **The Technical Steps**

#### **Step 1: Finding the Right Spots (ROI - Region of Interest)**
- We tell the computer exactly WHERE to look on screen
- Like saying "look at the bottom-right corner, coordinates x=1170, y=670"
- These are the **throttle and brake bars** in your video

#### **Step 2: Color Detection**
- The computer looks at each frame and asks: "How much GREEN do I see in the throttle bar?"
- Green bar 50% filled = 50% throttle
- It also handles color changes:
  - **Throttle**: Green normally, turns yellow when Traction Control activates
  - **Brake**: Red/orange normally, turns yellow when ABS activates

#### **Step 3: Measuring the Bars**
- For horizontal bars (like yours), it scans left-to-right
- Counts how many pixels are colored vs. empty
- Math: `(filled pixels / total bar width) × 100 = percentage`

#### **Step 4: Steering Detection**
- Looks for the brightest white spot in the steering indicator area
- Calculates its position: left side = -1.0, center = 0.0, right side = +1.0

---

## What We Struggled With (The Journey)

### **Challenge 1: Wrong Video Resolution**
- I initially set coordinates for 1920×1080 (Full HD)
- Your video was 1280×720 (720p)
- **Solution**: Extracted a sample frame to see actual resolution

### **Challenge 2: Found the Wrong Bars**
- First found the **tire pressure bars** (vertical green bars on left side)
- Those weren't throttle/brake - they show tire data!
- **Solution**: You corrected me - the real bars are horizontal in bottom-right

### **Challenge 3: Color Changes**
- Bars change color when ABS/TC activate (green→yellow, red→yellow)
- Initial code only looked for green, so it missed activated states
- **Solution**: Added detection for multiple colors (green + yellow + orange)

### **Challenge 4: Vertical vs. Horizontal**
- I initially thought bars were vertical (fill bottom-to-top)
- Your bars are horizontal (fill left-to-right)
- **Solution**: Added support for both orientations in the code

---

## Current State of the Solution

### ✅ **What's Working**

1. **Throttle Detection**
   - Reads the green/yellow horizontal bar
   - Handles Traction Control color changes
   - Outputs 0-100% values

2. **Brake Detection**
   - Reads the red/orange horizontal bar
   - Handles ABS color changes
   - Outputs 0-100% values

3. **Steering Detection**
   - Tracks steering inputs
   - Outputs -1.0 (full left) to +1.0 (full right)

4. **Data Export**
   - CSV file with frame-by-frame data
   - Beautiful 3-panel graph showing all telemetry
   - Timestamped files for tracking multiple sessions

### 📊 **Your Output Files**

Located in `data/output/`:
- **CSV**: Raw data you can open in Excel/Google Sheets
- **PNG Graph**: Visual representation of your driving

---

## The Technology Stack (What We Used)

### **Libraries Explained**

1. **OpenCV** (`opencv-python`)
   - The "eyes" of the program
   - Reads video files frame-by-frame
   - Converts colors (BGR → HSV for better color detection)

2. **NumPy**
   - Math library for processing image data
   - Images are just arrays of numbers to computers

3. **Pandas**
   - Organizes data into tables (like Excel)
   - Makes CSV export easy

4. **Matplotlib**
   - Creates the pretty graphs
   - Plots throttle, brake, steering over time

5. **PyYAML**
   - Reads the configuration file
   - So you can adjust ROI coordinates without changing code

---

## Key Concepts for Beginners

### **1. ROI (Region of Interest)**
The specific pixel coordinates where we look for data:
```yaml
throttle:
  x: 1170      # Start 1170 pixels from left edge
  y: 670       # Start 670 pixels from top
  width: 103   # Look at 103 pixels wide
  height: 14   # Look at 14 pixels tall
```

Think of it as drawing a small rectangle on your screen saying "only look here."

### **2. HSV Color Space**
- **BGR**: How cameras see color (Blue, Green, Red)
- **HSV**: How humans think about color (Hue, Saturation, Value)
  - **Hue**: The actual color (0-180 in OpenCV)
  - **Saturation**: How "pure" the color is (0-255)
  - **Value**: How bright it is (0-255)

HSV is better for detecting "any shade of green" regardless of brightness.

**Example color ranges in our code:**
```python
# Green (throttle bar)
lower_green = [35, 50, 50]   # Dark green
upper_green = [85, 255, 255] # Bright green

# Yellow (when TC/ABS active)
lower_yellow = [15, 100, 100]
upper_yellow = [35, 255, 255]
```

### **3. Mask Creation**
A mask is a black and white image that shows "where the color is":
- **White pixels** (255) = color match found here
- **Black pixels** (0) = no match

Example:
```
Original bar:  [====GREEN====        ]
Mask result:   [WWWWWWWWWW............]  (W=white, .=black)
```

Then we count: 10 white pixels out of 20 total = 50% throttle

### **4. Frame-by-Frame Processing**
Video isn't continuous - it's a series of still images:
- Your video: ~30 FPS = 30 images per second
- 49 second video = 1,467 individual images
- We analyze each image one at a time

### **5. Pixel Coordinates**
Computer screens use X,Y coordinates:
```
(0,0) -------- X increases →
 |
 |
 Y increases ↓
 
For 1280x720 video:
- Top-left corner: (0, 0)
- Top-right corner: (1280, 0)
- Bottom-left corner: (0, 720)
- Bottom-right corner: (1280, 720)
```

Your throttle bar at (1170, 670) is near the bottom-right corner.

---

## How to Use It

```bash
# 1. Activate the Python environment
source venv/bin/activate

# 2. Place your ACC video in videos/
mkdir -p videos
cp /path/to/acc_video.mp4 videos/

# 3. Run the extractor (select video + ROI profile)
python main.py

# 4. Check data/output/ for results
```

### Output Files:
- `telemetry_YYYYMMDD_HHMMSS.csv` - Raw data
- `telemetry_interactive_YYYYMMDD_HHMMSS.html` - Interactive Plotly graph

---

## The Code Structure

```
acc-telemetry/
├── src/
│   ├── video_processor.py           # Opens video, extracts ROI regions
│   ├── telemetry_extractor.py       # Analyzes colors, measures bars
│   ├── lap_detector.py              # Lap / speed / gear detection
│   ├── position_tracker_v2.py       # Minimap position tracking
│   ├── interactive_visualizer.py    # CSV + interactive HTML
│   └── web/                         # Optional FastAPI backend
├── config/
│   └── roi_config.yaml              # Named ROI profiles
├── videos/                          # Input .mp4 files
├── data/
│   └── output/                      # Results
├── main.py                          # CLI entrypoint
├── run_server.py                    # Web API entrypoint
├── requirements.txt
└── README.md
```

### What Each File Does:

**video_processor.py**
- Opens the video file
- Reads it frame-by-frame
- Cuts out the small ROI rectangles
- Passes them to the extractor

**telemetry_extractor.py**
- Takes ROI images
- Converts colors to HSV
- Creates masks to find green/red pixels
- Counts pixels to calculate percentages
- Returns throttle/brake/steering values

**interactive_visualizer.py**
- Takes all the telemetry data
- Creates a pandas DataFrame (table)
- Generates interactive Plotly HTML graphs
- Exports CSV file

**main.py**
- Orchestrates everything
- Shows progress (0%...10%...20%...)
- Displays summary statistics

---

## Limitations & Future Improvements

### **Current Limitations**
1. ✅ Calibrated for your video resolution (1280×720)
2. ✅ ROI coordinates need manual adjustment for different videos
3. ⚠️ Assumes bars are always visible (won't work if HUD is hidden)
4. ⚠️ Only works with that specific HUD layout
5. ⚠️ Steering detection might not be perfectly accurate

### **Possible Future Features**
- **Auto-detect ROI positions** (template matching)
- **Support multiple resolutions** automatically
- **Lap time detection** and lap splitting
- **Compare multiple laps** side-by-side
- **Export to professional formats** (MoTeC i2)
- **Analyze YouTube videos** from other drivers
- **Web UI** for drag-and-drop video upload
- **Real-time preview** of what ROIs are detecting

---

## Technical Concepts Explained

### **How Color Detection Works**

1. **Convert to HSV**
   ```python
   hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
   ```
   Changes color representation to make detection easier.

2. **Create Color Range**
   ```python
   lower_green = [35, 50, 50]
   upper_green = [85, 255, 255]
   ```
   Defines "what counts as green."

3. **Make Mask**
   ```python
   mask = cv2.inRange(hsv, lower_green, upper_green)
   ```
   Creates black/white image showing where green is.

4. **Count Pixels**
   ```python
   filled_pixels = np.count_nonzero(mask)
   percentage = (filled_pixels / total_pixels) * 100
   ```

### **Why Multiple Color Ranges?**

The bars change color during ABS/TC activation:
- **Throttle bar**: Green → Yellow (when TC intervenes)
- **Brake bar**: Red → Orange/Yellow (when ABS intervenes)

We need to detect both states, so we:
1. Create mask for normal color (green/red)
2. Create mask for activated color (yellow/orange)
3. Combine masks with `bitwise_or` (logical OR)
4. Now we detect the bar regardless of ABS/TC state

---

## Troubleshooting Guide

### Problem: "All values are 0% or 100%"
**Cause**: ROI coordinates are wrong

**Solution**: 
1. Edit `config/roi_config.yaml`
2. Adjust x, y, width, height values
3. Run again

### Problem: "Video file not found"
**Cause**: No `.mp4` files in `videos/`, or the path you selected is wrong

**Solution**:
- Place your video under `videos/` and re-run `python main.py`
- Select the correct file when prompted

### Problem: "Processing is very slow"
**Cause**: Normal - video processing is CPU-intensive

**Expected speeds**:
- ~30-60 frames per second on modern CPU
- 1 minute of video = 1-2 minutes processing time

### Problem: "Incorrect brake/throttle values"
**Possible causes**:
1. Different video resolution - need to recalibrate ROI
2. Different HUD layout - bars might be elsewhere
3. Color detection not tuned for your lighting

**Solution**: Check `roi_config.yaml` coordinates match your video

---

## Example: Understanding the Output

### CSV Data:
```csv
frame,time,throttle,brake,steering
733,24.49,67.8,0.0,0.45
734,24.52,45.2,31.5,-0.23
735,24.56,0.0,89.7,-0.78
```

**Reading this:**
- Frame 733 (24.49 seconds): 67.8% throttle, no brake, slight right turn
- Frame 734 (24.52 seconds): Lifting throttle, starting to brake, turning left
- Frame 735 (24.56 seconds): No throttle, heavy braking, turning harder left

This is typical corner entry behavior!

---

## The Bottom Line

You now have a working tool that turns your console racing videos into professional telemetry data. The computer "watches" your gameplay footage and records what the dashboard shows, just like you would manually - but automatically for every single frame!

The telemetry graph you generated shows realistic racing behavior:
- Full throttle on straights
- Braking zones before corners
- Steering inputs through turns
- Proper correlation between throttle/brake/steering

**This is production-ready for analyzing your own racing footage!** 🏁

---

## Learning Resources

If you want to learn more about the technologies used:

### Computer Vision Basics:
- [OpenCV Python Tutorial](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- Understanding HSV color space
- Image masking and thresholding

### Python Libraries:
- [NumPy basics](https://numpy.org/doc/stable/user/quickstart.html) - Array operations
- [Pandas basics](https://pandas.pydata.org/docs/getting_started/intro_tutorials/) - Data manipulation
- [Matplotlib basics](https://matplotlib.org/stable/tutorials/introductory/pyplot.html) - Plotting

### Next Projects:
- Add OCR (text recognition) to read lap times
- Try object detection to find UI elements automatically
- Machine learning to classify driving styles

