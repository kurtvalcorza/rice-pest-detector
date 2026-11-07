"""Could the tests have failed? Plant one known bug per requirement and see if the verifier rejects it.

Usage (from the top of a clean, linked Git worktree):
    python mutation_check.py --mutants workshop/advanced/mutants.json --evidence DIR -- VERIFY_COMMAND [ARG ...]

VERIFY_COMMAND is the same ``verify.py`` call Module 6 built, run without a shell. The check runs it once
on the unchanged code, then once per mutant: apply the patch, run, reverse the patch, confirm the tree is
clean. The verifier's exit code labels the requirement, using the table in
``specs/004-advanced-workshop/contracts/mutation-check.md``:

    checked     verifier exit 1     a test failed when this requirement was broken
    unguarded   verifier exit 0     the requirement was broken and every test still passed
    unverified  anything else       the check could not run; nothing is known

Exit codes: 0 every requirement checked; 1 at least one unguarded, none unverified; 2 could not judge
(usage, not a clean linked worktree, baseline not passing, a patch problem, or any unverified row).

``checked`` means one planted bug was caught, not that the requirement holds for every input: this is
testing, not proof. A requirement nobody wrote down has no mutant. Standard library only.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHECKED, UNGUARDED, UNVERIFIED = "checked", "unguarded", "unverified"
SCHEMA = 1
RESULT_LINE = re.compile(r"^RESULT: (PASS|FAIL|UNVERIFIED) \((.*)\) evidence=", re.MULTILINE)
DIRTY_ADVICE = "the worktree may hold a planted bug: delete it, do not repair it"


class CannotJudge(Exception):
    """Exit 2: the run stops here and writes no report."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CannotJudge(f"invalid arguments: {message}")


def label_for(exit_code):
    """The verdict table: only exit 1 is a kill and only exit 0 a survivor; nothing else is judged."""
    return {1: CHECKED, 0: UNGUARDED}.get(exit_code, UNVERIFIED)


def overall_exit(labels):
    if UNVERIFIED in labels:
        return 2
    return 1 if UNGUARDED in labels else 0


