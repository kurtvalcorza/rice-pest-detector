# Formal specification (Lean 4)

Machine-checked proofs about small, deterministic pieces that the release gates and the app
depend on. This covers neither the model nor the notebooks: whether the detector finds insects is
a measurement, recorded in [docs/evaluation-record.md](../docs/evaluation-record.md).

| File | Models | Proved |
| :-- | :-- | :-- |
| `RicePest/Tolerance.lean` | `metrics.count_within_tolerance` | the accepted counts are exactly `ref ± 1` below 10 and `ref ± ⌊ref/10⌋` from 10 up; a closer count never fails where a farther one passes |
| `RicePest/Postprocess.lean` | `infer.postprocess`, `app/lib/inference/postprocess.dart` | output is sorted by score with ties in query order; it keeps exactly the queries at or above the threshold; filter-then-sort equals sort-then-filter; a higher threshold keeps a prefix, so species counts never rise; the class is the first highest logit |
| `RicePest/Families.lean` | `dedup.group_families` | close families (any hashes within `max_distance` bits) always share a group, so any split chosen per group keeps them together (no train/test leakage); families share a group only if a chain of close families links them |

The proofs use Lean's core library only (no Mathlib): a build from scratch takes under a minute.
`lake build` fails if a proof is incomplete or cheats:
- `lakefile.toml` turns warnings into errors, so a `sorry` fails, and it builds every module under
  `RicePest/`, imported or not;
- `AxiomAudit.lean` fails if any `RicePest` declaration depends on an axiom other than `propext`,
  `Classical.choice` and `Quot.sound`. That catches a new `axiom`, `native_decide`, and a `sorry`
  even under `set_option warningAsError false`.

## How the proofs reach the real code

A proof is about the Lean model, not about the Python or Dart source. The link is a fixture file:
`Fixtures.lean` runs the proved specification on fixed inputs and writes
`app/test/fixtures/lean_spec_fixtures.json`, and two tests check the real code against it:

- `tests/test_lean_spec.py`: Python `postprocess`, `count_within_tolerance` and `group_families`
- `app/test/lean_spec_test.dart`: Dart `postprocess`

`tests/test_properties.py` checks the same properties on random inputs with Hypothesis.

The grouping is proved for a simpler algorithm than the Python union-find: labels spread the
smallest family index across close families until nothing changes. The fixtures check that the
union-find gives the same groups on 60 generated cases, 23 of which need a chain to merge. The
proof assumes the rounds settle within `n + 1` (the generator fails if they do not), and the
fixture hashes use 63 bits, not 64, so the Dart tests can read the same file.

The model scores queries by logit, which matches scoring by probability because the sigmoid is
increasing. In float64 that holds for the fixtures' logits in [-3, 3]. It stops holding once two
distinct logits give the same float64 sigmoid, which already happens near 24 (from 36.8 every
logit gives exactly 1.0, and below about -710 exactly 0.0). There the spec no longer models the
code: the order, the class chosen (the code takes the first of the merged classes) and the
threshold decision can all differ, and so can a species count. NaN logits are not modelled.

## Commands

Install Lean with [elan](https://lean-lang.org/install/), then, in this folder:

```
lake build                  # check every proof
lake exe fixtures           # regenerate the fixture file after changing the specification
lake exe fixtures --check   # what CI runs: fail if the committed fixtures are stale
```
