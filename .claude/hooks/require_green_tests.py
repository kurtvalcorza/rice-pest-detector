"""Claude Code Stop hook: block "done" while the app's tests fail.

Runs `flutter test` in app/. Exit 2 blocks the stop and feeds the failure back to the agent;
exit 0 allows it. If Flutter is not installed, the stop is allowed with a warning.
Switch it off with RICE_PEST_STOP_HOOK=off.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def decide(returncode, output, disabled):
    if disabled:
        return 0, "Stop hook disabled (RICE_PEST_STOP_HOOK=off)."
    if returncode is None:
        return 0, f"Warning: could not run flutter test, so the stop is allowed. Details: {output[-300:]}"
    if returncode == 0:
        return 0, "App tests pass."
    tail = "\n".join(output.strip().splitlines()[-15:])
    return 2, f"Not done: flutter test is failing. Make these pass before stopping:\n{tail}"


def main():
    disabled = os.environ.get("RICE_PEST_STOP_HOOK", "").lower() == "off"
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    flutter = shutil.which("flutter")
    if disabled or flutter is None:
        code, msg = decide(None if flutter is None else 0, "flutter not found on PATH", disabled)
    else:
        try:
            run = subprocess.run([flutter, "test"], cwd=root / "app", capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=600)
            code, msg = decide(run.returncode, run.stdout + run.stderr, disabled)
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, msg = decide(None, str(exc), disabled)
    print(msg, file=sys.stderr if code == 2 else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
