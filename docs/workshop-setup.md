# Coding with AI Agents: setup before the session

About 15 minutes, done before the day. The session is two hours of short talks, a live demo of the Android demo app and three short exercises. You can take part with any coding agent, or with none: everything is shown on screen, and you can pair with someone who has one.

## What you need, at a glance

| | Needed for | Required? |
| :-- | :-- | :-- |
| Git and this repository, cloned | The specs, agent setup and case studies used in the session | Yes |
| A coding agent you are allowed to use | Exercises 0, 1 and 2 | Yes, to follow along hands-on. Otherwise watch, or pair up |
| A terminal and an empty practice folder | Exercises 1 and 2 | Yes |
| `uv` and Spec Kit | Exercise 2 | Yes, for Exercise 2 |

That is all the session needs. Nothing in this repository has to be built for it, and the app demo runs on the presenter's machine. The model weights are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector) as a teaching demo.

**Optional**, each for one task:

| To… | Install |
| :-- | :-- |
| Run the tests and tools | [Python 3.12](https://www.python.org/downloads/), then `pip install -r requirements.txt` |
| Run the demo app | [Flutter](https://docs.flutter.dev/get-started/install), [Android Studio](https://developer.android.com/studio) and an Android emulator |
| Run the training notebooks | A [Google Colab](https://colab.research.google.com) account (you sign in with a Google account) |
| Let an agent work with the repository on GitHub | The [GitHub CLI](https://cli.github.com) (`gh`) or the [GitHub MCP server](https://github.com/github/github-mcp-server) |
| Let an agent run the Colab notebooks | The [Colab MCP server](https://github.com/googlecolab/colab-mcp), which connects a local agent to a Colab session in your browser |

Sections 5 and 6 below cover the first two optional rows; [setup.md](setup.md) covers all of them by task.

## 1. Clone this repository

Install [Git](https://git-scm.com/downloads) if you do not have it (Windows: `winget install --id Git.Git -e`; macOS: `brew install git`; Ubuntu: `sudo apt install git`), then:

```bash
git clone https://github.com/kurtvalcorza/rice-pest-detector.git
```

What you will open from it during the session:

| When | Open | What it shows |
| :-- | :-- | :-- |
| Module 2 | `.claude/skills/`, `.claude/agents/`, `.claude/hooks/` | A working skill, read-only sub-agent and Stop hook, the three extension points the module explains |
| Module 3, the real specs | `docs/specs/` | The specs written before the code: the model and the demo app |
| Module 5 and after | `docs/presentations/*.html` (open in a browser) | The session deck, the two case studies (training the model, building the app) and the deep dive on agent harnesses and context engineering |
| Any time | `README.md`, `docs/evaluation-record.md` | How the project works, and every result with its provenance |

## 2. A coding agent, set up safely

Use the agent you already have, whatever it is: one that runs in a terminal, in your editor or in the browser. Before the session:

1. **Check its terms.** Some agents exclude users under 18. Pick one whose terms allow you, or plan to watch and navigate for a partner.
2. **Sign in once** and send it a test message, so you are not creating an account during the session.
3. **Switch training off.** Many free tiers may use what you type to improve their models. Find the data or training setting and turn it off.
4. **Know what not to paste.** Never paste personal or confidential material (company code, client data) or graded work. Everything in the session is safe to type.

### Or let your agent do steps 3 and 4

Once your agent works, you can ask it to do the rest. Open it in the cloned `rice-pest-detector` folder and send:

> Read docs/workshop-setup.md. First tell me what is already installed and what is missing, and wait. Then make the practice folder and install only uv and Spec Kit, asking me before each command, and check that `specify --help` works. Do not change account, system or security settings, do not use admin rights, and do not install Flutter or Android tools.

Read its plan before you approve anything, and read each command before it runs: the `uv` installer downloads and runs a script from the internet. This is a small version of what the session is about. The repository's `AGENTS.md` repeats these limits for any agent that reads it.

## 3. A terminal and a practice folder

The exercises start from scratch, so keep them outside the cloned repository. Open your usual terminal (PowerShell on Windows; Terminal on macOS or Linux) and make an empty folder, for example:

```bash
mkdir agents-practice
cd agents-practice
git init
```

`git init` is optional but recommended: with Git, every change the agent makes shows up in `git diff` and can be undone with `git restore .`.

## 4. `uv` and Spec Kit (for Exercise 2)

Exercise 2 uses [Spec Kit](https://github.com/github/spec-kit) to write a spec before any code. It installs with `uv`, which also fetches a suitable Python (3.11 or later) if you do not have one.

**Install `uv`:**

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with a package manager: `winget install --id astral-sh.uv -e` (Windows) or `brew install uv` (macOS).

Close and reopen the terminal so it finds `uv`.

**Install Spec Kit:**

```bash
uv tool install specify-cli
specify --help
```

If `specify --help` prints its commands, you are ready. The session was prepared on Spec Kit 1.2.0; 1.2.1 or later works the same way.

**Optional dry run** (two minutes; it confirms Spec Kit and your agent work together):

```bash
specify init setup-check --integration <your-agent>
```

Replace `<your-agent>` with your agent's key, for example `claude`, `copilot`, `gemini`, `codex`, `cursor-agent` or `opencode` (the [full list](https://github.github.io/spec-kit/reference/integrations.html)). Open your agent in the new `setup-check` folder and type `/speckit-` in its chat: the Spec Kit commands should appear. Codex uses `$speckit-…` instead. Then delete the `setup-check` folder.

## 5. Optional, after the session: run the Python tests

`python -m venv .venv`, then `pip install -r requirements.txt`, then `pytest`. Needs Python 3.12. [setup.md](setup.md) has the exact commands and what each package is for.

## 6. Optional, in your own time: run the demo app on an emulator

Not needed for the session. Allow one to two hours for the first install and build.

| | You need |
| :-- | :-- |
| Flutter | Stable channel (Dart 3.13.5 or later). On Windows, install it to a path **without spaces**, for example `C:\src\flutter` |
| Android | Android Studio, with the Android SDK, platform tools, the Emulator and a system image (prepared on Android 36, Google APIs, x86_64) |
| Your laptop | Virtualisation turned on in the BIOS/UEFI, about 15 GB of free disk and 8 GB of RAM or more |

Install commands for Windows (winget), macOS (Homebrew) and Ubuntu (apt) are in the README, "Setup".

Then:

1. Run `flutter doctor` until the Android toolchain shows no errors, and accept the licences with `flutter doctor --android-licenses`.
2. In Android Studio's Device Manager, create an emulator with the system image above, and start it.
3. From the repository's `app/` folder: `flutter run --no-enable-impeller -d emulator-5554`. The flag avoids a hang on emulators without a graphics card. Or let a script do the starting, waiting and running: `.\tools\run_emulator.ps1` (Windows PowerShell) or `tools/run_emulator.sh` (macOS, Linux). It finds the Android SDK (`ANDROID_HOME`) and Flutter (`PATH` or `FLUTTER_ROOT`), starts the first emulator (or `-Avd <name>` / `--avd <name>`), waits for it to boot and runs the app. Add `-Fresh` / `--fresh` to clear the app's data first, so you can try the model download from the start.

**The model.** The trained weights are not part of this repository; they are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector). A fresh install opens with "No model is installed yet", and counting is off until the model is downloaded. The app's home screen offers **Download the model**: the app fetches r50-v5 (about 172 MB) from Kaggle, checks its size and SHA-256 and then counts, with the notice "Demo: real model weights … not validated in the field".

## If something does not work

- **`uv` or `specify` is "not found":** open a new terminal. On Windows, sign out and back in if it still fails.
- **A work or school laptop blocks installs:** skip step 4 and pair with someone for Exercise 2, or ask your IT team before the day. Without Git, download the repository as a ZIP from its GitHub page instead.
- **No agent, or under 18 and none allowed:** you can still do Exercise 0 on paper and navigate for a partner in Exercises 1 and 2.

On the day, bring the laptop charged, and the agent signed in.
