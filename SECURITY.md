# Security policy

This is a teaching and demonstration project (see the notice in [README.md](README.md)). It is maintained on a best-effort basis, with no guaranteed response time, but security reports are welcome and taken seriously.

## Reporting a vulnerability

Please report privately, not in a public issue:

- use GitHub's **Report a vulnerability** button on this repository's **Security** tab (private vulnerability reporting), or
- if that is unavailable, open an issue that says only that you have a security report and asks for a private channel, without the details.

Include what you found, how to reproduce it, and which file or version it affects. Please give the maintainers a reasonable time to respond before disclosing it publicly.

## In scope

- **Model download and import in the demo app** (`app/lib/model/`): any way to make the app load a model file whose size or SHA-256 does not match its pin or manifest, or to bypass the import checks (size, SHA-256, input/output shape, self-test).
- **The published model files** on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector): a file that does not match the SHA-256 recorded in `models/*.manifest.json`.
- **Agent configuration** (`AGENTS.md`, `.claude/`, `.agents/`): anything that would make a coding agent opened in this repository run unexpected commands, read secrets or reach the network beyond what the files describe. The Stop hook in `.claude/hooks/` runs the test suite; it can be switched off with `RICE_PEST_STOP_HOOK=off`.
- **Training notebooks** (`notebooks/`): anything that downloads or runs code other than the pinned packages, the pinned base model revisions and the dataset archive from Zenodo.
- **Secrets** accidentally committed to the repository.

## Out of scope

- The accuracy of the counts. The models are teaching demos, not validated in the field; wrong counts are a known limitation (see `docs/model-card.md`), not a security issue.
- Vulnerabilities in third-party packages (Flutter, ONNX Runtime, PyTorch, transformers and others): please report those upstream. Reports that this repository pins an affected version are welcome.
- Google Colab, Kaggle, Hugging Face and GitHub themselves.

## Supported versions

Only the latest commit on `main` is maintained.
