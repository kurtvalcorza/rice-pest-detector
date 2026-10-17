# AGENTS.md

Instructions for AI coding agents working in this repository.

## What this is

A rice-pest detector (Python: data pipeline, training, ONNX export) and a Flutter demo app (`app/`). The README explains the project; `docs/evaluation-record.md` records every result. The trained weights are not in this repository.

## Setting up for the Coding with AI Agents session

If you are asked to set this repository up for the workshop, follow `docs/workshop-setup.md` and nothing else:

- First report what is already installed and what is missing, then wait for the person to confirm.
- Install only what that guide lists for the session (`uv` and Spec Kit). Ask before each install command, and show the command first.
- Do not use admin rights, and do not change account, system or security settings.
- Do not install Flutter, Android Studio or other large tools unless the person asks for the optional emulator section.
- Do not accept licences or terms on the person's behalf.

## Working on the code

- Python: run `python -m pytest` before saying a change is done.
- App: run `flutter test` in `app/`. A Stop hook (`.claude/hooks/require_green_tests.py`) blocks finishing while it fails.
- Never commit model weights, `.env` files or credentials.
