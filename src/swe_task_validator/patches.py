"""Minimal helpers for unified diffs."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List

_HEADER = re.compile(r"^\+\+\+ (?:b/)?(\S+)", re.MULTILINE)


def touched_files(patch: str) -> List[str]:
    """Paths a unified diff writes to (from its ``+++`` lines), excluding /dev/null."""
    return [p for p in _HEADER.findall(patch) if p != "/dev/null"]


def is_test_path(path: str) -> bool:
    name = Path(path).name
    parts = Path(path).parts
    return "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py")


def apply_patch(patch: str, cwd: Path) -> None:
    """Apply a unified diff with ``git apply`` (works outside a git repository)."""
    if not patch.strip():
        return
    proc = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        input=patch, text=True, capture_output=True, cwd=cwd,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"patch did not apply: {proc.stderr.strip()}")
