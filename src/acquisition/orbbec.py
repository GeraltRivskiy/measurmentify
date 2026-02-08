from src.app_types import FrameDepth, Intrinsics
import numpy as np
from pyorbbecsdk import Config
from pyorbbecsdk import OBSensorType
from pyorbbecsdk import Pipeline


class OrbbecSource:
    def __init__(self):
        self.config = Config()
        self.pipeline = Pipeline()
        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
            assert profile_list is not None
            depth_profile = profile_list.get_default_video_stream_profile()
            assert depth_profile is not None
            print("depth profile: ", depth_profile)
            self.depth_intrinsics = depth_profile.get_intrinsic()    
            self.config.enable_stream(depth_profile)
        except Exception as e:
            print(e)
            return
        self.pipeline.start(self.config)
        

    def read(self):
        frames = self.pipeline.wait_for_frames(500)
        if frames is None:
            raise Exception("Frame was not obtained")
        depth_frame = frames.get_depth_frame()
        if depth_frame is None:
            raise Exception("Depth frame was not obtained")
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        scale = depth_frame.get_depth_scale()

        depth_data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16)
        depth_data = depth_data.reshape((height, width))
        
        intrinsics = Intrinsics(self.depth_intrinsics.fx,
                                self.depth_intrinsics.fy,
                                self.depth_intrinsics.cx,
                                self.depth_intrinsics.cy,
                                self.depth_intrinsics.width,
                                self.depth_intrinsics.height)
        
        return FrameDepth(depth = depth_data,
                          intrinsics=intrinsics, depth_scale=1.0)
        
    