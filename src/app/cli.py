from src.acquisition.orbbec import OrbbecSource
from src.core.pipeline import Pipeline

def main():
    src = OrbbecSource()
    pipe = Pipeline(dict())

    while True:
        frame = src.read()
        res = pipe.process(frame)

        print(res)

if __name__=="__main__":
    main()