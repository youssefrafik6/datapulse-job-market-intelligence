import argparse
from pathlib import Path

from datapulse.modeling import train

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and evaluate the advertised-salary model.")
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    report = train(args.database)
    print(report["selected"], report["test"])
