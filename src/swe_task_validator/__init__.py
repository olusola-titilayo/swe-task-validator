"""Validate SWE-bench-style coding tasks and review agent trajectories."""

from .task import Task, load_task
from .validate import CheckResult, ValidationReport, validate_task
from .trajectory import Finding, review_trajectory

__all__ = ["Task", "load_task", "CheckResult", "ValidationReport", "validate_task", "Finding", "review_trajectory"]
__version__ = "0.1.0"
