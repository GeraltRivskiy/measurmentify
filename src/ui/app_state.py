from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppMode(str, Enum):
    DEBUG = "debug"
    USE = "use"


class SourceMode(str, Enum):
    CAMERA = "camera"
    FILE = "file"


class ViewLayer(str, Enum):
    RAW = "raw"
    DOWNSAMPLED = "downsampled"
    TABLE = "table"
    OBJECT = "object"
    FILTERED = "filtered"


@dataclass
class AppState:
    mode: AppMode = AppMode.DEBUG
    source: SourceMode = SourceMode.CAMERA
    layer: ViewLayer = ViewLayer.RAW
    camera_connected: bool = False
    last_file: str | None = None
