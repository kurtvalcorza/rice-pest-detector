# Contributing

This is a teaching repository. It shows how to build software with AI coding agents, using a rice-pest detector and a demonstration Android app as the worked example. It is maintained on a best-effort basis, with no guaranteed response time. It is not a tool for farmers and it is not an official product (see the notice in [README.md](README.md)).

## Report a bug

Open an issue with the **Bug report** form. Include:

- what happened and what you expected
- the steps to reproduce it
- your environment: operating system, Python or Flutter version
- which part is affected: notebooks, tools, app or docs

## Ask a workshop question

Use the [Q&A category in Discussions](https://github.com/kurtvalcorza/rice-pest-detector/discussions/categories/q-a), not an issue.

## Propose a change

1. Fork the repository and create a branch.
2. Follow the approach the repository teaches: write or update the spec, then the plan, then a failing test, then the code.
3. Keep the change small and focused on one thing.
4. Run the tests before you open a pull request:
   - Python, from the repository root: `python -m pytest`
   - App, from `app/`: `flutter analyze && flutter test`
5. Open a pull request against `main` and say what changed and why. The CI checks must pass.

Do not commit model weights (`*.onnx`, `*.pt`, `*.safetensors`) or dataset images. Weights are published on Kaggle and the dataset is downloaded from Zenodo.

## Security

Do not report vulnerabilities in a public issue. See [SECURITY.md](SECURITY.md).

## Conduct

Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
