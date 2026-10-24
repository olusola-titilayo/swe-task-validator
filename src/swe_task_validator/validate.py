"""Check that a task is well-formed, fair and actually tests the fix."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from .patches import apply_patch, is_test_path, touched_files
from .task import Task

MIN_FAIL_TO_PASS = 1


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ValidationReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(CheckResult(name, ok, detail))

    def render(self) -> str:
        lines = [f"{'VALID' if self.ok else 'INVALID'} ({sum(c.ok for c in self.checks)}/{len(self.checks)} checks)"]
        for c in self.checks:
            lines.append(f"  {'✓' if c.ok else '✗'} {c.name}" + (f": {c.detail}" if c.detail else ""))
        return "\n".join(lines)


def run_tests(workdir: Path, test_ids: Iterable[str], timeout: float = 120) -> Dict[str, str]:
    """Run pytest node ids in ``workdir`` and return {test_id: "passed"|"failed"|"error"|"missing"}."""
    test_ids = list(test_ids)
    if not test_ids:
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", *test_ids],
            cwd=workdir, capture_output=True, text=True, timeout=timeout, env=env,
        )
        outcomes: Dict[str, str] = {}
        if report.exists():
            for case in ET.parse(report).getroot().iter("testcase"):
                file = case.get("file") or case.get("classname", "").replace(".", "/") + ".py"
                node = f"{file}::{case.get('name')}"
                if case.find("failure") is not None:
                    outcomes[node] = "failed"
                elif case.find("error") is not None:
                    outcomes[node] = "error"
                elif case.find("skipped") is not None:
                    outcomes[node] = "skipped"
                else:
                    outcomes[node] = "passed"
    return {t: outcomes.get(t, "missing") for t in test_ids}


def _leaks(instruction: str, task: Task) -> List[str]:
    """Test names or test file paths that appear verbatim in the instruction."""
    text = instruction.lower()
    leaked = []
    for test_id in task.fail_to_pass + task.pass_to_pass:
        path, _, name = test_id.partition("::")
        for token in (path, name):
            if token and re.search(rf"(?<![\w/]){re.escape(token.lower())}(?![\w])", text):
                leaked.append(token)
    for path in touched_files(task.tests_patch):
        if path.lower() in text:
            leaked.append(path)
    return sorted(set(leaked))


def validate_task(task: Task, timeout: float = 120) -> ValidationReport:
    report = ValidationReport()

    # Static checks ---------------------------------------------------------
    report.add("has fail-to-pass tests", len(task.fail_to_pass) >= MIN_FAIL_TO_PASS,
               f"{len(task.fail_to_pass)} listed")
    overlap = sorted(set(task.fail_to_pass) & set(task.pass_to_pass))
    report.add("fail-to-pass and pass-to-pass are disjoint", not overlap, ", ".join(overlap))

    sol_files = touched_files(task.solution_patch)
    test_edits = [p for p in sol_files if is_test_path(p)]
    report.add("solution does not edit tests", not test_edits, ", ".join(test_edits))

    collisions = sorted(set(sol_files) & set(touched_files(task.tests_patch)))
    report.add("solution and tests patch touch different files", not collisions, ", ".join(collisions))

    leaked = _leaks(task.instruction, task)
    report.add("instruction does not leak test names or paths", not leaked, ", ".join(leaked))

    # Behavioural checks ----------------------------------------------------
    all_tests = task.fail_to_pass + task.pass_to_pass
    with tempfile.TemporaryDirectory() as tmp:
        base, fixed = Path(tmp, "base"), Path(tmp, "fixed")
        shutil.copytree(task.repo, base)
        try:
            apply_patch(task.tests_patch, base)
        except RuntimeError as exc:
            report.add("tests patch applies to base", False, str(exc))
            return report
        report.add("tests patch applies to base", True)
        shutil.copytree(base, fixed)
        try:
            apply_patch(task.solution_patch, fixed)
        except RuntimeError as exc:
            report.add("solution patch applies", False, str(exc))
            return report
        report.add("solution patch applies", True)

        before = run_tests(base, all_tests, timeout)
        after = run_tests(fixed, all_tests, timeout)

    def bad(results: Dict[str, str], tests: List[str], want: str) -> List[str]:
        return [f"{t} ({results[t]})" for t in tests if results[t] != want]

    report.add("fail-to-pass tests fail before the fix", not bad(before, task.fail_to_pass, "failed"),
               "; ".join(bad(before, task.fail_to_pass, "failed")))
    report.add("fail-to-pass tests pass after the fix", not bad(after, task.fail_to_pass, "passed"),
               "; ".join(bad(after, task.fail_to_pass, "passed")))
    report.add("pass-to-pass tests pass before the fix", not bad(before, task.pass_to_pass, "passed"),
               "; ".join(bad(before, task.pass_to_pass, "passed")))
    report.add("pass-to-pass tests pass after the fix", not bad(after, task.pass_to_pass, "passed"),
               "; ".join(bad(after, task.pass_to_pass, "passed")))
    return report
