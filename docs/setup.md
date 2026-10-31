# Setup: what to install

What you install depends on what you want to do. Find your row, install what it lists and skip the rest. Nothing needs admin rights except where noted. The commands for Windows (winget), macOS (Homebrew) and Linux (Ubuntu) are in [Install commands by operating system](#install-commands-by-operating-system).

| I want to… | Install | Time |
| :-- | :-- | :-- |
| Read the slides and the docs | A web browser | none |
| Use a coding agent | An editor, an agent you are allowed to use and its command-line tool. See [An AI coding agent](#an-ai-coding-agent) | about 10 min |
| Take part in the 2-hour session, or do its exercises on your own | Git, a coding agent, `uv` and Spec Kit. The course path is in [workshop-setup.md](workshop-setup.md) | about 15 min |
| Run the Python tests and tools | Git, Python 3.12, the packages in `requirements.txt` | about 15 min |
| Train a model | A Google account and a browser; training runs on Google Colab | none locally |
| Export a model to ONNX, check parity, calibrate | Everything in the row "Run the Python tests and tools" | as above |
| Run the demo app on an emulator | Flutter, Android Studio with the Android SDK and an emulator | 1–2 hours the first time |
| Run notebooks and scripts on Colab from a terminal | The Colab CLI (Linux and macOS; on Windows, inside WSL). See [Colab CLI](#colab-cli-optional) | about 15 min |
| Let an agent run the Colab notebooks, or use Kaggle | The Colab MCP and Kaggle MCP servers. See [MCP](#let-your-agent-work-with-colab-and-kaggle-mcp) | about 10 min |
| Let an agent work with the repository on GitHub | The [GitHub CLI](https://cli.github.com) (`gh`, row in the table below) or the [GitHub MCP server](https://github.com/github/github-mcp-server) | about 5 min |

## Let your agent check what is installed

Once an agent works ([An AI coding agent](#an-ai-coding-agent)), it can tell you what you already have. Open it in the cloned `rice-pest-detector` folder and send:

> Read docs/setup.md. Without installing or changing anything, check which of these I have and their versions: git, uv, specify, python 3.12, the agent CLIs (agy, claude, codex), flutter, adb, colab, and on Windows wsl. Show a table with the tool, what this repository needs it for, the version or "missing", and the setup.md section that installs it. Then wait for me.

Every command it runs should be a version check (`git --version` and the like): approve each one, and stop it if it tries to install or change anything. Then install only the rows your task needs.

None of these needs the trained weights. They are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector), and the demo app can download r50-v5 itself.

## Install commands by operating system

Windows uses [winget](https://learn.microsoft.com/windows/package-manager/winget/) (built into Windows 10 and 11; run in PowerShell), macOS uses [Homebrew](https://brew.sh), Linux examples are for Ubuntu 24.04. Close and reopen the terminal after installing, so it finds the new commands.

| Tool | Windows (winget) | macOS (Homebrew) | Linux (Ubuntu) |
| :-- | :-- | :-- | :-- |
| Git | `winget install --id Git.Git -e` | `brew install git` | `sudo apt install git` |
| Python 3.12 (optional) | `winget install --id Python.Python.3.12 -e` | `brew install python@3.12` | `sudo apt install python3.12 python3.12-venv` |
| GitHub CLI (optional) | `winget install --id GitHub.cli -e` | `brew install gh` | [official instructions](https://github.com/cli/cli/blob/trunk/docs/install_linux.md) |
| Android Studio (optional) | `winget install --id Google.AndroidStudio -e` | `brew install --cask android-studio` | [download](https://developer.android.com/studio) |
| Flutter (optional) | [install guide](https://docs.flutter.dev/get-started/install/windows) (no winget package); unzip to a path without spaces, e.g. `C:\src\flutter` | `brew install --cask flutter` | `sudo snap install flutter --classic` |

`uv` and Spec Kit have their own installers, in [uv and Spec Kit](#uv-and-spec-kit); the agents' are in [An AI coding agent](#an-ai-coding-agent). The sections below give each tool's details and how to check it works.

## Git

Install it with the Git row of the [table above](#install-commands-by-operating-system), or download it from [git-scm.com/downloads](https://git-scm.com/downloads). Check with `git --version`, then clone the repository:

```bash
git clone https://github.com/kurtvalcorza/rice-pest-detector.git
cd rice-pest-detector
```

## An AI coding agent

What you install here is the agent's *harness*: the program around the AI model that reads your files, runs commands and asks your permission ("Agent = Model + Harness" in the session deck). Any coding agent you are allowed to use works. The workshop demos happened to use three, each as a VS Code extension with its command-line tool, so the steps below cover those. **Naming them is not a recommendation or an endorsement:** this project has no affiliation with any of these companies, receives nothing from them, and is not endorsed by them. Each is a third-party product under its own terms, data practices and pricing, which change; check them before you sign up. Choosing an agent and setting it up safely (terms, age limits, training settings) is in [workshop-setup.md, "Set up your agent safely"](workshop-setup.md#set-up-your-agent-safely).

**1. An editor.** The demos used VS Code: download it from [code.visualstudio.com](https://code.visualstudio.com), or `winget install Microsoft.VisualStudioCode` (Windows) or `brew install --cask visual-studio-code` (macOS).

**2. The agent's extension.** In VS Code, open the Extensions view (Ctrl+Shift+X, or Cmd+Shift+X on macOS) and install the one for your agent, or run `code --install-extension <id>`:

| Agent (alphabetical) | Extension id | Notes |
| :-- | :-- | :-- |
| Antigravity | `google.google-antigravity` | VS Code 1.90 or later; signs in with a Google account. [Getting started](https://antigravity.google/docs/getting-started) |
| Claude Code | `anthropic.claude-code` | VS Code 1.94 or later; needs an account type that includes Claude Code (see its [guide](https://code.claude.com/docs/en/vs-code)) |
| Codex | `openai.chatgpt` | Signs in with a ChatGPT account or another method it offers. [Guide](https://learn.chatgpt.com/docs/codex/ide) |

Open the extension's panel once and sign in. It works when it answers a test message.

**3. The agent's command-line tool.** Spec Kit's integrations for these agents (`agy`, `claude`, `codex`) expect the CLI, and the MCP set-up below uses the `claude` command:

| Agent (alphabetical) | macOS, Linux or WSL | Windows (PowerShell) | Check |
| :-- | :-- | :-- | :-- |
| Antigravity | `curl -fsSL https://antigravity.google/cli/install.sh \| bash` | `irm https://antigravity.google/cli/install.ps1 \| iex` | `agy --version` |
| Claude Code | `curl -fsSL https://claude.ai/install.sh \| bash` | `irm https://claude.ai/install.ps1 \| iex` | `claude --version` |
| Codex | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` | `npm install -g @openai/codex` (needs [Node.js](https://nodejs.org)) | `codex --version` |

Open a new terminal after installing, so it finds the command. Package-manager installs exist too (for example `brew install --cask claude-code` or `winget install Anthropic.ClaudeCode`); each vendor's guide lists them. The Claude Code extension carries its own copy of the CLI for its chat panel, but the `claude` command in a terminal needs this install. On Windows, Git for Windows (see [Git](#git)) lets Claude Code use Bash; without it, it uses PowerShell. Each installer downloads and runs a script from the internet: read the command before you run it.

## uv and Spec Kit

[Spec Kit](https://github.com/github/spec-kit) writes a spec before any code; the workshop's Exercise 2 and the self-paced exercise use it. It installs with `uv`, which also fetches a suitable Python (3.11 or later) if you do not have one.

**Install `uv`:**

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal so it finds `uv`.

**Install Spec Kit:**

```bash
uv tool install specify-cli
specify --help
```

If `specify --help` prints its commands, you are ready. This repository's Spec Kit files were made with Spec Kit 1.2.1.

**Optional dry run** (two minutes; it confirms Spec Kit and your agent work together):

```bash
specify init setup-check --integration <your-agent>
```

Replace `<your-agent>` with your agent's key, for example `agy`, `claude`, `codex`, `copilot`, `cursor-agent` or `opencode` (the [full list](https://github.github.io/spec-kit/reference/integrations.html)). Open your agent in the new `setup-check` folder and type `/speckit-` in its chat: the Spec Kit commands should appear. Codex uses `$speckit-…` instead. Then delete the `setup-check` folder.

## Python tools and tests

**Python 3.12** exactly: `pyproject.toml` requires `>=3.12,<3.13`. Download it from [python.org/downloads](https://www.python.org/downloads/). On Windows, tick "Add python.exe to PATH" on the installer's first screen. Check with `python --version`.

Then make a virtual environment and install the packages:

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest
```

```bash
# macOS or Linux
python3.12 -m venv .venv
.venv/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest
```

The `torch` line installs the CPU build of PyTorch, which is much smaller than the default one; the tests and tools do not need the larger default build. `requirements.txt` lists every package and the versions the repository was tested with:

| Package | Needed for |
| :-- | :-- |
| numpy, pillow | Everything: image loading, preprocessing, metrics |
| torch, transformers 5.20.1, scipy, pycocotools | Loading checkpoints, evaluation (COCO mAP), ONNX export. transformers must be 5.18 or later: earlier versions have a training-loss bug for RT-DETR and D-FINE (see the evaluation record) |
| onnx, onnxruntime | ONNX export, PyTorch–ONNX parity, calibration and threshold tools |
| pytest, ruff, nbformat | Tests, lint, the notebook generator |

`pyproject.toml` is the source of truth; `requirements.txt` mirrors it, and a test fails if they drift apart. If you use [uv](https://docs.astral.sh/uv/), `uv pip install -r requirements.txt` works the same way.

Tests that need torch, transformers or onnxruntime are skipped automatically when those packages are missing, so a partial install still runs the rest.

## Training

Nothing to install on your computer: training runs on Google Colab with a T4 GPU. You need a Google account with at least 20 GB free in Google Drive (the notebook warns if there is less). Each notebook installs its own packages and downloads the images from Zenodo during the run. How to run a notebook: the README, "Training on Colab".

### Colab CLI (optional)

The [Colab CLI](https://github.com/googlecolab/google-colab-cli) (`google-colab-cli`) starts Colab runtimes, including T4 GPUs, and runs notebooks and scripts on them from your terminal, so you or an agent can train without the browser. The later runs in the evaluation record (r50-1 and the second wave) were made with it.

> **Why WSL on Windows:** the Colab CLI's [README](https://github.com/googlecolab/google-colab-cli#readme) says it "currently supports Linux and macOS only. Windows is not supported at this time." WSL (Windows Subsystem for Linux) runs a real Linux on Windows, so the CLI runs there unchanged.

**Windows only: install WSL first.** In PowerShell **as administrator** (once; it needs virtualisation turned on in the BIOS/UEFI):

```powershell
wsl --install -d Ubuntu
```

Restart if asked, open **Ubuntu** from the Start menu and create its Linux user. Run everything below in that Ubuntu terminal. Your Windows files are under `/mnt/c/`, but cloning the repository inside Ubuntu (`git clone` as in [Git](#git)) is faster.

**Install** (Linux, macOS or WSL). It needs `uv` ([uv and Spec Kit](#uv-and-spec-kit), the macOS or Linux command), which also fetches the Python 3.12 the CLI requires:

```bash
uv tool install google-colab-cli
colab --help
```

**Sign in and check it works.** The first command that talks to Colab prints a sign-in URL: open it in any browser (on Windows, your normal one), sign in with your Google account, and paste the code it shows back into the terminal. Then start a small CPU runtime, run one line on it, and release it:

```bash
colab new
echo "print('Hello from Google Colab!')" | colab exec
colab stop
```

The sign-in token is saved in `~/.config/colab-cli/token.json`; keep it private, and delete it to sign out. Upgrade later with `uv tool upgrade google-colab-cli`. Every runtime uses your Colab quota until you `colab stop` it.

### Let your agent work with Colab and Kaggle (MCP)

Two MCP servers let a coding agent on your computer work with the notebooks and the published models. Both are optional; training works without them. The commands are shown for Claude Code, one of the agents the demos used; other clients are covered on each server's own page.

**Colab MCP** ([googlecolab/colab-mcp](https://github.com/googlecolab/colab-mcp)) connects a local agent to a Colab session open in your browser, so the agent can add and run notebook cells there. It needs `uv` (see [uv and Spec Kit](#uv-and-spec-kit)) and a client that runs on your computer and supports tool-list change notifications: Claude Code, Gemini CLI and Windsurf are the ones its page names. Gemini CLI no longer signs in with a personal Google account (checked with 0.62.0, 31 October 2026); it sends those users to Antigravity.

1. Add the server, for your user only (not to the repository):

   ```bash
   claude mcp add --scope user colab-mcp -- uvx git+https://github.com/googlecolab/colab-mcp
   ```

   In clients configured with an `mcpServers` JSON block, the same server is `"colab-mcp": {"command": "uvx", "args": ["git+https://github.com/googlecolab/colab-mcp"], "timeout": 30000}`.
2. Restart Claude Code and run `/mcp`: `colab-mcp` should be listed as connected.
3. Ask the agent to open a Colab connection. It opens Colab in your browser; sign in with your Google account there, and the agent's notebook tools appear once the session is connected.
4. Check the connection: ask it to add a cell that runs `!nvidia-smi` in the connected session and run it. It should report the GPU.

Code the agent runs in Colab uses your account's compute and can read your Google Drive once you mount it. Read each cell before you approve it, and run training cells one at a time.

**Kaggle MCP** ([kaggle.com/docs/mcp](https://www.kaggle.com/docs/mcp)) is a remote server at `https://www.kaggle.com/mcp` with tools for models, datasets, notebooks, competitions, benchmarks and hackathons. With it an agent can look up and download the published [rice-pest-detector models](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector) or check a Kaggle notebook session.

1. Add the server:

   ```bash
   claude mcp add --scope user --transport http kaggle https://www.kaggle.com/mcp
   ```

2. Sign in. Some tools work without it; anything tied to your account needs authorisation. Kaggle supports OAuth 2.0. In Claude Code, run `/mcp` and choose `kaggle`: if it offers to authenticate, follow the sign-in in your browser. Otherwise ask the agent to call Kaggle's `authorize` tool (Kaggle's page names this route for clients without their own sign-in command), or use a token instead (next step).
3. Token instead of OAuth: on Kaggle, open **Settings → Generate New Token** and copy it (it starts with `KGAT`). Keep it out of the repository and out of chat. Put it in an environment variable, then add the server with it:

   ```bash
   claude mcp add --scope user --transport http kaggle https://www.kaggle.com/mcp --header "Authorization: Bearer $KAGGLE_API_TOKEN"
   ```

   On Windows PowerShell use `$env:KAGGLE_API_TOKEN`. The token ends up in your user configuration, not in the repository: never use `--scope project` for it, which writes `.mcp.json` into the folder. Revoke the token on Kaggle when you no longer need it.
4. Check the connection: `/mcp` shows `kaggle` as connected, and asking the agent to list the variations of the Kaggle model `kurtvalcorza/rice-pest-detector` returns r50-v5, RF-DETR-M and D-FINE-L.

A signed-in Kaggle connection can create and change things on your account (models, datasets, notebook sessions). Approve each tool call, and prefer OAuth, which you can revoke from Kaggle's settings.

## Demo app (optional)

| | You need |
| :-- | :-- |
| Flutter | Stable channel, Dart 3.13.5 or later (tested with Flutter 3.47.7). On Windows, install it to a path **without spaces**, for example `C:\src\flutter`. [docs.flutter.dev/get-started/install](https://docs.flutter.dev/get-started/install) |
| Android Studio | With the Android SDK, Platform-Tools, the Emulator and a system image (tested on Android 36, Google APIs, x86_64). [developer.android.com/studio](https://developer.android.com/studio) |
| Your computer | Virtualisation turned on in the BIOS/UEFI (may need admin rights), about 15 GB free disk and 8 GB of RAM or more |

Then run `flutter doctor` until the Android toolchain shows no errors, accept the licences with `flutter doctor --android-licenses`, and create an emulator in Android Studio's Device Manager with the system image above. Check the install from `app/`:

```bash
flutter pub get
flutter test
```

`flutter pub get` installs the app's own packages (`flutter_onnxruntime`, `image` and others, listed in `app/pubspec.yaml`); you do not install them separately. If `flutter test` passes, the toolchain is ready. Running the app is in [workshop-setup.md, "Optional: run the demo app"](workshop-setup.md#optional-run-the-demo-app-on-an-emulator).

## If something does not work

- **`python` is not found, or opens the Microsoft Store:** Python is not on your PATH. Re-run the installer and tick "Add python.exe to PATH".
- **The wrong Python version:** use `py -3.12 -m venv .venv` on Windows, or `python3.12 -m venv .venv` elsewhere.
- **`pip install` fails on torch:** install the CPU build first, as above, then re-run `pip install -r requirements.txt`.
- **`wsl --install` fails:** run PowerShell as administrator, and turn on virtualisation in the BIOS/UEFI.
- **`uv` or `specify` is "not found":** open a new terminal. On Windows, sign out and back in if it still fails.
- **A work or school laptop blocks installs:** ask your IT team, or use the browser-only rows above. Without Git, download the repository as a ZIP from its GitHub page.
