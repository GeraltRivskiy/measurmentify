from src.app_types import PointCloud, DimsResult
import open3d as o3d



class Pipeline:
    def __init__(self, config: dict):
        self.cfg = config

    def process(self, frame: PointCloud):


        return DimsResult(0.1, 0.2, 0.3, 'm', 'obb')