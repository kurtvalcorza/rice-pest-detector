<!--
Sync Impact Report
- Version change: template (unversioned) → 1.0.0 (first ratification; MAJOR 1 because this is the
  initial adoption, not an amendment)
- Principles defined: I. Teaching Demo, Not a Field Tool; II. One Inference Contract;
  III. Test-First, Green Before Done; IV. Rules Fixed Before Results; V. Local and Private by Default;
  VI. Verified Models Only; VII. Shared Sources, Simplest Thing
- Added sections: Additional Constraints; Development Workflow; Governance
- Removed sections: none
- Templates: .specify/templates/plan-template.md ✅ no change needed (its Constitution Check gate
  reads this file at run time); spec-template.md ✅ no change needed; tasks-template.md ✅ no change
  needed (tests-first ordering is compatible with Principle III)
- Runtime guidance: AGENTS.md ✅ consistent (tests before done; no weights or credentials committed)
- Deferred TODOs: none
-->

# Rice-Pest Detector Constitution

## Core Principles

### I. Teaching Demo, Not a Field Tool

Everything this repository ships is a teaching and demonstration artefact.

- Every app MUST show a not-validated notice while any model is in use, and a "demo model, not
  validated" banner whenever the active model is not the default.
- No user-facing string MAY suggest a treatment, spray or other pest-management action; each app
  MUST have a test that fails if one does.
- Counts MUST be presented as experimental estimates. No text MAY address farmers as the intended
  users or imply an endorsement by any organisation.

Rationale: no model here has been validated in the field (README, release gates 2–6).

### II. One Inference Contract

`docs/inference-contract.md` and its reference implementation `src/rice_pest_detector/infer.py`
define how a photo becomes counts: EXIF orientation, RGB, Pillow-bilinear resize to the model's
input size, ÷255 with no normalisation, NCHW `pixel_values`, sigmoid then max over four classes,
inclusive `score >= threshold`.

- Every client (phone, desktop, CLI) MUST implement this contract and MUST pass the golden fixtures
  generated from the Python reference (`app/test/fixtures/`), at the tolerance those fixtures state.
- A change to the contract MUST update the reference, the fixtures and every client in the same
  change.
- Where a client cannot match a step byte for byte, the difference MUST be measured and recorded
  (as the phone app records its JPEG decoder difference).

### III. Test-First, Green Before Done (NON-NEGOTIABLE)

- New behaviour starts with a test that fails for the right reason, then the code that makes it
  pass.
- A change is not done until its project's whole suite passes (`python -m pytest`, `flutter test`,
  and the suite of any new client), locally and in CI.
- Generated files (fixtures, notebooks, decks) MUST have a `--check` mode, and CI MUST run it.

### IV. Rules Fixed Before Results

- Thresholds, calibration and model choice MUST be fixed on the validation split. The test split is
  looked at only under rules written down before the look.
- Every reported number MUST be traceable to `docs/evaluation-record.md` with its run, split and
  date.
- A client MUST NOT invent its own thresholds: it uses the model manifest's `threshold` and
  `review_below`.

### V. Local and Private by Default

- Photos and count history MUST stay on the user's device, in app-private storage.
- The only network access allowed is a model download the user starts, to a URL in the bundled
  catalogue or pin. No analytics, no telemetry, no background calls.
- Sharing MUST happen only through an explicit user action.

### VI. Verified Models Only

- A model MUST NOT be used until its size and SHA-256 match its manifest, its ONNX input and output
  names and shapes match the contract, and a synthetic-photo self-test gives finite outputs of the
  right shape.
- Manifests are strict: unknown or missing fields are rejected.
- A failed download, import or check MUST leave the previous model in use and remove partial files.

### VII. Shared Sources, Simplest Thing

- A new client MUST read shared facts (model catalogue, model pin, manifests, UI strings, history
  format) from the files that already define them, not from copies.
- Choose the simplest design that meets the spec; any extra layer, dependency or abstraction MUST be
  justified in the plan's Complexity Tracking.

## Additional Constraints

- Model weights, `.env` files and credentials MUST NOT be committed. Weights are published
  separately and fetched by URL with a pinned SHA-256.
- Third-party models, datasets and libraries keep their own licences; each is attributed in
  `NOTICE` or the model card.
- The dataset is credited as "its authors (Deleña et al.)", without claims about where it was
  captured.
- Supported platforms MUST be stated per client, with the tested versions of its toolchain.

## Development Workflow

- Specs before code: a feature starts as a spec (`/speckit-specify`), then a plan and tasks; code
  follows the tasks in milestones, each ending with green tests and a commit.
- Pull requests MUST pass CI (Python tests, Flutter tests and every `--check`) before merging.
- Results, decisions and their dates are recorded in `docs/evaluation-record.md` and
  `docs/decisions.md`.

## Governance

This constitution overrides other practice in this repository. Every plan MUST pass its
Constitution Check before research and again after design; a violation is either fixed or justified
in Complexity Tracking.

Amendments are made by pull request that states the change, its reason and its version bump, and
updates any template or guidance it affects. Versioning: MAJOR for removing or redefining a
principle, MINOR for adding one or materially expanding guidance, PATCH for wording. Reviewers check
compliance on every pull request.

**Version**: 1.0.0 | **Ratified**: 2026-10-19 | **Last Amended**: 2026-10-19
