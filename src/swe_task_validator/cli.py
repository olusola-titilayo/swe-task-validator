"""swe-task-validator: check a task directory, or review an agent trajectory.

    swe-task-validator task  examples/tasks/merge-intervals
    swe-task-validator trajectory examples/trajectories/careless.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .task import load_task
from .trajectory import load_trajectory, review_trajectory
from .validate import validate_task


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="swe-task-validator", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("task", help="validate a task directory")
    t.add_argument("path", type=Path)
    t.add_argument("--timeout", type=float, default=120)
    r = sub.add_parser("trajectory", help="review an agent trajectory (JSON Lines)")
    r.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    if args.command == "task":
        report = validate_task(load_task(args.path), args.timeout)
        print(report.render())
        return 0 if report.ok else 1

    findings = review_trajectory(load_trajectory(args.path))
    for f in findings:
        print(f)
    errors = sum(f.severity == "error" for f in findings)
    print(f"{errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
