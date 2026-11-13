import Lean.Data.Json
import RicePest

/-!
# Fixture generator

Runs the Lean specification on deterministic inputs and writes the expected outputs, which
`tests/test_lean_spec.py` (Python) and `app/test/lean_spec_test.dart` (Dart) check the real code
against. Run from `formal/`:

    lake exe fixtures            # write ../app/test/fixtures/lean_spec_fixtures.json
    lake exe fixtures --check    # fail if the committed file differs
-/

open Lean RicePest

def outPath : System.FilePath := ".." / "app" / "test" / "fixtures" / "lean_spec_fixtures.json"

/-- A small linear congruential generator, so the inputs need no library and never change. -/
def lcg (s : Nat) : Nat := (1103515245 * s + 12345) % 2147483648

/-- `n` values in `[lo, hi]`, and the next state. -/
def draws (s : Nat) (n : Nat) (lo hi : Int) : List Int × Nat := Id.run do
  let mut st := s
  let mut out := #[]
  for _ in [0:n] do
    st := lcg st
    out := out.push (lo + Int.ofNat ((st / 65536) % (hi - lo + 1).toNat))
  return (out.toList, st)

/-- Logits in eighths, on the quarter grid in [-3, 3]: even numbers from -24 to 24. Equal values
are common, so ties between queries and between classes are exercised. -/
def caseRows (seed : Nat) : List (List Int) := Id.run do
  let mut st := seed
  let mut rows := #[]
  for _ in [0:40] do
    let (row, st') := draws st 4 (-12) 12
    st := st'
    rows := rows.push (row.map (· * 2))
  return rows.toList

/-- Thresholds in eighths: 0 (probability exactly 0.5) and odd values, which no logit equals. -/
def thresholds : List Int := [0, -17, -9, -3, 5, 11, 17, 23]

def postprocessCase (seed : Nat) : Json :=
  let rows := caseRows seed
  let qs := queriesOf rows
  Json.mkObj [
    ("seed", toJson seed),
    ("logits_eighths", toJson rows),
    ("results", toJson (thresholds.map fun t => Json.mkObj [
      ("threshold_eighths", toJson t),
      ("expected", toJson ((postprocess qs t).map fun q => [q.idx, q.cls]))]))]

/-- For each reference count, the accepted predictions form one interval (proved in
`withinTolerance_band` and `withinTolerance_small`); record its ends. -/
def toleranceBand (ref : Nat) : Json :=
  let accepted := (List.range (2 * ref + 3)).filter (withinTolerance · ref)
  Json.mkObj [("ref", toJson ref), ("lo", toJson (accepted.head?.getD 0)),
              ("hi", toJson (accepted.getLast?.getD 0))]

/-- One 63-bit value from three generator draws. Real dHashes use 64 bits; staying below 2^63
keeps every value exact when the Dart tests decode the same JSON file (Dart ints are signed). -/
def drawHash (s : Nat) : Nat × Nat :=
  let a := lcg s
  let b := lcg a
  let c := lcg b
  (a % 2147483648 ||| (b % 2147483648) <<< 31 ||| (c % 2) <<< 62, c)

/-- Families of hashes drawn near a few shared bases, so near-duplicates, chains and separate
groups all occur. Family `i` is named `f00`, `f01`, ... as in `dedup.group_families`. -/
def familiesCase (seed : Nat) : Json := Id.run do
  let mut st := lcg seed
  let nBases := 1 + st % 3
  let mut bases := #[]
  for _ in [0:nBases] do
    let (h, st') := drawHash st
    st := st'
    bases := bases.push h
  st := lcg st
  -- At most 10: `groups` re-evaluates earlier rounds, so its cost grows quickly with n.
  let nFamilies := 2 + st % 9
  st := lcg st
  let d := st % 9
  let mut fams : Array (List Nat) := #[]
  for _ in [0:nFamilies] do
    st := lcg st
    let nHashes := 1 + st % 3
    let mut hs := #[]
    for _ in [0:nHashes] do
      st := lcg st
      let mut h := bases[st % bases.size]!
      st := lcg st
      for _ in [0:st % 7] do
        st := lcg st
        h := h ^^^ (1 <<< ((st / 65536) % 63))
      hs := hs.push h
    fams := fams.push hs.toList
  let hashes := fams.toList
  let name (i : Nat) := if i < 10 then s!"f0{i}" else s!"f{i}"
  let some g := groups nFamilies (familiesClose hashes d)
    | panic! s!"grouping did not settle for seed {seed}"
  let labels := (List.range nFamilies).map g
  let groupsOut := labels.eraseDups.map fun l =>
    ((List.range nFamilies).filter (g · == l)).map name
  return Json.mkObj [
    ("seed", toJson seed), ("max_distance", toJson d),
    ("hashes", Json.mkObj ((List.range nFamilies).map fun i => (name i, toJson (hashes.getD i [])))),
    ("groups", toJson groupsOut)]

def fixtures : Json :=
  Json.mkObj [
    ("generator", toJson "formal/Fixtures.lean (lake exe fixtures)"),
    ("postprocess", toJson ((List.range 12).map fun i => postprocessCase (20261113 + 7919 * i))),
    ("tolerance", toJson ((List.range 401).map toleranceBand)),
    ("families", toJson ((List.range 60).map fun i => familiesCase (20261114 + 104729 * i)))]

def main (args : List String) : IO UInt32 := do
  let text := fixtures.compress ++ "\n"
  if args == ["--check"] then
    let current ← IO.FS.readFile outPath
    if current == text then
      IO.println s!"{outPath} is up to date"
      return 0
    IO.eprintln s!"{outPath} differs from the Lean specification; run `lake exe fixtures`"
    return 1
  else if args.isEmpty then
    IO.FS.writeFile outPath text
    IO.println s!"wrote {outPath}"
    return 0
  else
    IO.eprintln "usage: lake exe fixtures [--check]"
    return 2
