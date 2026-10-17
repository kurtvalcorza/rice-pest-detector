---
name: refactor-safely
description: Use when moving code or settings between modules without changing behaviour. Runs the tests first, changes one file at a time, keeps public names working, and re-runs the tests after every step.
---

# Refactor safely

1. Run the tests first (`flutter test` in `app/`, or `pytest` for Python code) and note which fail before you change anything.
2. Before editing, find every place that uses what you are moving. Delegate this search to the `find-callers` sub-agent if it is available.
3. Change one file at a time. After each file, run the tests again.
4. Keep every public name usable from where it was, now pointing at the new location.
5. Do not change behaviour, thresholds or user-facing text. If a test you did not expect to fail turns red, undo that step.
6. Finish with a short summary: files changed, what moved where, and the final test result.

A Stop hook in this repository blocks "done" while the app's tests fail.
