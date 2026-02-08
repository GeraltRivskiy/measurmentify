import argparse

from src.core.pipeline import Pipeline
from src.config import DimsAlgoConfig

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true", help="Replay depth frames from .npz files")
    parser.add_argument("--data-dir", default="data", help="Directory with .npz files for replay")
    parser.add_argument("--config", default="configs/config.yaml", help="Config with camera intrinsics")
    args = parser.parse_args()

    if args.replay:
        from src.acquisition.replay import ReplaySource
        src = ReplaySource(data_dir=args.data_dir, config_path=args.config, loop=False)
    else:
        from src.acquisition.orbbec import OrbbecSource
        src = OrbbecSource()
    pipe = Pipeline(DimsAlgoConfig)

    while True:
        frame = src.read()
        res = pipe.process(frame)

        print(f'Length: {res[0]}, Width: {res[1]}, Height: {res[2]}')

if __name__ == "__main__":
    main()
