"""The example agent configuration shipped with the repo: a Stop hook, a skill and a read-only sub-agent."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "require_green_tests.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("require_green_tests", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    head = text.split("---\n", 2)[1]
    return dict(line.split(":", 1) for line in head.strip().splitlines() if ":" in line)


def test_green_app_tests_allow_stop():
    assert load_hook().decide(0, "All tests passed!", disabled=False)[0] == 0


def test_red_app_tests_block_stop_and_say_why():
    code, msg = load_hook().decide(1, "Some tests failed.\n  config_test.dart: counting settings live in config.dart", disabled=False)
    assert code == 2
    assert "flutter test" in msg and "config_test" in msg


def test_missing_flutter_fails_open_with_warning():
    code, msg = load_hook().decide(None, "flutter not found", disabled=False)
    assert code == 0 and "could not run" in msg


def test_off_switch_allows_stop():
    code, msg = load_hook().decide(1, "Some tests failed.", disabled=True)
    assert code == 0 and "RICE_PEST_STOP_HOOK=off" in msg


def test_settings_run_the_hook_with_a_quoted_project_dir_and_allow_only_flutter_test():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert '"$CLAUDE_PROJECT_DIR/.claude/hooks/require_green_tests.py"' in command
    assert settings["permissions"]["allow"] == ["Bash(flutter test:*)"]


def test_skill_has_name_and_description_and_is_mirrored():
    claude = ROOT / ".claude/skills/refactor-safely/SKILL.md"
    shared = ROOT / ".agents/skills/refactor-safely/SKILL.md"
    meta = frontmatter(claude)
    assert meta["name"].strip() == "refactor-safely"
    assert len(meta["description"].strip()) > 40
    assert claude.read_bytes() == shared.read_bytes()


def test_find_callers_is_read_only():
    meta = frontmatter(ROOT / ".claude/agents/find-callers.md")
    assert meta["name"].strip() == "find-callers"
    assert {t.strip() for t in meta["tools"].split(",")} <= {"Read", "Grep", "Glob"}
