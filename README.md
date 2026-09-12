---
title: ACC Telemetry Extractor
emoji: 🏎️
colorFrom: red
colorTo: gray
sdk: docker
pinned: false
app_port: 7860
---

# ACC Telemetry Extractor (Console Edition)

Extract detailed telemetry data from Assetto Corsa Competizione gameplay videos using computer vision. Designed for **console players (PS5/Xbox)** who can't access native telemetry export.

## 🎯 What It Does

This tool analyzes ACC gameplay videos frame-by-frame to extract:
- **Throttle input** (0-100%)
- **Brake input** (0-100%)
- **Steering input** (-1.0 to +1.0)
- **Speed** (km/h via OCR)
- **Gear** (1-6 via OCR)
- **Lap numbers** (via template matching)
- **Track position** (0-100% via minimap analysis) 🆕

And generates:
- CSV data files for analysis
- **Interactive HTML visualizations** with zoom, pan, and hover tooltips
- **Position-based lap comparison** - see exactly where you gain/lose time 🆕
- Multi-lap overlays via the visualizer API
- Lap statistics

## 🚀 Quick Start

```bash
# 1. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Place your gameplay video in videos/
mkdir -p videos
cp /path/to/your/acc_video.mp4 videos/

# 3. Extract telemetry (interactive video + ROI profile selection)
python main.py
```

`main.py` prompts you to pick a video from `videos/` and an ROI profile from `config/roi_config.yaml`, then writes CSV + interactive HTML to `data/output/`.

### Optional: Web API

```bash
python run_server.py
# API docs: http://localhost:8000/docs
```

### Optional: Position-based lap comparison

After extraction, generate a position-aligned comparison from the CSV:

```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

## 📊 Output Examples

### Interactive Visualization (NEW!)
**Browser-based interactive graphs with Plotly** - [See full guide](docs/INTERACTIVE_VISUALIZATION_GUIDE.md)

Features:
- 🔍 **Interactive zoom**: Click and drag to zoom into any region
- 🖱️ **Pan navigation**: Explore your lap in detail
- 📊 **Hover tooltips**: See exact values at any point
- 📈 **Synchronized views**: All plots zoom together
- 🏁 **Lap comparison**: Overlay multiple laps to compare performance
- 💾 **Export controls**: Download as high-res PNG
- 🌐 **Shareable**: Just send the HTML file - works in any browser

**Output**: `telemetry_interactive_YYYYMMDD_HHMMSS.html` (open in browser)

---

### Position-Based Lap Comparison (NEW! 🆕)
**Gold standard for racing analysis** - [See full guide](docs/POSITION_BASED_LAP_COMPARISON.md)

Compare laps by **track position** instead of time to see exactly where you gain or lose time around the track!

Features:
- 🎯 **Position alignment**: Compare inputs at the same corners (not same time)
- 📉 **Time delta plot**: Shows exactly where time is gained/lost
- 🔽 **Dropdown selector**: Switch between lap comparisons instantly
- 🗺️ **Track position axis**: 0% = start/finish, 50% = halfway around
- 📊 **5 synchronized plots**: Throttle, Brake, Steering, Speed, Time Delta

**Why it's better than time-based comparison:**
- See EXACTLY which corner is costing you time
- Compare braking points at the same position
- Identify problem sections immediately
- Direct comparison of driving technique

**Usage**:
```python
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer

viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
```

**Output**: `lap_comparison_position_YYYYMMDD_HHMMSS.html` (open in browser)

## 📁 Project Structure

```
acc-telemetry/
├── main.py                           # CLI telemetry extraction
├── run_server.py                     # FastAPI web backend entrypoint
├── config/
│   └── roi_config.yaml              # Named ROI profiles (resolution-specific)
├── src/
│   ├── video_processor.py           # Video frame extraction
│   ├── telemetry_extractor.py       # Computer vision analysis
│   ├── lap_detector.py              # Lap number / speed / gear detection
│   ├── position_tracker_v2.py       # Track position tracking (minimap) 🆕
│   ├── template_matcher.py          # Digit template matching
│   ├── interactive_visualizer.py    # Interactive Plotly visualizations
│   └── web/                         # FastAPI backend (jobs, videos, telemetry)
├── tests/
│   ├── test_position_smoothing.py
│   └── test_position_tracker_v2.py
├── videos/                          # Place input .mp4 files here
├── data/
│   └── output/                      # Generated CSV and HTML files
└── docs/                            # Guides and technical docs
```

## 🎮 Supported Setup

Currently configured via named profiles in `config/roi_config.yaml` (e.g. PS5 1080p). ROI coordinates are resolution- and HUD-dependent.

**Other resolutions?** Recalibrate ROI coordinates (see [USER_GUIDE.md](docs/USER_GUIDE.md) Resolution Configuration).

### 🔧 Calibrating ROIs

1. Extract a test frame:
   ```bash
   python -c "import cv2; cap=cv2.VideoCapture('videos/your_video.mp4'); _,f=cap.read(); cv2.imwrite('debug/frame.png',f); cap.release()"
   ```
2. Open `debug/frame.png` in an image viewer that shows pixel coordinates
3. Measure HUD element positions and update a profile in `config/roi_config.yaml`

## 📖 Documentation

### User Guides
- **[USER_GUIDE.md](docs/USER_GUIDE.md)** - Complete usage guide ⭐ START HERE
- **[POSITION_BASED_LAP_COMPARISON.md](docs/POSITION_BASED_LAP_COMPARISON.md)** - Position-based lap comparison (where you gain/lose time) 🆕
- **[INTERACTIVE_VISUALIZATION_GUIDE.md](docs/INTERACTIVE_VISUALIZATION_GUIDE.md)** - Interactive HTML graphs and lap comparison
- **[QUICKSTART_WEB.md](QUICKSTART_WEB.md)** - Web API quick start

### Technical Guides
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design
- **[TRACK_POSITION_TRACKING.md](docs/TRACK_POSITION_TRACKING.md)** - How minimap-based position tracking works 🆕
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues
- **[docs/README.md](docs/README.md)** - Full documentation index

## 🛠️ Technical Stack

- **Python 3.10+**
- **OpenCV** - Video processing and computer vision
- **NumPy / Pandas** - Array ops and CSV export
- **Plotly** - Interactive HTML visualizations
- **PyYAML** - Configuration
- **tesserocr / pytesseract** - OCR for speed, gear, lap times
- **FastAPI** - Optional web API (`src/web/`)

## 💡 How It Works

1. **Video Processing**: Extract frames from gameplay video
2. **ROI Extraction**: Crop HUD regions (throttle, brake, steering, minimap, etc.)
3. **Color Detection**: HSV masks for bar colors and steering indicator
4. **OCR / Templates**: Read speed, gear, and lap numbers
5. **Position Tracking**: Follow the red dot on the minimap racing line
6. **Export**: CSV + interactive HTML

## 🎯 Use Cases

### Personal Improvement
- Compare your laps to find where you're losing time
- Analyze braking points consistency
- Study throttle application technique
- Identify problem corners

### Lap Comparison
- **Position-based**: See exactly where you gain/lose time around the track 🆕
- **Time-based**: Compare overall lap progression
- Track improvement over practice sessions
- Find which corners have the most variation
- Identify your weakest sections

### Learn from Others
- Download fast laps from YouTube
- Extract their telemetry
- Compare your technique to theirs
- Identify specific differences in inputs

## 🔬 Key Features

### Multi-Color Detection
- Handles TC/ABS activation color changes
- Throttle: Green → Yellow when TC active
- Brake: Red → Orange when ABS active

### Interactive Output
- Browser-based Plotly graphs with zoom/pan/hover
- Suitable for sharing and detailed analysis
- Frame-by-frame accuracy

### Comprehensive Statistics
- Lap duration and frame count
- Average and max values for all inputs
- Full throttle percentage and time
- Braking event count and duration
- Steering angle statistics

## 🐛 Known Limitations

1. **Resolution-dependent**: ROI coordinates need recalibration for different video resolutions
2. **HUD-dependent**: Requires default ACC HUD to be visible
3. **Console-focused**: Designed for console gameplay footage (PC players have native telemetry export)
4. **Post-processing only**: Not real-time (but console players record first, analyze later anyway)

## 🚧 Roadmap

### Enhanced Features
- [ ] Automatic ROI detection (no manual calibration needed)
- [ ] Batch processing multiple videos
- [ ] Resolution-independent ROI scaling

### Advanced Analysis
- [x] Multi-lap overlay comparison (✅ COMPLETE)
- [x] Interactive zoom/pan visualization (✅ COMPLETE - Plotly integration)
- [x] Track position tracking (✅ COMPLETE - minimap analysis)
- [x] Position-based lap comparison (✅ COMPLETE) 🆕
- [x] Time delta analysis (✅ COMPLETE - integrated in position comparison) 🆕
- [ ] Track map overlay visualization
- [ ] Sector-by-sector analysis with automatic sector detection
- [ ] AI-powered driving feedback

### Community Platform
- [x] Web API for processing and telemetry (✅ COMPLETE)
- [ ] Full web UI for video upload
- [ ] Cloud processing
- [ ] Shared telemetry database
- [ ] YouTube integration

## 🤝 Contributing

This is a learning project, but contributions are welcome! Areas where help would be appreciated:
- Support for more video resolutions
- Automatic ROI detection algorithms
- OCR integration for lap times
- Additional visualization types
- Performance optimization

## 📄 License

MIT License - Feel free to use, modify, and share!

## 🙏 Acknowledgments

Built by a console sim racer frustrated by the lack of telemetry tools. Inspired by professional telemetry software like MoTeC i2 and RaceStudio, but adapted for the constraint of console gaming: **if you can see it on screen, we can extract it**.

## 📬 Questions?

Check the documentation:
- **User guide**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- **Technical details**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Full index**: [docs/README.md](docs/README.md)

---

**Happy racing! 🏁**

*Remember: The fastest drivers aren't necessarily the most talented - they're the ones who analyze and improve systematically.*
