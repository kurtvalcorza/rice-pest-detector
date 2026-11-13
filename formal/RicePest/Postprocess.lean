/-!
# Post-processing (`rice_pest_detector.infer.postprocess`, `app/lib/inference/postprocess.dart`)

Both implementations take the model's 300 queries, score each query by its best class, keep the
queries whose score is at or above the threshold, and sort them by score with ties in query
order. There is no NMS.

The model here works on logits, as integers in eighths, instead of on sigmoid probabilities.
The sigmoid is strictly increasing, so ordering and thresholding by logit is the same as by
probability, provided the threshold is given as a logit. The fixture generator (`Fixtures.lean`)
keeps logits in `[-3, 3]`, where float64 never merges two distinct values, and uses thresholds
that no logit equals (or exactly 0, whose sigmoid 0.5 is exact).

Outside that range the spec stops modelling the code once two distinct logits give the same
float64 sigmoid, which already happens near 24 (from 36.8 every logit gives exactly 1.0, and below
about -710 exactly 0.0). There the order, the class chosen (the code takes the first of the merged
classes) and the threshold decision can all differ, and so can a species count. A NaN logit is
not modelled either.

What is proved:
* `postprocess_sorted`: output is sorted by score, ties by query index.
* `mem_postprocess`, `length_postprocess`: it keeps exactly the queries at or above the threshold.
* `postprocess_eq_filter_sort`: filtering then sorting (what the code does) equals sorting then
  filtering.
* `postprocess_prefix`: a higher threshold keeps a prefix of the lower threshold's output.
* `countP_postprocess_antitone`: so the count of any species never rises with the threshold.
* `bestOf_spec`: the class chosen for a query is the first class with the highest logit.
-/

namespace RicePest

/-- One model query after taking its best class. `score` is that class's logit, in eighths. -/
structure Query where
  idx : Nat
  score : Int
  cls : Nat
deriving Repr, DecidableEq

/-- `a` is output no later than `b`: higher score first, then lower query index. The class only
breaks a tie between equal indices, which never happens for real queries; it makes the order
antisymmetric, so the sorted output is unique. -/
def before (a b : Query) : Bool :=
  decide (b.score < a.score) ||
    (decide (a.score = b.score) &&
      (decide (a.idx < b.idx) || (decide (a.idx = b.idx) && decide (a.cls ≤ b.cls))))

theorem before_trans : ∀ a b c : Query, before a b → before b c → before a c := by
  intro a b c hab hbc
  simp only [before, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq] at *
  omega

