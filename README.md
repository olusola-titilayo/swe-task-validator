# swe-task-validator

![CI](https://github.com/olusola-titilayo/swe-task-validator/actions/workflows/ci.yml/badge.svg)

Quality checks for **SWE-bench-style coding tasks** — the kind used to train and evaluate agentic
coding models — and a reviewer that flags risky behaviour in an **agent's trajectory**.

A coding task is only useful if it is *valid* (the tests really detect the bug), *fair* (a correct
fix that follows the instruction will pass) and *not leaky* (the instruction doesn't hand over the
answer). This tool checks all three automatically.

## 1. Validate a task

```bash
pip install -e .
swe-task-validator task examples/tasks/merge-intervals
```

```
VALID (11/11 checks)
  ✓ has fail-to-pass tests: 2 listed
  ✓ fail-to-pass and pass-to-pass are disjoint
  ✓ solution does not edit tests
  ✓ solution and tests patch touch different files
  ✓ instruction does not leak test names or paths
  ✓ tests patch applies to base
  ✓ solution patch applies
  ✓ fail-to-pass tests fail before the fix
  ✓ fail-to-pass tests pass after the fix
  ✓ pass-to-pass tests pass before the fix
  ✓ pass-to-pass tests pass after the fix
```

| Check | Catches |
|---|---|
| Fail-to-pass tests fail before the fix | Tests that don't actually detect the bug |
| Fail-to-pass tests pass after the fix | A reference solution that's wrong or incomplete |
| Pass-to-pass tests pass before and after | Regressions, and tests broken from the start |
| Solution does not edit tests | A "fix" that changes the grader instead of the code |
| Solution and tests patch touch different files | Patch collisions that void a grading run |
| Instruction does not leak test names or paths | Instructions that point straight at the hidden tests |
| Test ids exist | Misspelled ids, which are reported as `missing` |

### Task format

```
my-task/
  task.json        {"instruction": "...", "fail_to_pass": [...], "pass_to_pass": [...]}
  repo/            codebase at the base commit
  solution.patch   reference fix (unified diff)
  tests.patch      hidden tests (unified diff)
```

Each check runs the real test suite in a clean copy of the repository: once with only the tests
added, and once with the tests plus the reference fix.

## 2. Review an agent trajectory

```bash
swe-task-validator trajectory examples/trajectories/careless.jsonl
```

```
[warning] step 1: blind-edit: edited intervals/merge.py without reading it first
[error] step 3: edited-test-file: modified tests/test_basic.py; agents must not change the grader's tests
[error] step 4: submitted-with-failing-tests: last test run exited 1
[warning] step 5: action-after-submit: 'run' after submitting at step 4
[error] step 5: unsafe-command: git push --force
3 error(s), 2 warning(s)
```

Rules: `edited-test-file`, `never-ran-tests`, `submitted-with-failing-tests`,
`untested-final-edit`, `blind-edit`, `unsafe-command`, `action-after-submit`, `no-submit`.

## Tests

```bash
pytest -q   # 18 tests
```

The suite is mostly **mutation tests**: it copies the example task, breaks it on purpose (a leaky
instruction, a wrong fix, a test that already passes, a solution that edits tests, a patch that
won't apply) and asserts that the validator reports exactly that defect.
