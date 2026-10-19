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

Anything else (running the tests, the training notebooks, the demo app, or the Colab, Kaggle and GitHub MCP servers) is optional and listed by task in [setup.md](setup.md).

## 1. Clone this repository

Install Git if you do not have it ([setup.md, Git](setup.md#git)), then:

```bash
git clone https://github.com/kurtvalcorza/rice-pest-detector.git
```

What you will open from it during the session:

| When | Open | What it shows |
| :-- | :-- | :-- |
| Module 2 | `.claude/skills/`, `.claude/agents/`, `.claude/hooks/` | A working skill, read-only sub-agent and Stop hook, the three extension points the module explains |
| Module 3, the real specs | `.specify/memory/constitution.md`, `specs/` | Spec Kit specs: the project's constitution, the model (001), the phone app (002) and the desktop app (003) |
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

> Read docs/workshop-setup.md and the "uv and Spec Kit" section of docs/setup.md. First tell me what is already installed and what is missing, and wait. Then make the practice folder and install only uv and Spec Kit, asking me before each command, and check that `specify --help` works. Do not change account, system or security settings, do not use admin rights, and do not install Flutter or Android tools.

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

Exercise 2 and section 7 use [Spec Kit](https://github.com/github/spec-kit), which installs with `uv`. Follow [setup.md, uv and Spec Kit](setup.md#uv-and-spec-kit), including its optional two-minute dry run with your agent.

## 5. Optional, after the session: run the Python tests

See [setup.md, Python tools and tests](setup.md#python-tools-and-tests).

## 6. Optional, in your own time: run the demo app on an emulator

Not needed for the session. Install Flutter, Android Studio and an emulator first: [setup.md, Demo app](setup.md#demo-app-optional) (allow one to two hours the first time). Then start the emulator and, from the repository's `app/` folder:

```bash
flutter run --no-enable-impeller -d emulator-5554
```

The `--no-enable-impeller` flag avoids a hang on emulators without a graphics card. Or let a script do the starting, waiting and running: `.	ools
un_emulator.ps1` (Windows PowerShell) or `tools/run_emulator.sh` (macOS, Linux). It finds the Android SDK (`ANDROID_HOME`) and Flutter (`PATH` or `FLUTTER_ROOT`), starts the first emulator (or `-Avd <name>` / `--avd <name>`), waits for it to boot and runs the app. Add `-Fresh` / `--fresh` to clear the app's data first, so you can try the model download from the start. More detail, including device tests, is in the README, "Demo app (Android)".

**The model.** The trained weights are not part of this repository; they are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector). A fresh install opens with "No model is installed yet", and counting is off until the model is downloaded. The app's home screen offers **Download the model**: the app fetches r50-v5 (about 172 MB) from Kaggle, checks its size and SHA-256 and then counts, with the notice "Demo: real model weights … not validated in the field".

## 7. Exercise in your own time: spec the desktop app with Spec Kit

About 45 minutes. In the session, Exercise 2 showed Spec Kit on stage. Here you run the whole flow yourself on a real feature: a desktop version of the demo app (Windows, macOS and Linux). You write the specification, the plan and the task list, but no code. Then you compare your result with ours in [`specs/003-desktop-app/`](../specs/003-desktop-app/).

The steps follow Spec Kit's own [quickstart](https://github.github.io/spec-kit/quickstart.html). Read it alongside this section for what each command does.

**You need:** this repository, cloned (section 1); `uv` and Spec Kit (section 4); and an agent with its command-line tool ([setup.md, An AI coding agent](setup.md#an-ai-coding-agent)). Any agent Spec Kit supports works; find its integration key in Spec Kit's [integrations list](https://github.github.io/spec-kit/reference/integrations.html). The examples use the agents from the workshop demos, run in VS Code: Antigravity (`agy`), Claude Code (`claude`) and Codex (`codex`). Naming them is not an endorsement; see [setup.md, An AI coding agent](setup.md#an-ai-coding-agent).

### Step 1. Start from a clean branch

This repository already contains our Spec Kit run, so remove it on a branch of your own first. Your answers then cannot copy ours, and `main` keeps ours for the comparison at the end:

```bash
git switch -c my-speckit-run
git rm -r -q .specify specs .claude/skills/speckit-*
git commit -m "Start the Spec Kit exercise from scratch"
```

### Step 2. Initialise Spec Kit in the repository

```bash
specify init --here --integration claude
```

Replace `claude` with your agent's key, for example `agy` or `codex`. `--here` sets Spec Kit up in the current folder instead of a new one; it asks before merging into a folder that is not empty (add `--force` to skip the question). It adds `.specify/` (templates, scripts, a blank constitution) and the `speckit-*` commands for your agent. Run `git status` to see exactly what it added. If it reformatted a file you already had, such as `.claude/settings.json`, `git diff` shows it and `git checkout -- <file>` puts it back.

### Step 3. Run the commands in your agent

Open the repository folder in VS Code, open your agent's panel, and run each command on its own, reading what it wrote before you go on. Type the text after each command as its argument. In Codex, type `$speckit-…` instead of `/speckit-…`.

1. **Constitution**: the project's rules, which every later step is checked against.

   > /speckit-constitution Derive the principles from this repository's README, AGENTS.md and docs/inference-contract.md. Include: a teaching demo, not a field tool; one inference contract, checked with golden fixtures; test-first; thresholds and rules fixed before results; photos and data stay on the device; models verified before use; reuse shared files and choose the simplest design.

2. **Specify**: *what* to build and *why*, with no technology named.

   > /speckit-specify Build a desktop version of the Trap Pest Counter demo app for Windows, macOS and Linux, with the same features as the phone app: pick or drop a light-trap photo, count rice black bug and white stemborer with a model running on the computer, show review flags, keep past counts, and download, import, switch, delete and compare models. English and Filipino.

3. **Clarify** (optional, recommended): `/speckit-clarify`. The agent asks up to five questions about gaps in the spec. Answer them; each answer is written back into the spec.

4. **Plan**: *how*: the stack, the design and the checks against the constitution. We deliberately left the stack open:

   > /speckit-plan Compare two stacks in research and choose one: adding Windows, macOS and Linux targets to the existing Flutter app in app/, or a new Tauri 2 app with a Rust core and a TypeScript interface. The inference contract and its golden fixtures must keep working.

5. **Checklist** (optional): `/speckit-checklist` tests the spec's requirements for completeness and clarity.

6. **Tasks**: `/speckit-tasks` turns the plan into a numbered task list, grouped by user story, with tests before code.

7. **Analyze** (optional): `/speckit-analyze` is a read-only check that the spec, plan and tasks agree with each other and with the constitution.

Stop here. `/speckit-implement` and `/speckit-converge` would build the app, which is not part of this exercise.

### Step 4. Compare with ours

Your files are under `specs/001-desktop-app/`: Spec Kit numbers features from 001, and your branch has no others. Ours is `specs/003-desktop-app/` on `main`, because `main` also holds the specs for the model (001) and the phone app (002). Compare them:

```bash
git diff main -- .specify/memory/constitution.md
git diff --no-index specs/001-desktop-app ../rice-pest-detector-main/specs/003-desktop-app
```

The second command needs a copy of `main` next to your clone (`git worktree add ../rice-pest-detector-main main`). Or simply open both on GitHub.

Questions to answer for yourself:

- Which stack did your plan choose, and which constitution principle decided it? Ours chose Flutter desktop: research R1 explains why, and the Tauri option is recorded as rejected.
- Did your Constitution Check pass, or did it need a Complexity Tracking entry?
- Which numbers did your spec put in its success criteria? Could you test each one?
- Did your agent write any requirement that names a technology? The spec should not.
- How many tasks did you get, and do the test tasks come before the code they test?

**Done when:** you have a constitution, a spec with no `[NEEDS CLARIFICATION]` left, a plan whose Constitution Check passes (or is justified), a task list, and your answers to the questions above.

**Clean up:** `git switch main`, then `git branch -D my-speckit-run`.

## If something does not work

- **An install fails** (`uv`, `specify`, Git, Python): see [setup.md, If something does not work](setup.md#if-something-does-not-work).
- **A work or school laptop blocks installs:** skip step 4 and pair with someone for Exercise 2, or ask your IT team before the day. Without Git, download the repository as a ZIP from its GitHub page instead.
- **No agent, or under 18 and none allowed:** you can still do Exercise 0 on paper and navigate for a partner in Exercises 1 and 2.

On the day, bring the laptop charged, and the agent signed in.
