import Lean
import RicePest

/-!
# Axiom audit

Fails the build if any declaration in a `RicePest` module depends, directly or through what it
uses, on an axiom other than Lean's three standard ones. That catches a proof replaced by a new
`axiom`, a `sorry` (`sorryAx`) even under `set_option warningAsError false`, and `native_decide`
(`Lean.ofReduceBool`). It is built with the library (`lake build`), so CI runs it.
-/

open Lean Elab Command

def allowedAxioms : List Name := [``propext, ``Classical.choice, ``Quot.sound]

run_cmd do
  let env ← getEnv
  let mut audited : Nat := 0
  let mut bad : Array (Name × Name) := #[]
  for (n, _) in env.constants.map₁.toList do
    let some idx := env.getModuleIdxFor? n | continue
    let some mod := env.header.moduleNames[idx.toNat]? | continue
    unless (`RicePest).isPrefixOf mod do continue
    audited := audited + 1
    for a in ← liftCoreM (collectAxioms n) do
      unless allowedAxioms.contains a do bad := bad.push (n, a)
  if audited == 0 then
    throwError "axiom audit found no RicePest declarations to check"
  unless bad.isEmpty do
    let lines := bad.toList.map fun (n, a) => s!"  {n} uses {a}"
    throwError "axiom audit failed:\n{String.intercalate "\n" lines}"
  logInfo m!"axiom audit: {audited} RicePest declarations use only {allowedAxioms}"