def _git(*args):
    git = shutil.which("git")
    if git is None:
        raise CannotJudge("git was not found")
    return subprocess.run([git, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=False)


def tree_is_clean():
    done = _git("status", "--porcelain")
    return done.returncode == 0 and done.stdout.strip() == ""


def check_worktree():
    """Bugs are never planted in a learner's main clone: refuse anywhere but the top of a clean linked worktree."""
    done = _git("rev-parse", "--git-dir", "--git-common-dir", "--show-cdup")
    if done.returncode != 0:
        raise CannotJudge("this folder is not in a Git worktree")
    git_dir, common_dir, *cdup = done.stdout.splitlines()
    if Path(git_dir).resolve() == Path(common_dir).resolve():
        raise CannotJudge("this is the main clone: run this in a linked worktree (git worktree add)")
    if cdup and cdup[0]:
        raise CannotJudge("run this from the top folder of the linked worktree")
    if not tree_is_clean():
        raise CannotJudge("the worktree is not clean: commit or remove your changes first")


def load_mutants(path):
    """Return (requirements, assumed, patches folder); CannotJudge for anything that is not usable."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        requirements, assumed = data["requirements"], data["assumed"]
        ids = [entry["id"] for entry in requirements]
        names = [entry["patch"] for entry in requirements]
        items = [{"item": entry["item"], "reason": entry["reason"]} for entry in assumed]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CannotJudge(f"cannot read the mutants file {path}: {type(exc).__name__}: {exc}") from None
    if not ids:
        raise CannotJudge("the mutants file lists no requirements")
    if len(set(ids)) != len(ids):
        raise CannotJudge("the mutants file lists a requirement twice")
    patches = path.parent / "patches"
    for name in names:
        if Path(name).name != name or not (patches / name).is_file():
            raise CannotJudge(f"no such patch in {patches}: {name}")
    return requirements, items, patches


def run_verify(command):
    """Run the verify command without a shell; return (exit code or None, its stated reason).

    Python trusts cached bytecode when the source's size and whole-second time match. A planted bug can keep the
    size, and a whole cycle can fit in one second, so a stale .pyc could run the wrong code. Clear the cache and
    write none.
    """
    for cache in Path("src").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    program = shutil.which(command[0])
    if program is None:
        return None, f"command not found: {command[0]}"
    try:
        done = subprocess.run([program, *command[1:]], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                              check=False)
    except OSError as exc:
        return None, f"the command could not start: {exc.strerror or exc}"
    lines = RESULT_LINE.findall(done.stdout.decode("utf-8", errors="replace"))
    return done.returncode, lines[-1][1] if lines else f"the command exited {done.returncode}"


def run_mutant(requirement, patches, command):
    """Apply one patch, run the verify command, reverse the patch; return the report row."""
    name = requirement["patch"]
    patch = str((patches / name).resolve())
    applied = _git("apply", patch)
    if applied.returncode != 0:
        raise CannotJudge(f"{name} does not apply: {applied.stderr.strip()}")
    try:
        exit_code, reason = run_verify(command)
    finally:  # also on Ctrl-C: never leave the bug behind if it can be helped
        reversed_ = _git("apply", "-R", patch)
    if reversed_.returncode != 0:
        raise CannotJudge(f"{name} does not reverse: {reversed_.stderr.strip()}; {DIRTY_ADVICE}")
    if not tree_is_clean():
        raise CannotJudge(f"the tree is not clean after {name}: keep evidence outside the worktree; {DIRTY_ADVICE}")
    return {"id": requirement["id"], "patch": name, "label": label_for(exit_code), "verifier_exit": exit_code,
            "reason": reason}


def run_check(mutants, evidence, command):
    """Steps 1-4 of the contract. Returns the report; any CannotJudge leaves no report."""
    if not command:
        raise CannotJudge("invalid arguments: no verify command was given after --")
    requirements, assumed, patches = load_mutants(mutants)
    check_worktree()
    commit = _git("rev-parse", "HEAD").stdout.strip()

    exit_code, reason = run_verify(command)
    if exit_code != 0:
        raise CannotJudge(f"the baseline does not pass (exit {exit_code}: {reason}), so a kill would prove nothing")
    if not tree_is_clean():
        raise CannotJudge("the tree is not clean after the baseline: keep evidence outside the worktree")
    print(f"baseline    PASS ({reason})")

    rows = []
    for requirement in requirements:
        rows.append(run_mutant(requirement, patches, command))
        row = rows[-1]
        print(f"{row['label']:<11} {row['id']} (verifier exit {row['verifier_exit']}: {row['reason']})", flush=True)
    report = {"schema": SCHEMA, "commit": commit,
              "baseline": {"exit_code": 0, "result": "PASS", "reason": reason}, "requirements": rows,
              "assumed": assumed,
              "counts": {label: sum(row["label"] == label for row in rows)
                         for label in (CHECKED, UNGUARDED, UNVERIFIED)}}
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "mutation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def _parse(argv):
    if "--" in argv:
        split = argv.index("--")
        options, command = argv[:split], argv[split + 1:]
    else:
        options, command = argv, []
    parser = _Parser(prog="mutation_check.py", description=__doc__.splitlines()[0])
    parser.add_argument("--mutants", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    return parser.parse_args(options), command


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args, command = _parse(argv)
        report = run_check(args.mutants, args.evidence, command)
    except CannotJudge as exc:
        print(f"RESULT: NOT JUDGED ({exc})")
        return 2
    counts = report["counts"]
    print(f"RESULT: {counts[CHECKED]} checked, {counts[UNGUARDED]} unguarded, {counts[UNVERIFIED]} unverified "
          f"(a caught bug is testing, not proof) report={Path(args.evidence) / 'mutation-report.json'}")
    return overall_exit([row["label"] for row in report["requirements"]])


if __name__ == "__main__":
    sys.exit(main())
