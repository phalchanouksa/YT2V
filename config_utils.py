import json
import os

CONFIG_FILE = "downloader_config.json"


def load_ffmpeg_path() -> str:
    """Load FFmpeg path from config file if present and valid."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                path = config.get("ffmpeg_path")
                if path and os.path.exists(path):
                    return path
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return ""


def save_ffmpeg_path(path: str) -> None:
    """Save FFmpeg path to config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"ffmpeg_path": path}, f)
