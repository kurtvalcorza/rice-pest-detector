# Coding with AI Agents: the workshop, at your own pace

This page takes you through the *Coding with AI Agents* workshop on your own, in the same order as the session: six modules, three exercises, and a longer Spec Kit exercise to finish. Allow about three hours, in as many sittings as you like. There is no facilitator, so every exercise has a way to check your work and an answer to compare with.

**The slides.** Open `docs/presentations/coding-with-ai-agents-2h.html` from your clone in a web browser (GitHub shows the file's source, not the slides). Move with the arrow keys, and press **N** to show each slide's notes: the "About this slide" part says what the speaker said. Each module below gives its slide numbers. The "Presenting" part of the notes was for the speaker; skip it.

**What you need:** Git and this repository, an AI coding agent, an empty practice folder, and `uv` with Spec Kit for Module 3. Module 0 sets them up.

## Module 0. Introduction and set-up (slides 1–8, about 30 minutes)

Read slides 1–7: what the workshop covers, how it was made with AI, and why free tiers can train on what you type.

### Install what you need

Follow [setup.md](setup.md) for [Git](setup.md#git), [an AI coding agent](setup.md#an-ai-coding-agent) and [`uv` and Spec Kit](setup.md#uv-and-spec-kit), then clone this repository. Python, Flutter and the training tools are not needed. To see what you already have, [setup.md](setup.md#let-your-agent-check-what-is-installed) has a prompt that asks your agent to check, without installing anything.

### Set up your agent safely

1. **Check its terms.** Some agents exclude users under 18. Pick one whose terms allow you.
2. **Sign in once** and send it a test message.
3. **Switch training off.** Many free tiers may use what you type to improve their models. Find the data or training setting and turn it off.
4. **Know what not to paste.** Never paste personal or confidential material (company code, client data) or graded work. Everything in this workshop is safe to type.

Once your agent works, you can let it install the rest of what this workshop needs. Open it in the cloned `rice-pest-detector` folder and send:

> Read docs/workshop-setup.md and the "uv and Spec Kit" section of docs/setup.md. First tell me what is already installed and what is missing, and wait. Then make the practice folder and install only uv and Spec Kit, asking me before each command, and check that `specify --help` works. Do not change account, system or security settings, do not use admin rights, and do not install Flutter or Android tools.

Read its plan before you approve anything, and read each command before it runs: the `uv` installer downloads and runs a script from the internet. This is a small version of what the workshop is about. The repository's `AGENTS.md` repeats these limits for any agent that reads it.

### Make a practice folder

The exercises start from scratch, so keep them outside the cloned repository:

```bash
mkdir agents-practice
cd agents-practice
git init
```

With Git, every change the agent makes shows up in `git diff` and can be undone with `git restore .`.

### Exercise 0: one prompt (slide 8, 5 minutes)

The demo app counts rice pests in a photo of a light trap. An agent drafted it; a person directed every step. See it: the screenshots in the demo-app case study (open `docs/presentations/demo-app-process.html` in a browser), or run it yourself ([Optional: run the demo app](#optional-run-the-demo-app-on-an-emulator)).

Now **write down the one prompt you think built this app**. If you have an agent, try it in your practice folder and look at what comes back. Keep what you wrote: Module 1 shows how the app really started.

## Module 1. Direct (slides 9–18, about 15 minutes)

Read slides 9–18: why the one-shot prompt fails, the agent loop, `AGENTS.md`, and how to read a plan and when to stop the agent.

**Compare your Exercise 0 prompt** with slide 15, "How the app actually started", and with the "Behind the scenes: prompts used" slides in the demo-app case study. The first prompt was a question about the tech stack, not a build request, and fourteen short prompts followed, each settling a decision.

**Check yourself:** which decisions did your prompt leave to the agent? Typical gaps are the platform (phone, web or desktop), where the photos come from, what the model is and where it runs, what counts as "done", and what the app must never do (here: give spray or treatment advice).

## Module 2. Context (slides 19–35, about 40 minutes)

Read slides 19–33: an agent is a model plus a *harness*, context windows and why long sessions cost more, skills, hooks, sub-agents and MCP. The examples are real: `.claude/skills/`, `.claude/agents/` and `.claude/hooks/` in this repository.

### Exercise 1: conduct, do not one-shot (slide 34, 10 minutes)

In your practice folder, with your agent:

1. Take your Exercise 0 prompt.
2. Ask your agent for a plan first, and no code yet.
3. Read the plan: what did it assume? Correct one thing.
4. Approve one step only, and watch what it runs.
5. Stop it if it leaves the plan.

**Check yourself** (slide 35's debrief): name one assumption in the plan you corrected, a moment you would have stopped it, and something it never asked you.

<details>
<summary>What good answers look like</summary>

- **An assumption you corrected:** for example, it planned a web app when you meant a phone app, assumed it could train a model on the spot, or invented a data source.
- **A moment to stop it:** it installed packages or created files outside the step you approved, or started on step two.
- **What it never asked:** usually who the users are, what counts as done, how accurate the counts must be, and what it must never do. Those gaps are what a written spec closes, which is Module 3.

</details>

## Module 3. Specify (slides 36–62, about 45 minutes)

Read slides 36–59: what a spec is, the anatomy of a real one, acceptance criteria, and ten spec-driven frameworks compared. The real specs are in this repository: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) and [`specs/`](../specs/), for the model (001), the phone app (002) and a desktop app (003).

### Exercise 2: Spec Kit (slides 60–61, 15 minutes)

In a new folder, on an idea of your own (your Exercise 0 app is fine):

```bash
specify init my-project --integration <your-agent-key>
```

Your agent's key is in Spec Kit's [integrations list](https://github.github.io/spec-kit/reference/integrations.html), for example `agy`, `claude` or `codex`. Open the new folder in your agent and type in its chat (Codex uses `$speckit-…` instead of `/speckit-…`):

```text
/speckit-constitution   the ground rules for the project
/speckit-specify        what you want and why, not how
/speckit-clarify        let it ask about what is ambiguous
```

Read the `spec.md` it wrote.

**Check yourself** (slide 62's debrief): is the spec ready to build from? Every requirement has a number where it needs one, and every question clarify asked has an answer. Name one question clarify asked that your Exercise 0 prompt never answered, one gap it missed, and one requirement that needed a number. Compare with the counting rule in [`specs/002-mobile-app/spec.md`](../specs/002-mobile-app/spec.md): a detection counts when its score is at or above the model's threshold (0.48 for the default model), not "when the model is confident".

### Going further: the whole Spec Kit flow on the desktop app (about 45 minutes)

Here you run every step of Spec Kit's [quickstart](https://github.github.io/spec-kit/quickstart.html), on a real feature: a desktop version of the demo app. You write the specification, the plan and the task list, but no code, then compare with ours in [`specs/003-desktop-app/`](../specs/003-desktop-app/). Any agent Spec Kit supports works; the examples use `claude`, and you replace it with your agent's key.

#### Step 1. Start from a clean branch

This repository already contains our Spec Kit run, so remove it on a branch of your own first. Your answers then cannot copy ours, and `main` keeps ours for the comparison at the end:

```bash
git switch -c my-speckit-run
git rm -r -q .specify specs .claude/skills/speckit-*
git commit -m "Start the Spec Kit exercise from scratch"
```

#### Step 2. Initialise Spec Kit in the repository

```bash
specify init --here --integration claude
```

Replace `claude` with your agent's key, for example `agy` or `codex`. `--here` sets Spec Kit up in the current folder instead of a new one; it asks before merging into a folder that is not empty (add `--force` to skip the question). It adds `.specify/` (templates, scripts, a blank constitution) and the `speckit-*` commands for your agent. Run `git status` to see exactly what it added. If it reformatted a file you already had, such as `.claude/settings.json`, `git diff` shows it and `git checkout -- <file>` puts it back.

#### Step 3. Run the commands in your agent

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

#### Step 4. Compare with ours

Your files are under a folder such as `specs/001-desktop-app/` (Spec Kit picks the name): Spec Kit numbers features from 001, and your branch has no others. Ours is `specs/003-desktop-app/` on `main`, because `main` also holds the specs for the model (001) and the phone app (002). Compare them:

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

## Module 4. Guard (slides 63–71, about 15 minutes)

Read slides 63–71: the agent acts with your permissions, prompt injection (including through files you ask it to review), the "lethal trifecta", secrets and sandboxes.

**Do it:** open your agent's settings and check the six safe defaults on slide 71 against them: approvals on; network off unless the task needs it; no secrets in the repository; edits scoped to the folders the task needs; every command reviewed before it runs; every new dependency checked. Which one would be hardest to keep in your own work, and what would make it easier?

## Module 5. Share (slides 72–83, about 20 minutes)

Read slides 72–83: how an agent built the real app, licences, the model behind it, and how teams use agents. Then go deeper:

- **Training the model:** `docs/presentations/model-training.html`, and [`specs/001-model-training/`](../specs/001-model-training/).
- **Building the app:** `docs/presentations/demo-app-process.html`, and [`specs/002-mobile-app/`](../specs/002-mobile-app/).
- **Agent harnesses and context engineering:** `docs/presentations/harness-context-engineering.html`.

**The five takeaways:** conduct the agent, do not one-shot it; write the spec before the code; put the rules that matter in hooks, tests and CI; treat text from outside as untrusted; an agent drafts, a person decides and stays accountable.

### Going further: train the model yourself (about 7 hours, mostly waiting)

The model-training case study shows how the detector was trained. Here you start a training run of the demo model's recipe (r50-v5) yourself, on a free Colab GPU, and compare your numbers with the published ones. You need a Google account with at least 20 GB free in Google Drive and a browser; nothing is installed on your computer ([setup.md, Training](setup.md#training)).

1. **Open the notebook.** Open [`notebooks/train_colab_r50v5.ipynb` in Colab](https://colab.research.google.com/github/kurtvalcorza/rice-pest-detector/blob/main/notebooks/train_colab_r50v5.ipynb) (the badge in the README, "Training on Colab", does the same).
2. **Choose a GPU.** Runtime → Change runtime type → **T4 GPU**. The notebook stops early if no GPU is attached.
3. **Leave the settings as they are.** The notebook runs the published recipe unchanged: 40 epochs, which took 6.2 hours on a T4 for the published run. Keep the browser tab open; a free Colab session can end before that, and Run all then picks up where it stopped (step 4).

   *Short on time?* The published run's best checkpoint came at epoch 1 (counting from 0). You can change `epochs=40` to a smaller number in the cell that starts `from rice_pest_detector.train import`, but then it is your own experiment: the learning-rate schedule spreads over the epochs you choose, so your numbers will differ from the published run's.
4. **Run it.** Runtime → Run all, and accept the Google Drive prompt. The notebook installs its packages, downloads the dataset from Zenodo and checks every image (about 20 minutes), then trains (about 9 minutes per epoch on a T4). If Colab disconnects, choose Run all again: training resumes from Drive.
5. **The last cell stops on purpose.** It refuses to evaluate on the test photos (`THRESHOLD = None`): in this project the test split is looked at only under rules written down in advance (constitution Principle IV). The run is finished when the training cell prints the path of `best.pt`.
6. **Release the GPU.** Runtime → Disconnect and delete runtime, so the run stops using your Colab quota.

**Check yourself.** In Google Drive, open `rice-pest-detector/run-r50v5/best.json`: it holds your best validation species mAP50 (`map50_species`) and the epoch it came from; `history.jsonl` beside it has one line per epoch. Compare with the published r50-v5 run in [`docs/evaluation-record.md`](evaluation-record.md) ("Wave 2"): 0.937 at epoch 1. Then answer: why is the threshold for counting chosen on validation photos and never on test photos? (The model-training case study and [`specs/001-model-training/research.md`](../specs/001-model-training/research.md), R6, explain it.)

**With your agent.** This is a good place to practise Module 2: ask your agent to explain what the `fit` cell and `src/rice_pest_detector/train.py` do before you run them, and check its explanation against the README, "What the training loop guarantees". To start runs from a terminal or let an agent drive Colab, see [setup.md, Colab CLI](setup.md#colab-cli-optional) and [MCP](setup.md#let-your-agent-work-with-colab-and-kaggle-mcp).

**After training.** Choosing a counting threshold, exporting to ONNX and checking parity with PyTorch run on your computer with the Python tools ([setup.md, Python tools and tests](setup.md#python-tools-and-tests)); the steps are in the README, "Evaluation", "Export to ONNX and parity" and "Choosing a demo threshold". An exported model can be imported into the demo app from Settings, where it is marked "Demo model, not validated".

## Optional: run the demo app on an emulator

Not needed for the session. Install Flutter, Android Studio and an emulator first: [setup.md, Demo app](setup.md#demo-app-optional) (allow one to two hours the first time). Then start the emulator and, from the repository's `app/` folder:

```bash
flutter run --no-enable-impeller -d emulator-5554
```

The `--no-enable-impeller` flag avoids a hang on emulators without a graphics card. Or let a script do the starting, waiting and running: `.\tools\run_emulator.ps1` (Windows PowerShell) or `tools/run_emulator.sh` (macOS, Linux). It finds the Android SDK (`ANDROID_HOME`) and Flutter (`PATH` or `FLUTTER_ROOT`), starts the first emulator (or `-Avd <name>` / `--avd <name>`), waits for it to boot and runs the app. Add `-Fresh` / `--fresh` to clear the app's data first, so you can try the model download from the start. More detail, including device tests, is in the README, "Demo app (Android)".

**The model.** The trained weights are not part of this repository; they are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector). A fresh install opens with "No model is installed yet", and counting is off until the model is downloaded. The app's home screen offers **Download the model**: the app fetches r50-v5 (about 172 MB) from Kaggle, checks its size and SHA-256 and then counts, with the notice "Demo: real model weights … not validated in the field".

## If something does not work

- **An install fails** (`uv`, `specify`, Git, Python): see [setup.md, If something does not work](setup.md#if-something-does-not-work).
- **No agent, or under 18 and none allowed:** you can still read the slides, do Exercise 0 on paper, and read the plans and specs in this repository; or pair with someone who has an agent and read every action before it is approved.
- **A work or school laptop blocks installs:** ask your IT team, or use a personal machine.
