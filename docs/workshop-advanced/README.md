# Advanced track: engineering a controlled agent workflow

The core course teaches you to use a coding agent. This optional track teaches you to control one: to decide what counts as done, check it with something other than the agent's word, and stop the work when nothing can be checked. You work on this repository's real inference code, not on a toy.

**This repository is a teaching demo.** Passing its tests shows that the code does what its written contract says. It does not show that the model is accurate, validated in the field or suitable for decisions about crops; no model here has been validated in the field.

## Who it is for

You have finished the core course in [workshop-setup.md](../workshop-setup.md): Modules 0–4 and Exercise 1. You can read a short Python function and a test, run a command in a terminal, and review an agent's diff before you approve it. You do not need to know machine learning.

## The modules

The modules build on each other: Module 7 reuses Module 6's verifier and regression, and Module 8 reuses both.

| Module | What you do | Time | Status |
| :-- | :-- | :-- | :-- |
| [6. Engineer: protect the inference contract](module-6-engineer.md) | Break the detector's preprocessing on purpose in a throwaway worktree, see which controls notice, and build a verifier that says PASS, FAIL or UNVERIFIED | 45–60 minutes | Ready |
| 7. Orchestrate: a bounded agent loop | Run the agent in a loop that repairs on FAIL, stops on UNVERIFIED, and gives up after a fixed number of tries | 60–75 minutes | Not written yet |
| 8. Automate: from issue to verified pull request | In your own fork, take an issue to a pull request that CI and a person check before anything merges | 60–90 minutes | Not written yet |

The whole track takes about 2.75–3.75 hours. Each module ends with items in the [evidence checklist](evidence-checklist.md).

## What you need

- Git and your clone of this repository: [setup.md, Git](../setup.md#git).
- `uv`: [setup.md, uv and Spec Kit](../setup.md#uv-and-spec-kit). It fetches Python 3.12 and the few packages each module needs; you do not need PyTorch, Flutter, an emulator or model weights.
- A coding agent you are allowed to use: [setup.md, An AI coding agent](../setup.md#an-ai-coding-agent).
- Your `agents-practice` folder from Module 0, **next to your clone** (both in the same parent folder). The commands use `../agents-practice`.
- For Module 8 only: a GitHub account and the GitHub CLI. Without them you can still read Module 8 and compare with the reference evidence.

**Agents.** Any coding agent you are allowed to use works. Where these pages name agents, they name them only as examples, in alphabetical order (for example Antigravity, Claude Code, Codex). Naming them is not a recommendation or an endorsement; see the note in [setup.md, "An AI coding agent"](../setup.md#an-ai-coding-agent).

## Glossary

- **Verifier.** A script that runs the tests and reports the result from a fresh test report, not from what anyone says. Here it answers PASS, FAIL or UNVERIFIED.
- **Fail-open.** A check that lets work through when it cannot decide. The repository's Stop hook is fail-open on purpose.
- **Fail-closed.** A check that refuses when it cannot decide. The verifier is fail-closed: "could not run" is UNVERIFIED, never PASS.
- **Regression.** A change that breaks something that used to work. A regression test fails when that happens.
- **Worktree.** A second working folder for the same Git repository, on its own branch. You break things there and remove it with one command.
- **Fork.** Your own copy of a repository on GitHub. Module 8 works only in your fork, never in this repository.
- **State machine.** A fixed set of states (for example run, repair, blocked, done) and the rules for moving between them. Module 7's loop is one.
- **Evidence bundle.** The files a run leaves behind (`verification.json`, `run.log`, `junit.xml`) so that anyone can check the result without trusting an account of it.

## Getting help

Ask your agent first: give it the page, the command you ran and the full output. If that does not settle it, see [Getting help](../workshop-setup.md#getting-help) in the core course.
