# S7 secondary arm — H-EMBED: method and scoring rule, committed BEFORE execution

*This file is the hash-preimage commitment for the H-EMBED arm. It is committed **before any
H-EMBED hardware job is submitted**, exactly as `qpu_scaling_outlook.md` (commit `89cce5f`) was
committed before the H-INSTANCE arm. If an H-EMBED result is ever reported, `git log` shows this
file predates its job records.*

## 1. The prediction (pre-registered `89cce5f`, quoted verbatim, NOT modified)

> **H-EMBED** — the n=8 scrambling is driven by seed-0's particular logical→physical
> placement. **Prediction:** re-embedding the *same* seed-0 n=8 circuit (permuted qubit
> labels, same session) shifts raw error by more than the measured same-session band (≈0.01).

The prediction and its threshold are unchanged. This file adds only *how* the arm is realized and
one **additional** guard (§4) that can only make the test harder to pass, never easier.

## 2. How the re-embedding is realized

`qpu_run.py --perm-seed P` permutes the qubit labels of the **same** seed-0 instance: the coupling
matrix becomes `J[perm][:, perm]` and the input window is permuted to match. The graph is therefore
**isomorphic** — identical edge count, identical weight multiset — so the physics is unchanged and
only the logical→physical placement the vendor transpiler chooses can differ.

Two properties were verified offline before committing, and both are re-checkable:

| property | check | result |
|---|---|---|
| the relabeling is exact | simulate the permuted QASM, compare to the index-permuted original | `max|Δ| = 9.0e-16` |
| the bar is unchanged | `mean|F_exact|` for both arms | **bit-identical** |

Because the depolarized limit is bit-identical, **both arms are scored against the same limit**;
no comparator asymmetry of the kind we self-corrected in the H-INSTANCE arm can arise here.

A homogeneous-noise offline rehearsal gives near-equal raw error for the two arms (0.1190 vs
0.1124), as it must when every qubit has the same error rate — so a difference measured on metal
is attributable to physical qubit/coupler heterogeneity and routing, not to the relabeling.

## 3. Execution plan

Two campaigns, **same session**, OpenQuantum-route IQM Garnet, n=8, seed 0, 4,000 shots,
2 cals + 3 windows, scale-1 only (~20 OQ cr each, personal credits, outside the org ceiling):

- `hw_hembed_default` — `--seed 0` (default labelling)
- `hw_hembed_perm`    — `--seed 0 --perm-seed 7`

Same-session execution controls calibration drift, exactly as the H-INSTANCE arm did.

## 4. Scoring — vacuity check FIRST, then the pre-registered rule

A transpiler that recognises the isomorphism may place both arms on the **same** physical qubits.
The test would then be **vacuous**, and — critically — a vacuous run produces a *small* raw-error
difference, which the pre-registered rule would otherwise score as "H-EMBED refuted". We refuse to
let vacuity masquerade as a refutation, so we declare the discriminator now, before any data:

**Step 1 — vacuity.** Un-permute the measured feature vector of the permuted arm and compare it to
the default arm's measured features, per window:

`D = mean|F_perm_unpermuted − F_default|`, against the 4,000-shot floor `1/√4000 = 0.0158`.

- `D ≤ 0.0158` → the two arms measured the *same physical circuit*: **TEST VACUOUS.** Reported as
  "H-EMBED attempted; the route normalised the relabeling, so the arm was not testable" — plus a
  platform observation. **The pre-registered rule is NOT applied.**
- `D > 0.0158` → the placements genuinely differ: the test is valid, proceed to Step 2.

**Step 2 — the pre-registered rule, applied only if Step 1 passes.**

- `|raw(perm) − raw(default)| > 0.01` → **H-EMBED SUPPORTED**: the n=8 scrambling is driven by
  logical→physical placement. The paper's "mechanism honestly open" narrows to embedding.
- `|raw(perm) − raw(default)| ≤ 0.01` → **H-EMBED REFUTED**: placement does not drive it; the
  driver is the instance's coupling structure itself. The mechanism narrows the other way.

Either outcome is reported as measured. Both arms additionally get the same multinomial bootstrap
used elsewhere (`s7_bootstrap_ci.py` methodology), so the difference carries a shot-noise CI.

## 5. Abort rules (committed)

- Either campaign fails to reach terminal state within the poll timeout → report as attempted and
  not completed; **no partial scoring**.
- The two campaigns cannot be run in the same session → report as attempted; the drift control is
  lost and the arm stays open.
- Any raw value within ±0.02 of its limit → that point is *unresolved*, per the S7 rule already
  committed at `89cce5f`.

## 6. What this arm cannot do

It does not revisit the forecasting negative, does not add a device or an instance, and does not
address the single-seed concern (that is the H-INSTANCE arm plus `instance_ensemble_findings.md`).
It resolves exactly one question: of the three mechanism candidates listed in
`qpu_hardware_findings.md` ("instance structure", "embedding", "per-feature noise sensitivity"),
is **embedding** the driver?
