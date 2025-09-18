from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from uuid import uuid4

from enums import Download_Status

ProgressCallback = Callable[[Dict[str, Any]], None]
StatusCallback = Callable[[Download_Status, Optional[str]], None]


@dataclass
class DownloadItem:
    id: str = field(default_factory=lambda: uuid4().hex)
    url: str = ""
    filename: Optional[Path] = None

    # Metadaten (vom Resolver)
    title: Optional[str] = None
    image_url: Optional[str] = None
    uploader: Optional[str] = None

    # Fortschritt/Status
    status: Download_Status = Download_Status.QUEUED
    progress: float = 0.0  # 0.0 .. 1.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None  # KiB/s
    eta: Optional[int] = None
    error_message: Optional[str] = None

    # Zeiten
    created_at: datetime = field(default_factory=lambda:datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda:datetime.now(timezone.utc))

    # Controller-Hooks
    on_progress: Optional[ProgressCallback] = field(default=None, repr=False, compare=False)
    on_status_change: Optional[StatusCallback] = field(default=None, repr=False, compare=False)

    canceled: bool = False


    # Methoden für Status & Progress
    def set_status(self, status: Download_Status, error_message: Optional[str] = None) -> None:
        self.status = status
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
        if self.on_status_change:
            try:
                self.on_status_change(status, error_message)
            except Exception:
                #pass damit das programm nicht crashed
                pass

    def update_progress(
        self,
        downloaded_bytes: int,
        total_bytes: Optional[int] = None,
        speed: Optional[float] = None,
        eta: Optional[int] = None,
        status: Optional[Download_Status] = None,
    ) -> None:
        self.downloaded_bytes = max(0, downloaded_bytes)
        if total_bytes is not None:
            self.total_bytes = max(0, total_bytes)

        # Fortschrittsberechnung
        if self.total_bytes and self.total_bytes > 0:
            self.progress = min(1.0, self.downloaded_bytes / float(self.total_bytes))
        else:
            self.progress = 0.0

        self.speed = speed
        self.eta = eta
        if status is not None:
            self.status = status

        self.updated_at = datetime.utcnow()

        if self.on_progress:
            try:
                self.on_progress(self.progress_dict())
            except Exception:
                pass

    def mark_failed(self, message: str) -> None:
        self.set_status(Download_Status.FAILED, error_message=message)

    def mark_completed(self) -> None:
        if self.total_bytes is not None:
            self.downloaded_bytes = self.total_bytes
            self.progress = 1.0
        self.set_status(Download_Status.COMPLETED)

    def cancel(self) -> None:
        self.canceled = True
        self.set_status(Download_Status.CANCELED)

    def progress_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.name,
            "progress": self.progress,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "speed": self.speed,
            "eta": self.eta,
            "filename": str(self.filename) if self.filename else None,
            "title": self.title,
        }