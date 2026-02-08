import numpy as np
from pyorbbecsdk import Config, PointCloudFilter, OBFormat, Frame
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
        self.point_cloud_filter = PointCloudFilter()
        self.point_cloud_filter.set_create_point_format(OBFormat.POINT)

    def read(self):
        frames = self.pipeline.wait_for_frames(500)
        if frames is None:
            raise Exception("Frame was not obtained")
        point_cloud_frame = self.point_cloud_filter.process(frames)
        print(point_cloud_frame)
        
    
source = OrbbecSource()
frame = source.read()
