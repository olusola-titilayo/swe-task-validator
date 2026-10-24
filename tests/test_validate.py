import json
import shutil
from pathlib import Path

import pytest

from swe_task_validator import load_task, validate_task
from swe_task_validator.patches import is_test_path, touched_files

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "tasks" / "merge-intervals"


@pytest.fixture
def task_dir(tmp_path):
    dst = tmp_path / "task"
    shutil.copytree(EXAMPLE, dst)
    return dst


def failed(report):
    return {c.name for c in report.checks if not c.ok}


def edit_meta(task_dir, **changes):
    meta = json.loads((task_dir / "task.json").read_text())
    meta.update(changes)
    (task_dir / "task.json").write_text(json.dumps(meta))


def test_example_task_is_valid(task_dir):
    report = validate_task(load_task(task_dir))
    assert report.ok, report.render()
    assert len(report.checks) == 11


def test_instruction_leaking_a_test_name_is_flagged(task_dir):
    edit_meta(task_dir, instruction="Make test_touching_intervals_merge pass.")
    assert failed(validate_task(load_task(task_dir))) == {"instruction does not leak test names or paths"}


def test_solution_that_edits_tests_is_flagged(task_dir):
    patch = (task_dir / "solution.patch").read_text().replace("intervals/merge.py", "tests/merge.py")
    (task_dir / "solution.patch").write_text(patch)
    assert "solution does not edit tests" in failed(validate_task(load_task(task_dir)))


def test_fail_to_pass_test_that_already_passes_is_flagged(task_dir):
    meta = json.loads((task_dir / "task.json").read_text())
    edit_meta(task_dir,
              fail_to_pass=meta["fail_to_pass"] + ["tests/test_basic.py::test_empty"],
              pass_to_pass=[t for t in meta["pass_to_pass"] if not t.endswith("test_empty")])
    report = validate_task(load_task(task_dir))
    assert failed(report) == {"fail-to-pass tests fail before the fix"}
    assert "test_empty (passed)" in next(c.detail for c in report.checks if not c.ok)


def test_wrong_fix_is_flagged(task_dir):
    # A "fix" that only sorts: touching intervals still are not merged.
    patch = (task_dir / "solution.patch").read_text()
    patch = patch.replace("+        if result and start <= result[-1][1]:", "+        if result and start < result[-1][1]:")
    (task_dir / "solution.patch").write_text(patch)
    report = validate_task(load_task(task_dir))
    assert failed(report) == {"fail-to-pass tests pass after the fix"}


def test_misspelled_test_id_is_reported_missing(task_dir):
    edit_meta(task_dir, pass_to_pass=["tests/test_basic.py::test_does_not_exist"])
    report = validate_task(load_task(task_dir))
    assert any("(missing)" in c.detail for c in report.checks)


def test_overlapping_test_lists_are_flagged(task_dir):
    meta = json.loads((task_dir / "task.json").read_text())
    edit_meta(task_dir, pass_to_pass=meta["pass_to_pass"] + [meta["fail_to_pass"][0]])
    assert "fail-to-pass and pass-to-pass are disjoint" in failed(validate_task(load_task(task_dir)))


def test_patch_that_does_not_apply_stops_early(task_dir):
    (task_dir / "solution.patch").write_text("--- a/nope.py\n+++ b/nope.py\n@@ -1 +1 @@\n-x\n+y\n")
    report = validate_task(load_task(task_dir))
    assert report.checks[-1].name == "solution patch applies" and not report.checks[-1].ok


def test_load_task_requires_keys_and_files(task_dir):
    (task_dir / "task.json").write_text("{}")
    with pytest.raises(ValueError, match="instruction"):
        load_task(task_dir)
    shutil.rmtree(task_dir)
    (task_dir).mkdir()
    (task_dir / "task.json").write_text('{"instruction": "", "fail_to_pass": [], "pass_to_pass": []}')
    with pytest.raises(FileNotFoundError):
        load_task(task_dir)


def test_patch_helpers():
    patch = "--- /dev/null\n+++ b/tests/test_x.py\n@@\n--- a/src/a.py\n+++ b/src/a.py\n"
    assert touched_files(patch) == ["tests/test_x.py", "src/a.py"]
    assert is_test_path("tests/test_x.py") and is_test_path("pkg/foo_test.py")
    assert not is_test_path("src/testing_utils.py")
