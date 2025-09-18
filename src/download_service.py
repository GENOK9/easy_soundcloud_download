from __future__ import annotations

import platform
from pathlib import Path
from typing import Callable, Optional
import yt_dlp  # pip install yt-dlp
import shutil

"""
Lädt den SoundCloud-Track nach out_path.
- out_path: system music ordner/ESC/filename.mp3
"""


def _ffmpeg_localer() -> str | None:
    m = platform.machine().lower()
    if "x86_64" in m or "amd64" in m:
        return "/usr/bin/ffmpeg"

    # ARM64: ffmpeg aus Assets kopieren
    if "aarch64" in m or "arm64" in m:
        exec_dir = Path("/data/data/com.flet.src/files/")

        for binary_name in ["ffmpeg", "ffprobe"]:

            dst = exec_dir / binary_name
            try:
                if not dst.exists():
                    shutil.copy2(binary_name, dst)
                    dst.chmod(0o755)

            except Exception as e:
                return None

        return str(exec_dir)

    return None


def download(
    info: dict,
    out_path: Path,
    progress_cb: Optional[Callable[[dict], None]] = None,
    is_canceled: Optional[Callable[[], bool]] = None,
    log: Optional[object] = None
) -> None:


    url = info.get("webpage_url")
    if not url:
        raise ValueError("download_service: URL missing")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_path.parent / out_path.stem)

    def _hook(d: dict):
        if is_canceled and is_canceled():
            raise yt_dlp.utils.DownloadError("Download manuell abgebrochen")

        if progress_cb:
            try:
                progress_cb(d)
            except Exception:
                pass


    ydl_opts_arm64 = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [_hook],
        "logger": log,
        "verbose": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredquality": "0",
            }
        ],
    }

    ydl_opts_x64 = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [_hook],
        "ffmpeg_location": "/usr/bin/ffmpeg",
        "logger": log,
        "verbose": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }
        ],
    }
    m = platform.machine().lower()
    if "x86_64" in m or "amd64" in m:
        with yt_dlp.YoutubeDL(ydl_opts_x64) as ydl:
            ydl.download([url])
        return
    else:
        with yt_dlp.YoutubeDL(ydl_opts_arm64) as ydl:
            ydl.download([url])