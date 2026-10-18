"""Claude Code Stop hook: block "done" while the app's tests fail.

Runs `flutter test` in app/. Exit 2 blocks the stop and feeds the failure back to the agent;
exit 0 allows it. If Flutter is not installed, the stop is allowed with a warning.
It blocks once per stop: when the runtime reports that the agent is already continuing because of
this hook (`stop_hook_active` in the event on stdin) and the tests still fail, the stop is allowed
with a warning, so the agent cannot loop forever. Switch it off with RICE_PEST_STOP_HOOK=off.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def decide(returncode, output, disabled, already_active=False):
    if disabled:
        return 0, "Stop hook disabled (RICE_PEST_STOP_HOOK=off)."
    if returncode is None:
        return 0, f"Warning: could not run flutter test, so the stop is allowed. Details: {output[-300:]}"
    if returncode == 0:
        return 0, "App tests pass."
    tail = "\n".join(output.strip().splitlines()[-15:])
    if already_active:
        return 0, ("Warning: flutter test is still failing after the hook already blocked once, so the stop is "
                   f"allowed to avoid a loop. The work is not done until these pass:\n{tail}")
    return 2, f"Not done: flutter test is failing. Make these pass before stopping:\n{tail}"


def read_event(stream):
    """The Stop event the runtime sends on stdin, as a dict; {} when there is none or it is not JSON."""
    try:
        if stream is None or stream.isatty():
            return {}
        data = json.loads(stream.read() or "{}")
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def main():
    disabled = os.environ.get("RICE_PEST_STOP_HOOK", "").lower() == "off"
    already_active = bool(read_event(sys.stdin).get("stop_hook_active"))
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    flutter = shutil.which("flutter")
    if disabled or flutter is None:
        code, msg = decide(None if flutter is None else 0, "flutter not found on PATH", disabled)
    else:
        try:
            run = subprocess.run([flutter, "test"], cwd=root / "app", capture_output=True, text=True, check=False,
                                 encoding="utf-8", errors="replace", timeout=600)
            code, msg = decide(run.returncode, run.stdout + run.stderr, disabled, already_active)
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, msg = decide(None, str(exc), disabled)
    print(msg, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
