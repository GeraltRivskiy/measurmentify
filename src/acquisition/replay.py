from __future__ import annotations

from pathlib import Path
import numpy as np

from src.app_types import FrameDepth, Intrinsics


class ReplaySource:
    def __init__(
        self,
        data_dir: str | Path = "data",
        pattern: str = "*.npz",
        loop: bool = True,
        config_path: str | Path = "configs/config.yaml",
    ):
        self.data_dir = Path(data_dir)
        self.pattern = pattern
        self.loop = loop
        self.config_path = Path(config_path)
        self._paths = sorted(self.data_dir.glob(self.pattern))
        if not self._paths:
            raise FileNotFoundError(f"No .npz files found in {self.data_dir!s} with pattern {self.pattern!r}")
        self._index = 0
        self._intrinsics_cfg = self._load_intrinsics(self.config_path)

    def read(self) -> FrameDepth:
        if self._index >= len(self._paths):
            if self.loop:
                self._index = 0
            else:
                raise StopIteration("No more depth frames to replay")
        path = self._paths[self._index]
        self._index += 1
        return self._load_npz(path)

    def _load_npz(self, path: Path) -> FrameDepth:
        with np.load(path) as data:
            depth_data = data["depth_data"]
            if depth_data.ndim != 2:
                raise ValueError(f"depth_data must be 2D, got shape {depth_data.shape} in {path!s}")
            if depth_data.dtype != np.uint16:
                depth_data = depth_data.astype(np.uint16, copy=False)

            height, width = depth_data.shape
            if "width" in data and int(data["width"]) != width:
                raise ValueError(f"width mismatch in {path!s}: {int(data['width'])} != {width}")
            if "height" in data and int(data["height"]) != height:
                raise ValueError(f"height mismatch in {path!s}: {int(data['height'])} != {height}")

            depth_scale = float(data["depth_scale"]) if "depth_scale" in data else 1.0
            intrinsics = self._intrinsics_from_config(width, height)
            timestamp_ns = int(data["timestamp_ns"]) if "timestamp_ns" in data else None

        return FrameDepth(
            depth=depth_data,
            intrinsics=intrinsics,
            depth_scale=depth_scale,
            timestamp_ns=timestamp_ns,
        )

    @staticmethod
    def _load_intrinsics(config_path: Path) -> dict[str, float]:
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "PyYAML is required to read intrinsics from config.yaml. "
                "Install it with: pip install pyyaml"
            ) from exc

        if not config_path.exists():
            raise FileNotFoundError(f"config.yaml not found: {config_path!s}")

        with config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        intr = (cfg.get("acquisition") or {}).get("intrinsics") or {}
        required = ("fx", "fy", "cx", "cy")
        missing = [k for k in required if k not in intr]
        if missing:
            raise KeyError(f"Missing intrinsics keys in {config_path!s}: {', '.join(missing)}")
        return {k: float(intr[k]) for k in ("fx", "fy", "cx", "cy", "width", "height") if k in intr}

    def _intrinsics_from_config(self, width: int, height: int) -> Intrinsics:
        cfg = self._intrinsics_cfg
        cfg_w = int(cfg["width"]) if "width" in cfg else width
        cfg_h = int(cfg["height"]) if "height" in cfg else height
        if (cfg_w, cfg_h) != (width, height):
            raise ValueError(
                f"Depth shape {width}x{height} does not match config intrinsics "
                f"{cfg_w}x{cfg_h} from {self.config_path!s}"
            )

        return Intrinsics(
            fx=float(cfg["fx"]),
            fy=float(cfg["fy"]),
            cx=float(cfg["cx"]),
            cy=float(cfg["cy"]),
            width=cfg_w,
            height=cfg_h,
        )
