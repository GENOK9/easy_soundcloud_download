from enum import Enum
from typing import TypeAlias

class DownloadStatus(Enum):
    QUEUED = "QUEUED"
    FETCHING = "FETCHING"
    READY = "READY"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
Download_Status: TypeAlias = DownloadStatus