from src.app_types import PointCloud, Intrinsics
import numpy as np
from pyorbbecsdk import Config, PointCloudFilter, OBFormat, Frame
from pyorbbecsdk import OBSensorType, OBPropertyID
from pyorbbecsdk import Pipeline
import open3d as o3d

def convert_to_o3d_point_cloud(points, colors=None):
    """
    Converts numpy arrays of points and colors (if provided) into an Open3D point cloud object.
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors / 255.0)  # Assuming colors are in [0, 255]
    return pcd

class OrbbecSource:
    def __init__(self):
        self.config = Config()
        self.pipeline = Pipeline()
        device = self.pipeline.get_device()
        device.set_bool_property(OBPropertyID.OB_PROP_DEPTH_SOFT_FILTER_BOOL, False)
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
        self.camera_param = self.pipeline.get_camera_param()
        # self.point_cloud_filter = PointCloudFilter()
        # self.point_cloud_filter.set_camera_param(camera_param)
        # self.point_cloud_filter.set_create_point_format(OBFormat.POINT)

    def read(self):
        frames = self.pipeline.wait_for_frames(10000)
        if frames is None:
            raise Exception("Frame was not obtained")
        
        points = frames.get_point_cloud(self.camera_param)
        points_o3d = convert_to_o3d_point_cloud(np.array(points))
        
        
        intrinsics = Intrinsics(self.depth_intrinsics.fx,
                                self.depth_intrinsics.fy,
                                self.depth_intrinsics.cx,
                                self.depth_intrinsics.cy,
                                self.depth_intrinsics.width,
                                self.depth_intrinsics.height)
        
        return PointCloud(points=points_o3d,
                          intrinsics=intrinsics, depth_scale=1.0)
        
    