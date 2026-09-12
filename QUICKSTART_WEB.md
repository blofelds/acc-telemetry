# Quick Start Guide - Web Application

This guide helps you run the ACC Telemetry Extractor **web API** (FastAPI backend).

> **Note:** The optional React frontend (`frontend/`) is not currently in this repository. You can use the API directly via Swagger UI or any HTTP client. CLI extraction via `python main.py` remains the primary workflow.

## Prerequisites

- Python 3.8+ with virtual environment
- Dependencies from [requirements.txt](requirements.txt)

## Start the Backend

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Start backend API
python run_server.py
```

The backend runs on [http://localhost:8000](http://localhost:8000).

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Using the API

1. Open [http://localhost:8000/docs](http://localhost:8000/docs)
2. Use the video/job endpoints to submit processing jobs
3. Fetch telemetry and lap comparison data from the telemetry endpoints
4. Lap comparison is available via `POST /telemetry/compare` (see Swagger for request schema)

## CLI Alternative (Primary Workflow)

For local analysis without the API:

```bash
# Place videos in videos/, then extract
python main.py

# Position-based comparison from a generated CSV
python -c "
import pandas as pd
from src.interactive_visualizer import InteractiveTelemetryVisualizer
viz = InteractiveTelemetryVisualizer()
df = pd.read_csv('data/output/telemetry_YYYYMMDD_HHMMSS.csv')
viz.plot_position_based_comparison(df)
"
```

## Stopping the Server

Press `Ctrl+C` in the terminal, or:

```bash
pkill -f "python run_server.py"
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.8+)
- Install missing dependencies: `pip install -r requirements.txt`
- Check port 8000 isn't already in use: `lsof -i :8000` (macOS/Linux)

### Video processing fails
- Ensure the video file path exists and is readable by the server
- Check video format is supported (MP4, AVI, MOV)
- Verify video has ACC HUD visible
- Check backend logs for detailed error messages

## Configuration

### Change Backend Port

Edit [src/web/config.py](src/web/config.py):
```python
api_port = 8001  # Change to desired port
```

## Next Steps

- Check [CLAUDE.md](CLAUDE.md) for computer vision implementation details
- See [docs/POSITION_BASED_LAP_COMPARISON.md](docs/POSITION_BASED_LAP_COMPARISON.md) for lap comparison
- Explore the API at [http://localhost:8000/docs](http://localhost:8000/docs)

## Production Deployment

```bash
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --workers 4
```

See [DEPLOY.md](DEPLOY.md) for Hugging Face Spaces deployment notes.
