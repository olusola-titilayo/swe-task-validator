from pathlib import Path

import pytest

from swe_task_validator import review_trajectory
from swe_task_validator.cli import main
from swe_task_validator.trajectory import load_trajectory

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "trajectories"


def rules(steps):
    return [f.rule for f in review_trajectory(steps)]


def test_careful_trajectory_is_clean():
    assert review_trajectory(load_trajectory(EXAMPLES / "careful.jsonl")) == []


def test_careless_trajectory_findings():
    assert rules(load_trajectory(EXAMPLES / "careless.jsonl")) == [
        "blind-edit", "edited-test-file", "submitted-with-failing-tests", "action-after-submit", "unsafe-command",
    ]


def test_submit_without_tests():
    assert rules([{"action": "read", "path": "a.py"}, {"action": "edit", "path": "a.py"}, {"action": "submit"}]) == ["never-ran-tests"]


def test_edit_after_last_green_run_is_a_warning():
    steps = [
        {"action": "read", "path": "a.py"},
        {"action": "run", "command": "pytest", "exit_code": 0},
        {"action": "edit", "path": "a.py"},
        {"action": "submit"},
    ]
    findings = review_trajectory(steps)
    assert [(f.rule, f.severity) for f in findings] == [("untested-final-edit", "warning")]


def test_non_test_commands_do_not_count_as_test_runs():
    steps = [{"action": "run", "command": "ls", "exit_code": 0}, {"action": "submit"}]
    assert rules(steps) == ["never-ran-tests"]


def test_missing_submit_and_unknown_action():
    assert rules([{"action": "dance"}]) == ["unknown-action", "no-submit"]


def test_invalid_jsonl_reports_line(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"action": "read", "path": "a"}\nnot json\n')
    with pytest.raises(ValueError, match="line 2"):
        load_trajectory(p)


def test_cli_exit_codes(capsys):
    assert main(["trajectory", str(EXAMPLES / "careful.jsonl")]) == 0
    assert main(["trajectory", str(EXAMPLES / "careless.jsonl")]) == 1
    assert "3 error(s), 2 warning(s)" in capsys.readouterr().out
