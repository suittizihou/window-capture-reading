# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Window Capture Reading is a Windows application that captures specified windows in real-time, detects screen changes, and plays notification sounds. Built with Python 3.11+, it uses Win32 API for window capture and OpenCV/scikit-image for difference detection.

## Development Commands

### Setup
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```powershell
# Run the application
python -m src.main

# Run pre-built EXE
.\dist\WindowCaptureReading.exe
```

### Testing
```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/services/test_window_capture.py
```

### Code Quality
```powershell
# Format code with Black (88 char line length)
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### License Management
```powershell
# Update license information
python scripts/check_licenses.py

# Pre-release license check
python scripts/pre_release_check.py
```

### Building Executable
```powershell
# Install PyInstaller
pip install pyinstaller

# Build EXE using spec file
pyinstaller WindowCaptureReading.spec

# Manual build (not recommended - use spec file instead)
pyinstaller --add-data "resources;resources" --windowed --name WindowCaptureReading --icon "resources/icon.ico" src/main.py
```

## Architecture

### Core Components

**Window Capture (`src/services/window_capture.py`)**
- Uses **Windows.Graphics.Capture API** via `windows-capture` library for high-performance screen capture
- Event-driven architecture with background thread (`start_free_threaded()`)
- Captures specific windows by title using `window_name` parameter
- Maintains latest frame in thread-safe buffer for on-demand retrieval
- Returns numpy arrays (BGR format) for OpenCV compatibility
- Supports DirectX applications that traditional Win32 APIs cannot capture

**Difference Detection (`src/services/difference_detector.py`)**
- Two detection methods: SSIM (Structural Similarity Index) and absolute difference
- SSIM is default and more robust to lighting changes
- Maintains frame history and implements cooldown mechanism
- Returns `DiffResult` with boolean flag, diff image, and similarity score

**Configuration (`src/utils/config.py`)**
- Singleton pattern via `get_config()` function
- Uses `dataclass` for type safety
- Auto-creates `config.json` in project root (or next to EXE when frozen)
- Key settings: `window_title`, `capture_interval`, `diff_threshold`, `diff_method`, `notification_sound`

**GUI (`src/gui/main_window.py`)**
- Tkinter-based interface with DPI awareness
- Real-time preview of captured window with ROI selection
- Difference visualization canvas
- Settings dialog for threshold adjustment
- Runs capture/detection in separate threads to avoid UI blocking

### Threading Model

The application uses multiple threads to maintain UI responsiveness:
- **Main Thread**: Tkinter GUI event loop
- **Capture Thread**: Polls `WindowCapture.capture()` at regular intervals defined by `capture_interval`
- **Windows Capture Internal Thread**: Background thread managed by `windows-capture` library that continuously captures frames
- **Detection Thread**: Processes frames and detects differences
- Communication via `queue.Queue` for thread-safe data passing between capture and detection threads
- Thread-safe frame buffer in `WindowCapture` class protected by `threading.Lock`

### Entry Points

- `src/main.py`: Main entry point with CLI argument support (use this)
- `src/gui/__init__.py`: Contains `start_gui()` function (called by `src/main.py`)
- `src/gui/main_window.py`: Contains the actual GUI implementation

## Coding Standards

### Style (from Cursor rules)
- **PEP8** formatting with **88 character line limit** (Black default)
- **Full type annotations** for all functions and classes
- **Docstrings** required for all functions/classes (PEP257)
- Naming conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE_WITH_UNDERSCORES` for constants

### Error Handling
- Use centralized logging via `src/utils/logging_config.py`
- Always capture context with `logger.error(msg, exc_info=True)`
- Never expose sensitive information in logs

### Type Hints
- Image arrays: Use `NDArray[np.uint8]` or custom `ImageArray` type alias
- Optional values: Explicit `Optional[T]` annotations
- All function parameters and return types must be annotated

## Project Structure

```
src/
  gui/              # GUI components (Tkinter)
    main_window.py  # Main application window
    settings_dialog.py  # Settings UI
    preview_canvas.py   # Window capture preview
    diff_canvas.py      # Difference visualization
  services/         # Core business logic
    window_capture.py       # Win32 window capture
    difference_detector.py  # Image difference detection
    memory_watcher.py       # Memory monitoring
    logger.py               # Logging utilities
  utils/            # Shared utilities
    config.py           # Configuration management
    logging_config.py   # Logging setup
    performance.py      # Performance monitoring
    messages.py         # UI messages
    resource_path.py    # PyInstaller resource paths
  main.py           # CLI entry point
  version.py        # Version information

resources/          # Static assets (sounds, icons)
tests/              # Unit tests (mirrors src/ structure)
docs/               # Documentation
scripts/            # Utility scripts (license checks)
```

## Configuration File

`config.json` is auto-generated with defaults on first run. Example:

```json
{
  "window_title": "Window Capture Reading - LDPlayer",
  "capture_interval": 1.0,
  "diff_threshold": 0.035,
  "diff_method": "ssim",
  "notification_sound": true
}
```

- `diff_threshold`: Lower values = more sensitive (0.01-0.1 typical range)
- `diff_method`: "ssim" (recommended) or "absdiff"
- `capture_interval`: Seconds between captures

## Important Notes

### PyInstaller Frozen Environment
- Use `src/utils/resource_path.py` or `src/resource_path.py` for resource paths
- Check `getattr(sys, "frozen", False)` to detect EXE mode
- Config saves to `[exe_dir]/config/` when frozen

### Windows-Specific
- This is a **Windows-only** application (Win32 API dependency)
- Requires Windows 10/11
- DPI awareness handled via `SetProcessDPIAware()`

### License Compliance
- GitHub Actions automatically checks licenses on dependency changes
- LICENSES.md is auto-generated from dependencies
- See `docs/license_compliance.md` for details

### GUI Responsiveness
- Always run long operations (capture, detection) in background threads
- Use `queue.Queue` for thread-safe communication with GUI
- Update GUI via `root.after()` from worker threads

## Testing Notes

- Tests are located in `tests/` mirroring `src/` structure
- Currently limited test coverage (mainly `test_window_capture.py`)
- Use pytest fixtures for common setup
- Mock Win32 API calls when testing window capture

## Build and Release

- GitHub Actions workflow triggers on `v*` tags
- Workflow file: `.github/workflows/release-exe.yml`
- Creates GitHub release with EXE artifact
- See `docs/exe_build.md` for manual build instructions