# YT2V

A simple, reliable YouTube downloader GUI for Windows built on `yt-dlp` with optional FFmpeg merging for high-quality formats.

## Features
- Fetch available video qualities from a YouTube URL.
- Standard (progressive) and High-Quality (video-only merged with audio via FFmpeg).
- Set and persist custom FFmpeg path (`downloader_config.json`).
- Live progress updates and status messages.
- Choose output folder and auto-sanitized filenames.

## Requirements
- Python 3.10+ (tested on 3.12)
- `yt-dlp` Python package
- FFmpeg (required for merging high-quality video + audio)
  - Download: https://ffmpeg.org
  - Either add `ffmpeg` to your system PATH or set the path inside the app using the "Set FFmpeg Path" button.

Install dependencies in your virtual environment (recommended):

```bash
# From the project root
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install yt-dlp pyinstaller
```

## Run from source
```bash
python main.py
```

## Build a portable EXE (Windows)
Use PyInstaller to build a single-file, windowed executable:

```bash
pyinstaller --onefile --noconsole --name YT2V main.py
```

- The EXE will be in the `dist/` folder as `YT2V.exe`.
- If you want a console for debugging, omit `--noconsole`.
- Optional: add an icon via `--icon path\to\icon.ico`.

### Notes about portability
- This app calls `yt-dlp` via Python. The EXE built with `--onefile` includes your Python code and packages, but the target machine still needs FFmpeg to be installed or a path set in the app for high-quality merges.
- If you want to ship a fully offline bundle, you can also include a copy of `yt-dlp.exe` and adjust the code to call that bundled binary instead of relying on the Python package. Ask for help if you need this mode.

## Configuration
- The app stores the FFmpeg path in `downloader_config.json` in the project directory.
- This file is intentionally ignored by Git via `.gitignore`.

## Project structure
```
.
├─ main.py                # App bootstrap
├─ ui.py                  # Tkinter UI (YouTubeDownloader)
├─ ytdlp_service.py       # yt-dlp/FFmpeg operations
├─ config_utils.py        # Config load/save helpers
├─ downloader_config.json # Local config (FFmpeg path)
└─ README.md              # This file
```

## Troubleshooting
- "yt-dlp not found" or errors when fetching: ensure `yt-dlp` is installed in the same environment you run/build from.
- High-quality download merge fails: set FFmpeg path in the app or install FFmpeg and ensure it’s in PATH.
- Antivirus flags the EXE: some AVs are sensitive to onefile packers. Consider using one-folder mode (`pyinstaller --onedir`) if this occurs.
