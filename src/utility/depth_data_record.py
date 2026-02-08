from pyorbbecsdk import Config
from pyorbbecsdk import OBSensorType
from pyorbbecsdk import Pipeline
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

def main():
    config = Config()
    pipeline = Pipeline()
    try:
        profile_list = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        assert profile_list is not None
        depth_profile = profile_list.get_default_video_stream_profile()
        assert depth_profile is not None
        print("depth profile: ", depth_profile)
        config.enable_stream(depth_profile)
    except Exception as e:
        print(e)
        return
    pipeline.start(config)
    frames = pipeline.wait_for_frames(500)
    

    depth_frame = frames.get_depth_frame()

    width = depth_frame.get_width()
    height = depth_frame.get_height()
    scale = depth_frame.get_depth_scale()

    depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
    depth_data = depth_data.reshape((height, width))

    print(depth_data)

    # Save depth data to .npz alongside basic metadata.
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"depth_data_{ts}.npz"
    np.savez_compressed(
        out_path,
        depth_data=depth_data,
        width=width,
        height=height,
        depth_scale=scale,
    )
    print(f"saved: {out_path}")

    pipeline.stop()

if __name__ == "__main__":
    main()
