"""Task format.

A task is a directory containing::

    task.json        {"instruction": str, "fail_to_pass": [test ids], "pass_to_pass": [test ids]}
    repo/            the codebase at the base commit
    solution.patch   the reference ("golden") fix, as a unified diff against repo/
    tests.patch      the hidden tests, as a unified diff against repo/

Test ids are pytest node ids such as ``tests/test_merge.py::test_touching``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class Task:
    root: Path
    instruction: str
    fail_to_pass: List[str]
    pass_to_pass: List[str]

    @property
    def repo(self) -> Path:
        return self.root / "repo"

    @property
    def solution_patch(self) -> str:
        return (self.root / "solution.patch").read_text()

    @property
    def tests_patch(self) -> str:
        return (self.root / "tests.patch").read_text()


def load_task(root: Path) -> Task:
    root = Path(root)
    meta = json.loads((root / "task.json").read_text())
    missing = [k for k in ("instruction", "fail_to_pass", "pass_to_pass") if k not in meta]
    if missing:
        raise ValueError(f"task.json missing keys: {', '.join(missing)}")
    for name in ("repo", "solution.patch", "tests.patch"):
        if not (root / name).exists():
            raise FileNotFoundError(f"task is missing {name}")
    return Task(root, meta["instruction"], list(meta["fail_to_pass"]), list(meta["pass_to_pass"]))
