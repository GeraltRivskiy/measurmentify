from src.app_types import FrameDepth, DimsResult

class Pipeline:
    def __init__(self, config: dict):
        self.cfg = config

    def process(self, frame: FrameDepth):


        return DimsResult(0.1, 0.2, 0.3, 'm', 'obb')