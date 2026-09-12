# ACC Telemetry Extractor - Documentation Index

Welcome to the ACC Telemetry Extractor documentation. This index will help you find the information you need.

## Start Here

If you're new to the project, start with these documents:

1. **[../README.md](../README.md)** - Project overview and quick start
2. **[USER_GUIDE.md](USER_GUIDE.md)** - Complete usage guide with examples
3. **[FEATURES.md](FEATURES.md)** - Feature descriptions and development journey

## Core Documentation

### For Users

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive usage guide
  - Quick start instructions
  - Interactive visualization usage
  - Position-based lap comparison
  - CSV data interpretation
  - Common use cases and workflows

- **[FEATURES.md](FEATURES.md)** - Feature descriptions with development history
  - Core telemetry extraction (throttle, brake, steering)
  - Lap number detection (OCR evolution)
  - Track position tracking (minimap analysis)
  - Interactive visualization (Plotly)
  - Position-based comparison (gold standard analysis)
  - Explains WHY each approach was chosen

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solutions to common issues
  - Resolution and ROI problems
  - Lap detection issues (with bug fix history)
  - Telemetry extraction problems
  - Position tracking issues
  - Performance optimization
  - Complete historical bug fixes

### For Developers

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and design decisions
  - System overview and module descriptions
  - Implementation details and algorithms
  - Development journey (what was tried and why)
  - Design principles and lessons learned
  - Performance characteristics
  - Future enhancement ideas

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Original project summary (historical)
  - Beginner-friendly explanation of how it works
  - Technology stack explanation
  - Key concepts for beginners
  - The journey of building the initial version

## Specialized Topics

### Position Tracking

- **[POSITION_BASED_LAP_COMPARISON.md](POSITION_BASED_LAP_COMPARISON.md)** - Position-based analysis guide
  - Why position-based comparison is superior
  - Complete usage guide with examples
  - Analysis workflows and interpretation
  - Practical examples

- **[TRACK_POSITION_TRACKING.md](TRACK_POSITION_TRACKING.md)** - Track position implementation
  - How position tracking works
  - Racing line extraction algorithm
  - Red dot detection and position calculation
  - Configuration and testing

- **[RACING_LINE_EXTRACTION.md](RACING_LINE_EXTRACTION.md)** - Multi-frame frequency voting technique
  - The problem (red dot occlusion)
  - The solution (frequency voting)
  - Why it works
  - Algorithm details and parameters

### Performance & Optimization

- **[PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)** - OCR performance evolution
  - pytesseract vs tesserocr comparison
  - Template matching (historical intermediate step)
  - Performance benchmarks
  - Why tesserocr is the current default

- **[PERFORMANCE_LOGGING.md](PERFORMANCE_LOGGING.md)** - Performance tracking features
  - What is measured
  - How to interpret performance reports
  - Optimization targets

## Historical/Deprecated Documents

These documents describe features or bugs that have been resolved but are preserved for historical context:

### "What's New" Announcements (Historical)

These were feature announcements during development. The information has been incorporated into the main documentation above.

- **[WHATS_NEW.md](WHATS_NEW.md)** - Interactive visualization announcement (Oct 2024)
- **[WHATS_NEW_LAP_FIX.md](WHATS_NEW_LAP_FIX.md)** - Lap oscillation bug fix announcement (Oct 2024)
- **[WHATS_NEW_POSITION_COMPARISON.md](WHATS_NEW_POSITION_COMPARISON.md)** - Position comparison announcement (Oct 2024)
- **[WHATS_NEW_KALMAN_FILTERING.md](WHATS_NEW_KALMAN_FILTERING.md)** - Kalman filtering announcement (Oct 2024, later replaced)

### Bug Fix Documents (Historical)

Detailed technical analyses of bugs that were discovered and fixed. Information incorporated into TROUBLESHOOTING.md.

- **[LAP_DETECTION_BUG_FIX.md](LAP_DETECTION_BUG_FIX.md)** - Lap oscillation bug (Oct 2024, FIXED)
  - Technical analysis of 10↔11, 20↔21 oscillations
  - Root cause analysis
  - Solution implementation
  - Before/after results

- **[lap_detection_fix.md](lap_detection_fix.md)** - Lap 0 rejection bug (Oct 2024, FIXED)
  - Lap 0 not being saved
  - OCR misreads being accepted
  - Insufficient temporal smoothing
  - Solutions implemented

- **[THROTTLE_DETECTION_BUG_FIX.md](THROTTLE_DETECTION_BUG_FIX.md)** - False throttle bug (Oct 2024, FIXED)
  - UI text artifacts detected as throttle
  - Pixel threshold solution
  - Verification results

### Deprecated Features

- **[KALMAN_FILTERING.md](KALMAN_FILTERING.md)** - Kalman filtering implementation (DEPRECATED)
  - ⚠️ **Status**: Implemented, tested, then replaced with simpler approach
  - Why it was tried (outlier rejection for position tracking)
  - How it worked (FilterPy, 1D Kalman filter)
  - Why it was replaced (unnecessary complexity, simpler threshold works equally well)
  - Preserved as learning artifact

