import json

from datapulse.modeling import METRICS

if __name__ == "__main__":
    report = json.loads(METRICS.read_text())
    print(json.dumps(report, indent=2))
