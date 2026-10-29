# Evidence checklist: advanced track

Each module ends with a short list of things to check. Every item is checked from a file, a command's output or a link, never from the agent's account of what it did. That is the point of the track: an agent's "done" is a claim, and the files are the evidence.

**Where to keep it.** Keep each module's evidence in your practice folder, `agents-practice/advanced-evidence/<module>/` (`m6`, `m7`, `m8`), outside your clone and outside any worktree, so removing a worktree keeps it. **Keep it free of secrets:** before you share a bundle with anyone, check that nothing in it holds a token, key, password or personal data. The verifier writes paths as you gave them, so give relative paths if you will share the folder.

## Module 6: Engineer

Page: [module-6-engineer.md](module-6-engineer.md).

- [ ] `baseline/verification.json` says `PASS`, exit 0, with 4 tests.
- [ ] `regression.diff` changes only `src/rice_pest_detector/infer.py`, and only the line the patch changes.
- [ ] `regression/verification.json` says `FAIL`, exit 1, and names `test_preprocess_shape_range_and_no_normalisation` as the only failing test.
- [ ] `stop-hook.txt` shows the Stop hook allowing the stop (or passing) while the regression is in place, and you can say why: it runs `flutter test`, not `pytest`.
- [ ] `unavailable/verification.json` says `UNVERIFIED`, exit 2, with a reason you caused on purpose (for example a misspelt command).
- [ ] `scope.txt` lists only `src/rice_pest_detector/infer.py` and `workshop/advanced/starter/verify.py` as changed, and the summary shows only `infer.py | 1 +`: the agent stayed inside the starter.
- [ ] `restored/verification.json` says `PASS`, exit 0, with 4 tests, after the worktree is back to the original code.
- [ ] `git worktree list` no longer shows the practice worktree, and `git status` in your clone is clean.
- [ ] `reflection.md` answers: which control would have caught this regression (instructions, Stop hook, CI), and why; what `--min-tests 4` protects against.
- [ ] Nothing in the folder holds a token, key, password or personal data.

## Module 7: Orchestrate

- [ ] `records/<success-task>.json` ends `approved`, with at least one `verifier_fail` followed by `repair_done` and `verifier_pass`, and the `approve` entry's actor is `human`.
- [ ] `records/<exhaustion-task>.json` ends `blocked` with `blocked_reason` `retry_exhausted` and `attempts` 3.
- [ ] You tried one event the table does not allow (for example `approve` while verifying, or sending `verifier_pass` by hand): exit code 3, and the record file did not change.
- [ ] Every `verifier_*` entry has actor `verifier` and a verification result; none was typed by you or the agent.
- [ ] `prompts.md` has the prompt you gave the agent at each handoff.
- [ ] `reflection.md` answers: what moved each task forward; what the workflow cannot stop (a hand-edited record, an unauthenticated "human"); when a connected path would be worth its risk.
- [ ] Nothing in the folder holds a token, key, password or personal data.

## Module 8: Automate

- [ ] `links.md` has the issue, pull request and CI run URLs, all under `github.com/<you>/rice-pest-detector`, none under the upstream repository.
- [ ] The pull request's diff changes only files under `tests/` (or the test file the issue names); no threshold, `infer.py` line, contract text or fixture changed.
- [ ] Your local verifier run on the branch says `PASS` before the pull request was opened.
- [ ] The fork's CI run shows the Python tests and Flutter app tests jobs, with their result.
- [ ] `review.md` records your review: what you read, what you checked, and your decision; any merge was done by you, by hand.
- [ ] `reflection.md` answers: which text in the issue or pull request the agent read as instructions; what a malicious issue could ask for; why forks have no secrets and why this exercise needs none.
- [ ] Nothing in the folder holds a token, key, password or personal data.
