# Python
from __future__ import annotations

import asyncio
import platform
from pathlib import Path
from typing import Dict, Optional, Callable
import re

from download_item import DownloadItem
from enums import Download_Status
import download_service, soundcloud_resolver

ProgressHook = Callable[[dict], None]
StatusHook = Callable[[Download_Status, Optional[str]], None]

def _detect_music_dir() -> Path:
    """
    Versucht plattformübergreifend den Music-Ordner zu finden.
    """
    home = Path.home()

    if platform.machine().lower() in ("aarch64", "arm64"):
        esc_path = Path("/sdcard/Download/ESC")
        if esc_path.exists():
            return esc_path
        esc_path.mkdir(parents=True, exist_ok=True)
        return esc_path

    # Linux: XDG user dirs
    xdg_file = home / ".config" / "user-dirs.dirs"
    if xdg_file.exists():
        try:
            text = xdg_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("XDG_MUSIC_DIR"):
                    # Format: XDG_MUSIC_DIR="$HOME/Music"
                    val = line.split("=", 1)[1].strip().strip('"')
                    val = val.replace("$HOME", str(home))
                    p = Path(val)
                    if p.exists():
                        return p / "ESC"
        except Exception:
            pass

    # Fallback
    return home

def _default_base_dir() -> Path:
    music = _detect_music_dir()
    return music

class DownloadController:
    """
    Nimmt link entgegen, zieht Metadaten und Startet Download mit Download_service
    """
    def __init__(self, base_dir: Path | str = "storage", max_concurrent: int = 2):
        # auto-Modus unterstützt: legt unter dem lokalen Musik-Ordner "ESC" an
        if base_dir == "auto":
            self.base_dir = _default_base_dir()
        else:
            self.base_dir = Path(base_dir)

        # parallele Downloads begrenzen
        self._sema = asyncio.Semaphore(max_concurrent)

        # Verwaltung
        self._items: Dict[str, DownloadItem] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    # API für View
    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        return self._items.get(item_id)

    def list_items(self) -> list[DownloadItem]:
        return list(self._items.values())

    def cancel(self, item_id: str) -> None:
        item = self._items.get(item_id)
        if not item:
            return
        item.cancel()

    def add_link(
        self,
        url: str,
        on_progress: Optional[ProgressHook] = None,
        on_status: Optional[StatusHook] = None,
        log = None
    ) -> DownloadItem:
        """
        wird von GUI aufgerufen, startet download_service und returned Item für die Listview
        """
        url = (url or "").strip()
        if not self._is_valid_soundcloud_url(url):
            item = DownloadItem(url=url)
            item.set_status(Download_Status.FAILED, "Ungültige URL")
            self._items[item.id] = item
            return item

        item = DownloadItem(url=url)
        item.on_progress = on_progress
        item.on_status_change = on_status
        item.set_status(Download_Status.FETCHING)

        self._items[item.id] = item

        # Download Process
        task = asyncio.create_task(self._process_item(item, log))
        self._tasks[item.id] = task
        task.add_done_callback(lambda t: self._tasks.pop(item.id, None))

        return item

    # Kernablauf
    async def _process_item(self, item: DownloadItem, log = None) -> None:
        try:
            #Metadaten einholen
            info = await self._resolve_metadata(item)
            if item.canceled:
                return

            # Metadaten auf item legen
            item.title = info.get("title") or item.title
            item.uploader = info.get("uploader") or info.get("artist") or item.uploader
            item.image_url = info.get("thumbnail") or item.image_url
            item.ext = (info.get("ext") or "mp3").lstrip(".")

            #Dateipfad bilden (künstler_-_titelname.ext)
            out_path = self._make_output_path(
                self.base_dir,
                item.uploader or "",
                item.title or "",
                item.ext or "m4a",
            )
            item.filename = out_path

            # Status “bereit”
            item.set_status(Download_Status.READY)

            if item.canceled:
                return

            # Download ausführen. mit sema werden parallele downloads begrenzt.
            async with self._sema:
                item.set_status(Download_Status.DOWNLOADING)

                def on_progress_hook(d: dict):
                    status = d.get("status")
                    if status == "downloading":
                        total = d.get("total_bytes") or d.get("total_bytes_estimate")
                        downloaded = d.get("downloaded_bytes") or 0
                        speed = d.get("speed")
                        eta = d.get("eta")
                        item.update_progress(
                            downloaded_bytes=int(downloaded),
                            total_bytes=int(total) if total else None,
                            speed=float(speed) if speed else None,
                            eta=int(eta) if eta else None,
                            status=Download_Status.DOWNLOADING,
                        )
                    elif status == "finished":
                        item.update_progress(
                            downloaded_bytes=item.total_bytes or item.downloaded_bytes,
                            total_bytes=item.total_bytes,
                            status=Download_Status.DOWNLOADING,
                        )
                # Python 2.7 warning ist hier irrelevant
                await asyncio.to_thread(
                    download_service.download,
                    info,
                    out_path= item.filename,
                    progress_cb=on_progress_hook,
                    is_canceled=lambda: item.canceled,
                    log = log
                )

            if item.canceled:
                return

            #Fertig
            item.mark_completed()

        except Exception as e:
            item.mark_failed(str(e))

    # Hilfsfunktionen
    async def _resolve_metadata(self, item: DownloadItem) -> dict:
        """
        Erwartet ein dict mit title, uploader, Download-Infos.
        """
        return await asyncio.to_thread(soundcloud_resolver.resolve, item.url)

    @staticmethod
    def _is_valid_soundcloud_url(url: str) -> bool:
        return bool(url and "soundcloud.com" in url.lower())

    @staticmethod
    def _sanitize_component(s: str) -> str:
        illegal = r'\/:*?"<>|'
        s = "".join(ch for ch in s if ch not in illegal)
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"_+", "_", s)
        return s.strip("._")

    def _make_output_path(self, base_dir: Path, artist: str, title: str, ext: str) -> Path:
        """
        ${künstlername}_-_${titelname}.ext
        - Kollisionen: name.ext, name (1).ext, ...
        """
        artist_s = self._sanitize_component(artist)
        title_s = self._sanitize_component(title)
        if artist_s and title_s:
            stem = f"{artist_s}_-_{title_s}"
        else:
            stem = artist_s or title_s or "track"

        extension = ext.lstrip(".") or "mp3"
        candidate = base_dir / f"{stem}.{extension}"
        if not candidate.exists():
            return candidate

        i = 1
        while True:
            alt = base_dir / f"{stem} ({i}).{extension}"
            if not alt.exists():
                return alt
            i += 1