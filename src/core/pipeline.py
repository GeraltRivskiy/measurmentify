from src.app_types import FramePointCloud, DimsResult

class Pipeline:
    def __init__(self, config: dict):
        self.cfg = config

    def process(self, frame: FramePointCloud):


        return DimsResult(0.1, 0.2, 0.3, 'm', 'obb')