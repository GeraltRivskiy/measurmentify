from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyorbbecsdk import Config, OBSensorType, Pipeline, OBPropertyID


def _points_to_numpy(points) -> np.ndarray:
    points_np = np.asarray(points)
    if points_np.dtype.fields:
        points_np = np.stack(
            (points_np["x"], points_np["y"], points_np["z"]),
            axis=-1,
        )
    return points_np.astype(np.float32, copy=False)


def _resolve_output_path(name: str | None) -> Path:
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    if name:
        path = Path(name)
        if path.suffix.lower() != ".npz":
            path = path.with_suffix(".npz")
        if path.parent == Path("."):
            return out_dir / path
        return path
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return out_dir / f"point_cloud_{ts}.npz"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--name",
        help="Output filename for .npz (default: timestamped in ./data). "
        "You can pass a name or a path.",
    )
    args = parser.parse_args()

    config = Config()
    pipeline = Pipeline()

    device = pipeline.get_device()
    device.set_bool_property(OBPropertyID.OB_PROP_DEPTH_SOFT_FILTER_BOOL, False)

    try:
        profile_list = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        assert profile_list is not None
        depth_profile = profile_list.get_default_video_stream_profile()
        assert depth_profile is not None
        print("depth profile: ", depth_profile)
        depth_intrinsics = depth_profile.get_intrinsic()
        config.enable_stream(depth_profile)
    except Exception as e:
        print(e)
        return

    pipeline.start(config)
    camera_param = pipeline.get_camera_param()
    frames = pipeline.wait_for_frames(10000)
    if frames is None:
        print("Frame was not obtained")
        pipeline.stop()
        return

    depth_frame = frames.get_depth_frame()
    if depth_frame is None:
        print("Depth frame was not obtained")
        pipeline.stop()
        return

    width = depth_frame.get_width()
    height = depth_frame.get_height()
    depth_scale = depth_frame.get_depth_scale()

    points = frames.get_point_cloud(camera_param)
    points_np = _points_to_numpy(points)

    out_path = _resolve_output_path(args.name)
    np.savez_compressed(
        out_path,
        points=points_np,
        width=width,
        height=height,
        depth_scale=depth_scale,
        fx=float(depth_intrinsics.fx),
        fy=float(depth_intrinsics.fy),
        cx=float(depth_intrinsics.cx),
        cy=float(depth_intrinsics.cy),
        intr_width=int(depth_intrinsics.width),
        intr_height=int(depth_intrinsics.height),
    )
    print(f"saved: {out_path}")

    pipeline.stop()


if __name__ == "__main__":
    main()

