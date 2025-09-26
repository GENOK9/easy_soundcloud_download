# Python
from __future__ import annotations

from typing import Dict, Optional

from urllib.parse import urlparse
import yt_dlp  #pip install yt-dlp


def _is_soundcloud_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "soundcloud.com" in host


def resolve(url: str) -> Dict[str, Optional[str]]:
    """
    Gibt dictionary für den Controller zurück:
      - title
      - uploader
      - thumbnail
      - url,
    bei Playlists wird der erste Eintrag genommen.
    """
    if not _is_soundcloud_url(url):
        raise ValueError("Ungültige SoundCloud-URL")

    ydl_opts = {
        "quiet": True,
        "nocheckcertificate": True,
        "skip_download": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Playlist
    if info and info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if entries:
            info = entries[0]

    if not info:
        raise RuntimeError("Keine Informationen vom Resolver erhalten")

    title = info.get("title")
    uploader = info.get("uploader") or info.get("artist") or info.get("uploader_id")
    thumbnail = info.get("thumbnail")
    ext = (info.get("ext") or "m4a").lstrip(".")
    if not ext:
        ext = _guess_ext_from_formats(info) or "mp3"

    return {
        "title": title,
        "uploader": uploader,
        "artist": uploader,
        "thumbnail": thumbnail,
        "ext": ext,
        "webpage_url": info.get("webpage_url") or url,
    }


def _guess_ext_from_formats(info: dict) -> Optional[str]:
    formats = info.get("formats") or []
    audio_formats = [f for f in formats if f.get("acodec") and (not f.get("vcodec") or f.get("vcodec") == "none")]
    for f in audio_formats or formats:
        e = f.get("ext")
        if e:
            return e
    return None