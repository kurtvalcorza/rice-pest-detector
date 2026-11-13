/-!
# Family grouping and leakage (`rice_pest_detector.dedup.group_families`)

Photos are first grouped into families (all export variants of one source photo). Two families
are *close* when any of their perceptual hashes differ in at most `max_distance` bits. Families
are then merged into groups, and the split assigns whole groups to train, val or test. The
leakage guarantee is that two close families never end up in different splits.

The Python code merges with a union-find. Here the grouping is a different, simpler algorithm
whose correctness is proved: every family starts labelled with its own index, and each round
takes the smallest label among itself and its close neighbours, until nothing changes. The
fixtures check that Python's groups equal these on generated inputs.

What is proved, for any symmetric closeness relation on families `0 … n-1`:
* `groups_close`: two close families get the same label (no leakage).
* `groups_connected`: two families with the same label are linked by a chain of close families
  (groups are no coarser than they must be).
* `groups_split_no_leakage`: so any split decided per group keeps close families together.

`groups` stops after `n + 1` rounds and returns `none` if it has not settled. Nothing here proves
it always settles in time; the fixture generator fails if it ever does not.
-/

namespace RicePest

/-- Families `i` and `j` are linked by a chain of close families. -/
inductive Connected (close : Nat → Nat → Bool) : Nat → Nat → Prop
  | refl (i : Nat) : Connected close i i
  | tail {i j k : Nat} : Connected close i j → close j k = true → Connected close i k

theorem Connected.trans {close : Nat → Nat → Bool} {i j k : Nat}
    (h₁ : Connected close i j) (h₂ : Connected close j k) : Connected close i k := by
  induction h₂ with
  | refl => exact h₁
  | tail _ hc ih => exact .tail ih hc

theorem Connected.single {close : Nat → Nat → Bool} {i j : Nat} (h : close i j = true) :
    Connected close i j :=
  .tail (.refl i) h

theorem Connected.symm {close : Nat → Nat → Bool} (hsymm : ∀ a b, close a b = close b a)
    {i j : Nat} (h : Connected close i j) : Connected close j i := by
  induction h with
  | refl => exact .refl _
  | @tail j k _ hc ih =>
    exact (Connected.single (by rw [hsymm]; exact hc)).trans ih

/-- One round for family `i`: the smallest label among itself and its close neighbours. -/
def step (n : Nat) (close : Nat → Nat → Bool) (f : Nat → Nat) (i : Nat) : Nat :=
  (List.range n).foldl (fun m j => if close i j then min m (f j) else m) (f i)

theorem foldl_min_le_init (close : Nat → Nat → Bool) (f : Nat → Nat) (i : Nat) :
    ∀ (l : List Nat) (m : Nat),
      l.foldl (fun m j => if close i j then min m (f j) else m) m ≤ m
  | [], _ => Nat.le_refl _
  | j :: js, m => by
    simp only [List.foldl_cons]
    refine Nat.le_trans (foldl_min_le_init close f i js _) ?_
    split <;> omega

theorem foldl_min_le_mem (close : Nat → Nat → Bool) (f : Nat → Nat) (i : Nat) :
    ∀ (l : List Nat) (m j : Nat), j ∈ l → close i j = true →
      l.foldl (fun m j => if close i j then min m (f j) else m) m ≤ f j
  | [], _, _, h, _ => absurd h (List.not_mem_nil)
  | k :: ks, m, j, h, hc => by
    simp only [List.foldl_cons]
    rcases List.mem_cons.mp h with rfl | h
    · refine Nat.le_trans (foldl_min_le_init close f i ks _) ?_
      simp only [hc, ite_true]; omega
    · exact foldl_min_le_mem close f i ks _ j h hc

/-- The result of a round is the family's own label or a close neighbour's. -/
theorem foldl_min_cases (close : Nat → Nat → Bool) (f : Nat → Nat) (i : Nat) :
    ∀ (l : List Nat) (m : Nat),
      l.foldl (fun m j => if close i j then min m (f j) else m) m = m ∨
        ∃ j ∈ l, close i j = true ∧
          l.foldl (fun m j => if close i j then min m (f j) else m) m = f j
  | [], _ => .inl rfl
  | k :: ks, m => by
    simp only [List.foldl_cons]
    rcases foldl_min_cases close f i ks
        (if close i k then min m (f k) else m) with h | ⟨j, hj, hc, h⟩
    · rw [h]
      by_cases hk : close i k = true
      · simp only [hk, ite_true]
        by_cases hle : m ≤ f k
        · exact .inl (Nat.min_eq_left hle)
        · exact .inr ⟨k, List.mem_cons_self .., hk, Nat.min_eq_right (by omega)⟩
      · simp only [hk]; exact .inl rfl
    · exact .inr ⟨j, List.mem_cons_of_mem _ hj, hc, h⟩

theorem step_le_neighbour {n : Nat} {close : Nat → Nat → Bool} {f : Nat → Nat} {i j : Nat}
    (hj : j < n) (hc : close i j = true) : step n close f i ≤ f j :=
  foldl_min_le_mem close f i _ _ j (List.mem_range.mpr hj) hc

