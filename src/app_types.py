from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Intrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int

@dataclass(frozen=True, slots=True)
class FrameDepth:
    depth: NDArray[np.uint16]
    intrinsics: Intrinsics
    depth_scale: float
    timestamp_ns: Optional[int] = None

@dataclass(frozen=True, slots=True)
class DimsResult:
    length: float
    width: float
    height: float
    units: Literal["m","mm", "cms"] = "mm"
    bbox_type: Literal["aabb", "obb", "plane"] = "obb"