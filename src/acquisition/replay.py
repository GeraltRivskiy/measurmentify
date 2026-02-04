from __future__ import annotations

from pathlib import Path
import numpy as np
import open3d as o3d

from src.app_types import PointCloud, Intrinsics


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
        self._intrinsics_cfg = None
        self._intrinsics_error = None
        try:
            self._intrinsics_cfg = self._load_intrinsics(self.config_path)
        except Exception as exc:
            self._intrinsics_error = exc

    def read(self) -> PointCloud:
        if self._index >= len(self._paths):
            if self.loop:
                self._index = 0
            else:
                raise StopIteration("No more depth frames to replay")
        path = self._paths[self._index]
        self._index += 1
        return self._load_npz(path)

    def _load_npz(self, path: Path) -> PointCloud:
        with np.load(path) as data:
            if "points" not in data:
                raise KeyError(f"Missing 'points' in {path!s}. Expected point cloud .npz format.")

            points = data["points"]
            if points.ndim != 2 or points.shape[1] != 3:
                raise ValueError(f"points must be Nx3, got shape {points.shape} in {path!s}")
            if points.dtype != np.float32:
                points = points.astype(np.float32, copy=False)

            width = int(data["width"]) if "width" in data else None
            height = int(data["height"]) if "height" in data else None
            if width is None and "intr_width" in data:
                width = int(data["intr_width"])
            if height is None and "intr_height" in data:
                height = int(data["intr_height"])
            if width is None or height is None:
                raise KeyError(f"Missing width/height metadata in {path!s}")

            depth_scale = float(data["depth_scale"]) if "depth_scale" in data else 1.0
            intrinsics = self._intrinsics_from_file_or_config(data, width, height)
            timestamp_ns = int(data["timestamp_ns"]) if "timestamp_ns" in data else None

        pcd = self._convert_to_o3d_point_cloud(points)
        return PointCloud(
            pcd=pcd,
            intrinsics=intrinsics,
            depth_scale=depth_scale,
            timestamp_ns=timestamp_ns,
        )

    @staticmethod
    def _convert_to_o3d_point_cloud(points: np.ndarray) -> o3d.geometry.PointCloud:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        return pcd

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

    def _intrinsics_from_file_or_config(
        self,
        data: np.lib.npyio.NpzFile,
        width: int,
        height: int,
    ) -> Intrinsics:
        if all(k in data for k in ("fx", "fy", "cx", "cy")):
            intr_w = int(data["intr_width"]) if "intr_width" in data else width
            intr_h = int(data["intr_height"]) if "intr_height" in data else height
            return Intrinsics(
                fx=float(data["fx"]),
                fy=float(data["fy"]),
                cx=float(data["cx"]),
                cy=float(data["cy"]),
                width=intr_w,
                height=intr_h,
            )

        if self._intrinsics_cfg is None:
            if self._intrinsics_error is not None:
                raise self._intrinsics_error
            raise KeyError("Missing intrinsics in file and config intrinsics not available")

        return self._intrinsics_from_config(width, height)

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