### Visualization Guides (Partially Historical)

- **[DETAILED_ANALYSIS_GUIDE.md](DETAILED_ANALYSIS_GUIDE.md)** - Static visualization guide (HISTORICAL)
  - Describes the old detailed static PNG visualizations
  - The `generate_detailed_analysis.py` / `detailed_visualizer.py` scripts were removed
  - Use interactive HTML from `main.py` and `InteractiveTelemetryVisualizer` instead

- **[INTERACTIVE_VISUALIZATION_GUIDE.md](INTERACTIVE_VISUALIZATION_GUIDE.md)** - Interactive viz guide
  - Plotly visualizations (current)
  - Also covered in USER_GUIDE.md

### Lap Recognition (Partially Historical)

- **[TEMPLATE_MATCHING_GUIDE.md](TEMPLATE_MATCHING_GUIDE.md)** - Template matching user guide (HISTORICAL)
  - Intermediate lap-number approach; not used by `extract_lap_number()` today
  - tesserocr is the current default (see FEATURES.md)

- **[TEMPLATE_MATCHING_IMPLEMENTATION.md](TEMPLATE_MATCHING_IMPLEMENTATION.md)** - Implementation details (HISTORICAL)
  - Sliding window algorithm from the template-matching phase

- **[LAP_RECOGNITION_FEATURE.md](LAP_RECOGNITION_FEATURE.md)** - Original lap detection feature
  - OCR-based lap number detection
  - Lap time extraction
  - Initial implementation (before template matching)
  - Some information now outdated (describes only pytesseract, not tesserocr)

## Quick Reference

### I want to...

**...extract telemetry from my first video**
→ Start with [USER_GUIDE.md](USER_GUIDE.md) Quick Start section

**...understand why position-based comparison is better**
→ Read [POSITION_BASED_LAP_COMPARISON.md](POSITION_BASED_LAP_COMPARISON.md)

**...fix telemetry extraction issues**
→ Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**...understand how the system works technically**
→ Read [ARCHITECTURE.md](ARCHITECTURE.md)

**...know what features are available and how they evolved**
→ Read [FEATURES.md](FEATURES.md)

**...configure ROI for different video resolution**
→ See [USER_GUIDE.md](USER_GUIDE.md) Resolution Configuration section

**...understand why tesserocr replaced pytesseract**
→ Read [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) (template matching history: [TEMPLATE_MATCHING_GUIDE.md](TEMPLATE_MATCHING_GUIDE.md))

**...learn about historical bugs and how they were fixed**
→ Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) Historical Bug Fixes section

**...understand why Kalman filtering was replaced**
→ Read [KALMAN_FILTERING.md](KALMAN_FILTERING.md) and [FEATURES.md](FEATURES.md) Position Tracking section

**...contribute to the project**
→ Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details and design philosophy

## Documentation Philosophy

This documentation follows these principles:

1. **Preserve the Journey** - We document what was tried, what worked, what didn't, and why
2. **Explain the Why** - Not just how to use features, but why they exist and why certain approaches were chosen
3. **Historical Context** - Deprecated features and bug fixes are preserved as learning artifacts
4. **Progressive Disclosure** - Start with user guides, dive deeper into technical docs as needed
5. **Practical Focus** - Real-world examples and workflows, not just API documentation

## Contributing to Documentation

When updating documentation:

1. **Don't delete historical information** - Mark as deprecated/historical instead
2. **Explain the evolution** - Show what was tried and why decisions were made
3. **Update the index** - Keep this README.md current
4. **Cross-reference** - Link related documents together
5. **Preserve context** - Future developers benefit from understanding the journey

## Changelog

**January 2025** - Documentation reorganization
- Created consolidated core docs (USER_GUIDE, FEATURES, TROUBLESHOOTING, ARCHITECTURE)
- Preserved all historical documents and bug fix information
- Added this index to help navigate documentation
- Organized docs by audience (users vs developers) and purpose

**September 2026** - Accuracy pass against current code
- Lap numbers documented as tesserocr; template matching guides marked historical
- Named ROI profiles instead of a single 720p layout
- Web compare path is `POST /api/telemetry/compare` (JSON, not HTML)
- `main.py` outputs CSV + interactive HTML only; position HTML is a separate visualizer call

**September 2025** - Removed stale file references
- Dropped docs for deleted CLI helpers (`compare_laps.py`, `compare_laps_by_position.py`, `generate_detailed_analysis.py`, etc.)
- Documented current workflows: `videos/` + `main.py`, visualizer APIs, and optional `run_server.py` web API

**October 2024** - Active development period
- Multiple "What's New" announcements as features were added
- Bug fix documentation as issues were discovered and resolved
- Feature-specific guides created during implementation

## Getting Help

If you can't find what you're looking for:

1. Check this index for relevant documents
2. Use your text editor's search across all docs (search for keywords)
3. Review git history for context on specific changes
4. Open an issue on GitHub with questions

---

**Remember**: The documentation reflects the development journey. Mistakes and experiments are documented alongside successes because they teach us how we arrived at the current, working solution.
