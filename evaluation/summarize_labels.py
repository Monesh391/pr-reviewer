"""Read your tp/fp labels in real_pr_findings.csv and print precision."""
import csv
from pathlib import Path

path = Path(__file__).parent / "real_pr_findings.csv"
tp = fp = 0
with open(path, encoding="utf-8") as fh:
    for row in csv.DictReader(fh):
        verdict = row["verdict"].strip().lower()
        tp += verdict == "tp"
        fp += verdict == "fp"
labeled = tp + fp
print(f"Labeled findings: {labeled}  (true positives: {tp}, false alarms: {fp})")
if labeled:
    print(f"Precision on real PRs: {tp / labeled:.1%}")