theorem step_cases (n : Nat) (close : Nat → Nat → Bool) (f : Nat → Nat) (i : Nat) :
    step n close f i = f i ∨ ∃ j, close i j = true ∧ step n close f i = f j := by
  rcases foldl_min_cases close f i (List.range n) (f i) with h | ⟨j, _, hc, h⟩
  · exact .inl h
  · exact .inr ⟨j, hc, h⟩

/-- `f` has settled: no round changes any label. -/
def settled (n : Nat) (close : Nat → Nat → Bool) (f : Nat → Nat) : Bool :=
  (List.range n).all fun i => step n close f i == f i

def iterate (n : Nat) (close : Nat → Nat → Bool) : Nat → (Nat → Nat) → Option (Nat → Nat)
  | 0, _ => none
  | fuel + 1, f => if settled n close f then some f else iterate n close fuel (step n close f)

/-- Group labels for families `0 … n-1`: each family's label is a family index. -/
def groups (n : Nat) (close : Nat → Nat → Bool) : Option (Nat → Nat) :=
  iterate n close (n + 1) id

/-- Every label is reachable: invariant of the rounds. -/
theorem iterate_connected {n : Nat} {close : Nat → Nat → Bool} :
    ∀ (fuel : Nat) (f g : Nat → Nat), (∀ i, Connected close i (f i)) →
      iterate n close fuel f = some g → ∀ i, Connected close i (g i)
  | 0, _, _, _, h => by simp [iterate] at h
  | fuel + 1, f, g, hf, h => by
    unfold iterate at h
    split at h
    · simp only [Option.some.injEq] at h; subst h; exact hf
    · refine iterate_connected fuel _ g ?_ h
      intro i
      rcases step_cases n close f i with he | ⟨j, hc, he⟩
      · rw [he]; exact hf i
      · rw [he]; exact (Connected.single hc).trans (hf j)

theorem iterate_settled {n : Nat} {close : Nat → Nat → Bool} :
    ∀ (fuel : Nat) (f g : Nat → Nat), iterate n close fuel f = some g → settled n close g = true
  | 0, _, _, h => by simp [iterate] at h
  | fuel + 1, f, g, h => by
    unfold iterate at h
    split at h
    · rename_i hs; simp only [Option.some.injEq] at h; subst h; exact hs
    · exact iterate_settled fuel _ g h

/-- No leakage: close families get the same group. -/
theorem groups_close {n : Nat} {close : Nat → Nat → Bool} (hsymm : ∀ a b, close a b = close b a)
    {g : Nat → Nat} (hg : groups n close = some g) {i j : Nat} (hi : i < n) (hj : j < n)
    (hc : close i j = true) : g i = g j := by
  have hs := iterate_settled _ _ _ hg
  simp only [settled, List.all_eq_true, List.mem_range, beq_iff_eq] at hs
  have h₁ : g i ≤ g j := hs i hi ▸ step_le_neighbour hj hc
  have h₂ : g j ≤ g i := hs j hj ▸ step_le_neighbour hi (by rw [hsymm]; exact hc)
  omega

/-- Groups are no coarser than they must be: the same group means a chain of close families. -/
theorem groups_connected {n : Nat} {close : Nat → Nat → Bool}
    (hsymm : ∀ a b, close a b = close b a) {g : Nat → Nat} (hg : groups n close = some g)
    {i j : Nat} (h : g i = g j) : Connected close i j := by
  have hc := iterate_connected (n + 1) id g (fun i => .refl i) hg
  have hj := (hc j).symm hsymm
  rw [← h] at hj
  exact (hc i).trans hj

/-- The leakage guarantee as the pipeline uses it: whatever split is chosen per group, close
families land in the same split. -/
theorem groups_split_no_leakage {α : Type} {n : Nat} {close : Nat → Nat → Bool}
    (hsymm : ∀ a b, close a b = close b a) {g : Nat → Nat} (hg : groups n close = some g)
    (split : Nat → α) {i j : Nat} (hi : i < n) (hj : j < n) (hc : close i j = true) :
    split (g i) = split (g j) := by
  rw [groups_close hsymm hg hi hj hc]

/-! ## Closeness of perceptual hashes -/

/-- Number of set bits. -/
def popcount (x : Nat) : Nat :=
  if h : x = 0 then 0 else x % 2 + popcount (x / 2)
termination_by x
decreasing_by omega

/-- Two families are close when any of their hashes differ in at most `d` bits. -/
def familiesClose (hashes : List (List Nat)) (d : Nat) (i j : Nat) : Bool :=
  (hashes.getD i []).any fun a => (hashes.getD j []).any fun b => popcount (a ^^^ b) ≤ d

theorem familiesClose_symm (hashes : List (List Nat)) (d : Nat) :
    ∀ a b, familiesClose hashes d a b = familiesClose hashes d b a := by
  intro a b
  apply Bool.eq_iff_iff.mpr
  simp only [familiesClose, List.any_eq_true, decide_eq_true_eq]
  constructor
  · rintro ⟨x, hx, y, hy, h⟩; exact ⟨y, hy, x, hx, by rwa [Nat.xor_comm]⟩
  · rintro ⟨x, hx, y, hy, h⟩; exact ⟨y, hy, x, hx, by rwa [Nat.xor_comm]⟩

end RicePest
