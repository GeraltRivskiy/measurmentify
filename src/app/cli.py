import argparse

from src.acquisition.orbbec import OrbbecSource
from src.acquisition.replay import ReplaySource
from src.core.pipeline import Pipeline

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true", help="Replay depth frames from .npz files")
    parser.add_argument("--data-dir", default="data", help="Directory with .npz files for replay")
    parser.add_argument("--config", default="configs/config.yaml", help="Config with camera intrinsics")
    args = parser.parse_args()

    if args.replay:
        src = ReplaySource(data_dir=args.data_dir, config_path=args.config)
    else:
        src = OrbbecSource()
    pipe = Pipeline(dict())

    while True:
        frame = src.read()
        res = pipe.process(frame)

        print(res)

if __name__ == "__main__":
    main()