theorem before_total : ∀ a b : Query, (before a b || before b a) = true := by
  intro a b
  simp only [before, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  omega

theorem before_antisymm : ∀ a b : Query, before a b → before b a → a = b := by
  intro ⟨i, s, c⟩ ⟨i', s', c'⟩ hab hba
  simp only [before, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq] at *
  have : i = i' ∧ s = s' ∧ c = c' := by omega
  obtain ⟨rfl, rfl, rfl⟩ := this
  rfl

/-- Kept at threshold `t` (in eighths of a logit). -/
def keep (t : Int) (q : Query) : Bool := decide (t ≤ q.score)

/-- The specification: filter by threshold, then sort. -/
def postprocess (qs : List Query) (t : Int) : List Query :=
  (qs.filter (keep t)).mergeSort before

/-- Two permutations of each other that are both sorted by an antisymmetric relation are equal. -/
theorem eq_of_perm_of_pairwise {R : α → α → Prop} (anti : ∀ a b, R a b → R b a → a = b) :
    ∀ {l₁ l₂ : List α}, l₁.Perm l₂ → l₁.Pairwise R → l₂.Pairwise R → l₁ = l₂
  | [], _, hp, _, _ => (List.Perm.nil_eq hp)
  | a :: as, [], hp, _, _ => absurd hp.length_eq (by simp)
  | a :: as, b :: bs, hp, h₁, h₂ => by
    have ha : a ∈ b :: bs := hp.mem_iff.mp (List.mem_cons_self ..)
    have hb : b ∈ a :: as := hp.mem_iff.mpr (List.mem_cons_self ..)
    have hab : a = b := by
      rcases List.mem_cons.mp ha with h | h
      · exact h
      rcases List.mem_cons.mp hb with h' | h'
      · exact h'.symm
      exact anti a b ((List.pairwise_cons.mp h₁).1 b h') ((List.pairwise_cons.mp h₂).1 a h)
    subst hab
    rw [eq_of_perm_of_pairwise anti (List.perm_cons a |>.mp hp) h₁.tail h₂.tail]

theorem postprocess_sorted (qs : List Query) (t : Int) :
    (postprocess qs t).Pairwise (fun a b => before a b = true) :=
  List.pairwise_mergeSort before_trans before_total _

theorem mem_postprocess {q : Query} {qs : List Query} {t : Int} :
    q ∈ postprocess qs t ↔ q ∈ qs ∧ t ≤ q.score := by
  simp [postprocess, keep]

theorem length_postprocess (qs : List Query) (t : Int) :
    (postprocess qs t).length = qs.countP (keep t) := by
  simp [postprocess, List.length_mergeSort, List.countP_eq_length_filter]

/-- Filtering then sorting, as the Python and Dart code do, equals sorting then filtering. -/
theorem postprocess_eq_filter_sort (qs : List Query) (t : Int) :
    postprocess qs t = (qs.mergeSort before).filter (keep t) :=
  eq_of_perm_of_pairwise (R := fun a b => before a b = true) before_antisymm
    ((List.mergeSort_perm _ _).trans ((List.mergeSort_perm qs before).filter (keep t)).symm)
    (postprocess_sorted qs t)
    ((List.pairwise_mergeSort before_trans before_total qs).filter _)

/-- On a list sorted by `before`, filtering by a threshold keeps a prefix. -/
theorem filter_keep_eq_takeWhile (t : Int) :
    ∀ {l : List Query}, l.Pairwise (fun a b => before a b = true) →
      l.filter (keep t) = l.takeWhile (keep t)
  | [], _ => rfl
  | y :: ys, h => by
    by_cases hy : keep t y = true
    · rw [List.filter_cons_of_pos hy, List.takeWhile_cons_of_pos hy,
        filter_keep_eq_takeWhile t (List.pairwise_cons.mp h).2]
    · have hnil : ys.filter (keep t) = [] := by
        rw [List.filter_eq_nil_iff]
        intro x hx hkx
        have hyx := (List.pairwise_cons.mp h).1 x hx
        simp only [keep, before, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq] at hy hkx hyx
        omega
      rw [List.filter_cons_of_neg hy, List.takeWhile_cons_of_neg hy, hnil]

/-- Raising the threshold keeps a prefix of the output. -/
theorem postprocess_prefix (qs : List Query) {t₁ t₂ : Int} (h : t₁ ≤ t₂) :
    postprocess qs t₂ <+: postprocess qs t₁ := by
  have hfilter : postprocess qs t₂ = (postprocess qs t₁).filter (keep t₂) := by
    rw [postprocess_eq_filter_sort, postprocess_eq_filter_sort, List.filter_filter]
    congr 1
    funext q
    simp only [keep]
    by_cases hq : t₂ ≤ q.score
    · have : t₁ ≤ q.score := by omega
      simp [hq, this]
    · simp [hq]
  rw [hfilter, filter_keep_eq_takeWhile t₂ (postprocess_sorted qs t₁)]
  exact List.takeWhile_prefix _

/-- So the count of any species (any predicate on the class) never rises with the threshold. -/
theorem countP_postprocess_antitone (qs : List Query) (species : Nat → Bool) {t₁ t₂ : Int}
    (h : t₁ ≤ t₂) :
    (postprocess qs t₂).countP (fun q => species q.cls) ≤
      (postprocess qs t₁).countP (fun q => species q.cls) :=
  (postprocess_prefix qs h).sublist.countP_le

/-! ## Best class of a query -/

/-- Index and value of the first maximum (`numpy.argmax`; Dart keeps the first `p > best`). -/
def bestOf : List Int → Option (Nat × Int)
  | [] => none
  | x :: xs =>
    match bestOf xs with
    | none => some (0, x)
    | some (i, v) => if v ≤ x then some (0, x) else some (i + 1, v)

theorem bestOf_cons_ne_none (x : Int) (xs : List Int) : bestOf (x :: xs) ≠ none := by
  simp only [bestOf]
  split
  · simp
  · split <;> simp

theorem bestOf_spec : ∀ {l : List Int} {i : Nat} {v : Int}, bestOf l = some (i, v) →
    l[i]? = some v ∧ (∀ y ∈ l, y ≤ v) ∧ (∀ j y, j < i → l[j]? = some y → y < v)
  | [], _, _, h => by simp [bestOf] at h
  | x :: xs, i, v, h => by
    unfold bestOf at h
    split at h
    · rename_i hnone
      simp only [Option.some.injEq, Prod.mk.injEq] at h
      obtain ⟨rfl, rfl⟩ := h
      have : xs = [] := by
        cases xs with
        | nil => rfl
        | cons y ys => exact absurd hnone (bestOf_cons_ne_none y ys)
      subst this
      simp
    · rename_i i' v' hsome
      obtain ⟨hget, hmax, hfirst⟩ := bestOf_spec hsome
      split at h
      · rename_i hle
        simp only [Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        refine ⟨rfl, ?_, fun j y hj => absurd hj (Nat.not_lt_zero _)⟩
        intro y hy
        rcases List.mem_cons.mp hy with rfl | hy
        · exact Int.le_refl _
        · exact Int.le_trans (hmax y hy) hle
      · rename_i hlt
        simp only [Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        refine ⟨by simpa using hget, ?_, ?_⟩
        · intro y hy
          rcases List.mem_cons.mp hy with rfl | hy
          · omega
          · exact hmax y hy
        · intro j y hj hjy
          cases j with
          | zero => simp at hjy; omega
          | succ j => exact hfirst j y (by omega) (by simpa using hjy)

/-- Queries from a model's logits (one row of class logits per query, in eighths). -/
def queriesOf (rows : List (List Int)) : List Query :=
  (rows.zipIdx).filterMap fun (row, q) => (bestOf row).map fun (c, v) => ⟨q, v, c⟩

end RicePest
