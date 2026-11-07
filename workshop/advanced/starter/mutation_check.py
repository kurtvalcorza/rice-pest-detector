"""STARTER: could the tests have failed? Fill in the TODOs, test-first.

Point the track's tests at this file and watch them fail, then make them pass one at a time:

    RPD_WORKSHOP_IMPL=starter python -m pytest workshop/advanced/tests        # macOS, Linux
    $env:RPD_WORKSHOP_IMPL="starter"; python -m pytest workshop/advanced/tests  # Windows PowerShell

Usage, once finished (the same as the reference in ``workshop/advanced/solutions/mutation_check.py``):
    python mutation_check.py --mutants workshop/advanced/mutants.json --evidence DIR -- VERIFY_COMMAND [ARG ...]

Plant one bug per requirement and judge each by the verifier's exit code: 1 is ``checked``, 0 is
``unguarded``, anything else is ``unverified``. Exit 0 when all are checked, 1 when any is unguarded and
none unverified, 2 when the run could not judge. The tables are in
specs/004-advanced-workshop/contracts/mutation-check.md. Standard library only.
"""

import sys

CHECKED, UNGUARDED, UNVERIFIED = "checked", "unguarded", "unverified"
SCHEMA = 1


class CannotJudge(Exception):
    """Exit 2: the run stops here and writes no report."""


def label_for(exit_code):
    """Return the label for one mutant from the verify command's exit code (None if it never started)."""
    raise NotImplementedError("label_for: TODO")


def overall_exit(labels):
    """Return 0 if every label is checked, 1 if any is unguarded and none unverified, else 2."""
    raise NotImplementedError("overall_exit: TODO")


def tree_is_clean():
    """True when ``git status --porcelain`` shows nothing."""
    raise NotImplementedError("tree_is_clean: TODO")


def check_worktree():
    """Raise CannotJudge unless the current folder is the top of a clean linked worktree.

    In a linked worktree, ``git rev-parse --git-dir`` and ``--git-common-dir`` differ.
    """
    # TODO: why refuse the main clone at all? What happens to it if the run is killed part-way?
    raise NotImplementedError("check_worktree: TODO")


def load_mutants(path):
    """Return (requirements, assumed, patches folder); CannotJudge for anything that is not usable.

    Patches sit in ``patches/`` beside the mutants file. No requirements, a repeated ID or a missing
    patch all stop the run here.
    """
    raise NotImplementedError("load_mutants: TODO")


def run_verify(command):
    """Run the verify command without a shell; return (exit code or None, its stated reason).

    The reason is the text in brackets on the verifier's last ``RESULT:`` line. Clear ``__pycache__`` under
    ``src`` first and set ``PYTHONDONTWRITEBYTECODE=1``: a planted bug can keep the file's size, and a run can
    fit in one second, so Python could otherwise reuse a stale .pyc and run the wrong code.
    """
    raise NotImplementedError("run_verify: TODO")


def run_mutant(requirement, patches, command):
    """Apply one patch, run the verify command, reverse the patch, confirm the tree is clean.

    Return {id, patch, label, verifier_exit, reason}. A patch that cannot be applied or reversed
    raises CannotJudge.
    """
    # TODO: `git apply`, `git apply -R`. The reverse belongs in a `finally`.
    raise NotImplementedError("run_mutant: TODO")


def run_check(mutants, evidence, command):
    """Steps 1-4 of the contract: refuse, baseline, one run per mutant, write mutation-report.json.

    The baseline must exit 0, or the run stops: a check that fails before any bug is planted proves
    nothing. The report holds schema, commit, baseline, requirements, assumed and counts.
    """
    raise NotImplementedError("run_check: TODO")


def main(argv=None):
    """Parse the arguments, call run_check, print one line per requirement and a last ``RESULT:`` line.

    Any CannotJudge becomes exit 2 with no report.
    """
    # TODO: argparse for --mutants and --evidence; everything after "--" is the verify command.
    raise NotImplementedError("main: TODO")


if __name__ == "__main__":
    sys.exit(main())
