"""mutation_check.py: every row of the verdict and exit-code tables, on a throwaway Git repository.

The verify command here is a fake: it reads which bug is planted in ``target.txt`` and exits with the
code the test chose for it. Each planted bug is a one-line patch made with ``git diff``, as the real
ones are. Nothing here touches this repository's code.
"""

import json
import subprocess
import sys
import textwrap

import pytest

FAKE_VERIFY = textwrap.dedent("""
    import json, pathlib, sys
    plan = json.loads(pathlib.Path(sys.argv[1]).read_text())
    value = pathlib.Path("target.txt").read_text().strip()
    with open(sys.argv[2], "a") as log:
        log.write(value + "\\n")
    action = plan["actions"].get(value)
    if action == "stray":
        pathlib.Path("stray.txt").write_text("left behind")
    elif action == "rewrite":
        pathlib.Path("target.txt").write_text("somebody else was here\\n")
    code = plan["codes"].get(value, 0)
    print("pytest noise")
    print("RESULT: %s (reason for %s) evidence=ev" % ({0: "PASS", 1: "FAIL"}.get(code, "UNVERIFIED"), value))
    sys.exit(code)
""")


def _git(cwd, *args):
    done = subprocess.run(["git", "-c", "user.name=Workshop", "-c", "user.email=workshop@example.invalid", *args],
                          cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout


class Practice:
    """A clone, a linked worktree on a practice branch, patches and a fake verifier."""

    def __init__(self, tmp_path, script):
        self.script, self.tmp = script, tmp_path
        self.clone, self.worktree = tmp_path / "clone", tmp_path / "practice worktree"
        self.track = tmp_path / "track"
        self.mutants, self.evidence = self.track / "mutants.json", tmp_path / "evidence"
        self.plan, self.log = tmp_path / "plan.json", tmp_path / "verify.log"
        (self.track / "patches").mkdir(parents=True)
        self.clone.mkdir()
        target = self.clone / "target.txt"
        _git(self.clone, "init", "-q")
        target.write_text("value=0\n", encoding="utf-8")
        _git(self.clone, "add", "target.txt")
        _git(self.clone, "commit", "-q", "-m", "start")
        for number in range(1, 7):
            target.write_text(f"value={number}\n", encoding="utf-8")
            patch = self.track / "patches" / f"bug{number}.patch"
            patch.write_text(_git(self.clone, "diff"), encoding="utf-8", newline="\n")
            _git(self.clone, "checkout", "-q", "--", "target.txt")
        _git(self.clone, "worktree", "add", "-q", str(self.worktree), "-b", "practice")
        (tmp_path / "fake_verify.py").write_text(FAKE_VERIFY, encoding="utf-8")
        self.write_mutants(1, 2, 3)

    def write_mutants(self, *numbers):
        data = {"schema": 1,
                "requirements": [{"id": f"req-{n}", "patch": f"bug{n}.patch", "bug": f"bug {n}"} for n in numbers],
                "assumed": [{"item": "the weights", "reason": "no test here loads them"}]}
        self.mutants.write_text(json.dumps(data), encoding="utf-8")

    def run(self, baseline=0, codes=None, actions=None, cwd=None, command=None, options=None):
        """Run the check; ``codes`` maps a bug number to the verify command's exit code."""
        table = {"value=0": baseline, **{f"value={n}": code for n, code in (codes or {}).items()}}
        plan = {"codes": table, "actions": {f"value={n}": action for n, action in (actions or {}).items()}}
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        if command is None:
            command = [sys.executable, str(self.tmp / "fake_verify.py"), str(self.plan), str(self.log)]
        if options is None:
            options = ["--mutants", str(self.mutants), "--evidence", str(self.evidence)]
        return subprocess.run([sys.executable, str(self.script), *options, "--", *command], cwd=cwd or self.worktree,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                              check=False)

    def report(self):
        return json.loads((self.evidence / "mutation-report.json").read_text(encoding="utf-8"))

    def has_report(self):
        return (self.evidence / "mutation-report.json").exists()

    def seen(self):
        return self.log.read_text(encoding="utf-8").split() if self.log.exists() else []

    def clean(self):
        return _git(self.worktree, "status", "--porcelain") == ""


@pytest.fixture
def practice(tmp_path, mutation_check_path):
    return Practice(tmp_path, mutation_check_path)


@pytest.mark.parametrize(("code", "label"), [(1, "checked"), (0, "unguarded"), (2, "unverified"), (7, "unverified"),
                                             (-9, "unverified"), (None, "unverified")])
def test_the_verdict_table(code, label, mutation_check_mod):
    assert mutation_check_mod.label_for(code) == label


@pytest.mark.parametrize(("labels", "code"), [
    (["checked", "checked"], 0),
    (["checked", "unguarded"], 1),
    (["unguarded", "unguarded"], 1),
    (["checked", "unverified"], 2),
    (["unguarded", "unverified"], 2),
    (["unverified"], 2),
])
def test_the_exit_code_table(labels, code, mutation_check_mod):
    assert mutation_check_mod.overall_exit(labels) == code


def test_every_bug_caught_exits_0_and_labels_each_checked(practice):
    done = practice.run(codes={1: 1, 2: 1, 3: 1})
    assert done.returncode == 0, done.stdout + done.stderr
    report = practice.report()
    assert [r["label"] for r in report["requirements"]] == ["checked"] * 3
    assert report["counts"] == {"checked": 3, "unguarded": 0, "unverified": 0}


def test_a_surviving_bug_exits_1_and_is_unguarded(practice):
    done = practice.run(codes={1: 1, 2: 0, 3: 1})
    assert done.returncode == 1
    row = practice.report()["requirements"][1]
    assert (row["id"], row["label"], row["verifier_exit"]) == ("req-2", "unguarded", 0)
    assert practice.report()["counts"] == {"checked": 2, "unguarded": 1, "unverified": 0}


@pytest.mark.parametrize("code", [2, 7])
def test_an_uncheckable_bug_exits_2_is_unverified_and_the_run_finishes(code, practice):
    done = practice.run(codes={1: 0, 2: code, 3: 1})
    assert done.returncode == 2
    report = practice.report()
    assert [r["label"] for r in report["requirements"]] == ["unguarded", "unverified", "checked"]
    assert report["requirements"][1]["verifier_exit"] == code
    assert report["counts"] == {"checked": 1, "unguarded": 1, "unverified": 1}


def test_the_report_holds_the_contracts_fields(practice):
    practice.run(codes={1: 1})
    report = practice.report()
    assert set(report) == {"schema", "commit", "baseline", "requirements", "assumed", "counts"}
    assert report["schema"] == 1
    assert report["commit"] == _git(practice.worktree, "rev-parse", "HEAD").strip()
    assert report["baseline"] == {"exit_code": 0, "result": "PASS", "reason": "reason for value=0"}
    assert report["requirements"][0] == {"id": "req-1", "patch": "bug1.patch", "label": "checked", "verifier_exit": 1,
                                         "reason": "reason for value=1"}
    assert report["assumed"] == [{"item": "the weights", "reason": "no test here loads them"}]


def test_every_mutant_appears_once_in_order(practice):
    practice.write_mutants(3, 1, 2)
    practice.run()
    assert [r["id"] for r in practice.report()["requirements"]] == ["req-3", "req-1", "req-2"]


def test_it_prints_one_line_per_requirement_and_a_result_line(practice):
    done = practice.run(codes={1: 1, 2: 0, 3: 2})
    lines = done.stdout.strip().splitlines()
    assert any("req-1" in line and "checked" in line for line in lines)
    assert any("req-2" in line and "unguarded" in line for line in lines)
    assert any("req-3" in line and "unverified" in line for line in lines)
    assert lines[-1].startswith("RESULT:")
    assert "1 checked" in lines[-1] and "1 unguarded" in lines[-1] and "1 unverified" in lines[-1]


def test_the_tree_is_clean_after_each_mutant(practice):
    head = _git(practice.worktree, "rev-parse", "HEAD")
    assert practice.run(codes={1: 1, 2: 1, 3: 1}).returncode == 0
    assert practice.seen() == ["value=0", "value=1", "value=2", "value=3"]  # one bug at a time, never stacked
    assert practice.clean()
    assert _git(practice.worktree, "rev-parse", "HEAD") == head
    assert (practice.worktree / "target.txt").read_text(encoding="utf-8").strip() == "value=0"


def test_it_can_run_twice_in_the_same_worktree(practice):
    assert practice.run(codes={1: 1, 2: 1, 3: 1}).returncode == 0
    assert practice.run(codes={1: 1, 2: 1, 3: 1}).returncode == 0


def test_the_main_clone_is_refused_and_nothing_runs(practice):
    done = practice.run(cwd=practice.clone)
    assert done.returncode == 2 and "worktree" in done.stdout
    assert practice.seen() == [] and not practice.has_report()


def test_a_folder_outside_git_is_refused(practice, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    assert practice.run(cwd=outside).returncode == 2
    assert practice.seen() == []


def test_a_subfolder_of_the_worktree_is_refused(practice):
    folder = practice.worktree / "sub"
    folder.mkdir()
    assert practice.run(cwd=folder).returncode == 2
    assert practice.seen() == []


def test_a_changed_file_is_refused_and_kept(practice):
    (practice.worktree / "target.txt").write_text("value=mine\n", encoding="utf-8")
    done = practice.run()
    assert done.returncode == 2 and "clean" in done.stdout
    assert practice.seen() == [] and not practice.has_report()
    assert (practice.worktree / "target.txt").read_text(encoding="utf-8") == "value=mine\n"


def test_an_untracked_file_is_refused(practice):
    (practice.worktree / "notes.txt").write_text("mine", encoding="utf-8")
    assert practice.run().returncode == 2
    assert practice.seen() == []


@pytest.mark.parametrize("baseline", [1, 2, 7])
def test_a_baseline_that_does_not_pass_stops_before_any_bug_is_planted(baseline, practice):
    done = practice.run(baseline=baseline)
    assert done.returncode == 2 and "baseline" in done.stdout.lower()
    assert practice.seen() == ["value=0"]
    assert not practice.has_report() and practice.clean()


def test_a_baseline_that_cannot_start_stops_the_run(practice):
    done = practice.run(command=["no-such-command-rpd-workshop"])
    assert done.returncode == 2 and not practice.has_report() and practice.clean()


def test_a_baseline_that_changes_the_tree_stops_the_run(practice):
    done = practice.run(command=[sys.executable, "-c", "open('stray.txt', 'w').close()"])
    assert done.returncode == 2 and "clean" in done.stdout and not practice.has_report()


def test_a_patch_that_will_not_apply_stops_the_run_with_no_report(practice):
    (practice.track / "patches" / "bug2.patch").write_text(
        "--- a/target.txt\n+++ b/target.txt\n@@ -1 +1 @@\n-value=elsewhere\n+value=2\n", encoding="utf-8", newline="\n")
    done = practice.run(codes={1: 1})
    assert done.returncode == 2 and "bug2.patch" in done.stdout
    assert practice.seen() == ["value=0", "value=1"]
    assert not practice.has_report() and practice.clean()


def test_a_missing_patch_stops_the_run_before_it_starts(practice):
    practice.write_mutants(1, 9)
    done = practice.run()
    assert done.returncode == 2 and "bug9.patch" in done.stdout
    assert practice.seen() == []


def test_a_patch_that_will_not_reverse_stops_the_run_and_says_to_delete_the_worktree(practice):
    done = practice.run(actions={2: "rewrite"})
    assert done.returncode == 2 and "delete" in done.stdout.lower()
    assert not practice.has_report()


def test_cached_bytecode_is_never_reused_between_runs(practice):
    """A planted bug can keep the file's size, and a run can fit in one second: Python would then trust a stale .pyc."""
    (practice.clone / ".git" / "info" / "exclude").write_text("__pycache__/\n", encoding="utf-8")
    cache = practice.worktree / "src" / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "infer.cpython-312.pyc").write_bytes(b"stale")
    seen = practice.tmp / "seen.log"
    code = ("import os, pathlib, sys; "
            "line = os.environ.get('PYTHONDONTWRITEBYTECODE', 'unset'), pathlib.Path('src/pkg/__pycache__').exists(); "
            "open(sys.argv[1], 'a').write(f'{line}\\n')")
    assert practice.run(command=[sys.executable, "-c", code, str(seen)]).returncode == 1
    assert seen.read_text(encoding="utf-8").splitlines() == ["('1', False)"] * 4  # the baseline and three mutants


def test_a_verify_command_that_leaves_a_file_behind_stops_the_run(practice):
    done = practice.run(actions={1: "stray"})
    assert done.returncode == 2 and "clean" in done.stdout
    assert practice.seen() == ["value=0", "value=1"]
    assert not practice.has_report()


def test_an_unknown_option_is_a_usage_error(practice):
    assert practice.run(options=["--mutants", str(practice.mutants), "--evidence", "x", "--force"]).returncode == 2
    assert practice.seen() == []


def test_no_verify_command_is_a_usage_error(practice):
    assert practice.run(command=[]).returncode == 2
    assert practice.seen() == []


@pytest.mark.parametrize("options", [["--evidence", "x"], ["--mutants", "m.json"]])
def test_both_options_are_required(options, practice):
    assert practice.run(options=options).returncode == 2


@pytest.mark.parametrize("text", ["{not json", "[]", "{}", '{"requirements": [], "assumed": []}',
                                  '{"requirements": [{"id": "a"}], "assumed": []}',
                                  '{"requirements": [{"id": "a", "patch": "../bug1.patch"}], "assumed": []}',
                                  ('{"requirements": [{"id": "a", "patch": "bug1.patch"},'
                                   ' {"id": "a", "patch": "bug2.patch"}], "assumed": []}')])
def test_a_bad_mutants_file_is_refused(text, practice):
    practice.mutants.write_text(text, encoding="utf-8")
    assert practice.run().returncode == 2
    assert practice.seen() == []


def test_a_missing_mutants_file_is_refused(practice):
    practice.mutants.unlink()
    assert practice.run().returncode == 2
