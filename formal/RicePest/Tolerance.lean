/-!
# Count tolerance (`rice_pest_detector.metrics.count_within_tolerance`)

The ship gate counts an image as correct for a species when the predicted count is within
±1 of the reference below 10, and within 10 percent of it from 10 up. Python writes the second
case as `abs(pred - ref) <= 0.10 * ref` in floating point; here it is the exact integer rule
`10 * |pred - ref| ≤ ref`. `tests/test_properties.py` checks that the float version agrees
with this rule.
-/

namespace RicePest

/-- `|a - b|` on natural numbers. -/
def dist (a b : Nat) : Nat := if a ≤ b then b - a else a - b

/-- The tolerance rule, in exact arithmetic. -/
def withinTolerance (pred ref : Nat) : Bool :=
  if ref < 10 then dist pred ref ≤ 1 else 10 * dist pred ref ≤ ref

theorem withinTolerance_self (ref : Nat) : withinTolerance ref ref = true := by
  unfold withinTolerance dist; split <;> simp

/-- A prediction at least as close to the reference never fails where a farther one passes. -/
theorem withinTolerance_of_closer {p₁ p₂ ref : Nat} (hclose : dist p₁ ref ≤ dist p₂ ref)
    (h : withinTolerance p₂ ref = true) : withinTolerance p₁ ref = true := by
  unfold withinTolerance at *
  split <;> simp_all <;> omega

/-- Closed form from 10 up: the accepted predictions are exactly
`ref - ⌊ref / 10⌋ ≤ pred ≤ ref + ⌊ref / 10⌋`. -/
theorem withinTolerance_band {pred ref : Nat} (h : 10 ≤ ref) :
    withinTolerance pred ref = true ↔ ref - ref / 10 ≤ pred ∧ pred ≤ ref + ref / 10 := by
  unfold withinTolerance dist
  have : ¬ ref < 10 := by omega
  simp only [this, ite_false, decide_eq_true_eq]
  split <;> omega

/-- Below 10 the accepted predictions are `ref - 1 ≤ pred ≤ ref + 1`. -/
theorem withinTolerance_small {pred ref : Nat} (h : ref < 10) :
    withinTolerance pred ref = true ↔ ref - 1 ≤ pred ∧ pred ≤ ref + 1 := by
  unfold withinTolerance dist
  simp only [h, ite_true, decide_eq_true_eq]
  split <;> omega

/-- An accepted prediction is never further than ±1 or ±10 percent (rounded down) away. -/
theorem withinTolerance_width {pred ref : Nat} (h : withinTolerance pred ref = true) :
    dist pred ref ≤ max 1 (ref / 10) := by
  unfold withinTolerance at h
  split at h <;> simp at h <;> omega

end RicePest
