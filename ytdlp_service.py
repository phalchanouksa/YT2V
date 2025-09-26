import json
import os
import re
import subprocess
from typing import Callable, Dict, List, Tuple


def _hidden_startupinfo():
    startupinfo = None
    if hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def fetch_video_info(url: str) -> Dict:
    """Run yt-dlp to fetch video info JSON for a given URL."""
    command = ['yt-dlp', '--dump-json', url]
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        encoding='utf-8',
        startupinfo=_hidden_startupinfo(),
    )
    return json.loads(process.stdout)


def parse_streams(video_info: Dict, include_video_only: bool) -> Tuple[List[Dict], List[str]]:
    """Parse formats to a simplified streams list and user-facing option strings."""
    yt_streams: List[Dict] = []

    for f in video_info.get('formats', []):
        filesize = f.get('filesize') or f.get('filesize_approx')
        if f.get('vcodec') == 'none' or not filesize:
            continue  # Skip audio-only or unknown size

        is_progressive = f.get('acodec') != 'none'
        if is_progressive:
            note = "(Standard)"
        elif include_video_only:
            note = "(HQ - Merged w/ Audio)"
        else:
            continue

        yt_streams.append({
            'id': f.get('format_id'),
            'res': f.get('resolution'),
            'size': round(filesize / 1024 / 1024, 2),
            'ext': f.get('ext'),
            'note': note,
            'progressive': is_progressive,
        })

    # Sort by vertical resolution descending if available
    def sort_key(s: Dict) -> int:
        try:
            return int(s['res'].split('x')[1])
        except Exception:
            return 0

    yt_streams.sort(key=sort_key, reverse=True)
    stream_options = [f"{s['res']} {s['note']} [{s['ext']}] - {s['size']} MB" for s in yt_streams]
    return yt_streams, stream_options


def ensure_ffmpeg_available(ffmpeg_executable: str) -> None:
    """Raise if ffmpeg is not available."""
    subprocess.run([ffmpeg_executable or 'ffmpeg', '-version'],
                   check=True, capture_output=True, startupinfo=_hidden_startupinfo())


def build_download_command(stream: Dict, url: str, output_template: str, ffmpeg_location: str = "") -> Tuple[List[str], bool]:
    """Build the yt-dlp download command for the given stream and url.

    Returns (command, is_hq_merge)
    """
    is_hq_merge = not stream['progressive']
    if is_hq_merge:
        # Prefer AAC/M4A when merging for better compatibility
        format_code = f"{stream['id']}+bestaudio[ext=m4a]/bestvideo+bestaudio"
    else:
        format_code = stream['id']

    command = [
        'yt-dlp', '-f', format_code,
        '--progress',
        '--merge-output-format', 'mp4',
        '--no-keep-fragments',
        '-o', output_template,
        url,
    ]

    if ffmpeg_location and is_hq_merge:
        command.extend(['--ffmpeg-location', os.path.dirname(ffmpeg_location)])

    return command, is_hq_merge


def run_download(command: List[str], on_progress: Callable[[float, str], None]) -> Tuple[int, str]:
    """Run the yt-dlp download process, parse progress, and stream output to a callback.

    Returns (returncode, full_output_text)
    """
    full_lines: List[str] = []
    progress_regex = re.compile(r"\[download\]\s+([0-9.]+)%")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
        encoding='utf-8',
        startupinfo=_hidden_startupinfo(),
    )

    if process.stdout is None:
        process.wait()
        return process.returncode, ""

    for line in iter(process.stdout.readline, ''):
        line = line.rstrip('\n')
        full_lines.append(line)
        if '[Merger]' in line or '[ExtractAudio]' in line:
            on_progress(100.0, "Merging media files...")
        m = progress_regex.search(line)
        if m:
            try:
                on_progress(float(m.group(1)), line)
            except Exception:
                pass

    process.wait()
    return process.returncode, "\n".join(full_lines)
