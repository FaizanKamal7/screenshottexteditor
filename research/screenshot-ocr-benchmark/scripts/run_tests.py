"""Run the test suite and record per-file outcomes to pilot/validation/pytest_results.json.

    python scripts/run_tests.py
"""

import json
import os
import sys
from collections import defaultdict

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Collector:
    def __init__(self):
        self.results = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0, "failures": []})

    def pytest_runtest_logreport(self, report):
        path = report.nodeid.split("::")[0]
        r = self.results[path]
        if report.when == "call":
            if report.passed:
                r["passed"] += 1
            elif report.failed:
                r["failed"] += 1
                r["failures"].append(report.nodeid)
        elif report.failed:  # setup/teardown error
            r["failed"] += 1
            r["failures"].append(f"{report.nodeid} ({report.when})")
        elif report.skipped:
            r["skipped"] += 1


def main() -> None:
    os.chdir(ROOT)
    collector = Collector()
    code = pytest.main(["-q", "-p", "no:cacheprovider", "tests"], plugins=[collector])
    out = os.path.join(ROOT, "pilot", "validation", "pytest_results.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(collector.results), f, indent=1)
    sys.exit(code)


if __name__ == "__main__":
    main()
