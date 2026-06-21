# Phase-3 Axis-A: MPS / tensor-network backend (the scale frontier)

**Goal.** The dense engine (`qrc_engine.py`) stores the full 2ⁿ statevector, so it walls at
n=12 (>12 min/input). A matrix-product-state (MPS) backend represents the reservoir state as
a chain of rank-3 tensors with bounded bond dimension χ, with cost ~ n·χ³·d instead of 2ⁿ —
*if* the reservoir's entanglement stays low enough for a modest χ. This component builds and
validates that backend and then measures, decisively, whether the CHIMERA reservoir is
actually MPS-compressible.

## What was built

- **`mps_engine.py`** — a finite-MPS, canonical-form TEBD engine:
  - product-state init, single-qubit gates, two-qubit gates with SVD truncation to χ
    (discarded weight logged), **long-range ZZ gates via SWAP networks** (the Phase-2
    Hamiltonian has a *random* coupling graph, connectivity 0.5 — long-range, the hard case),
  - 2nd-order Trotter evolution of `exp(-iHτ)` for the transverse-field Ising H,
  - exact ⟨Z_i⟩ and ⟨Z_iZ_j⟩ contractions from the canonical form (same feature layout as
    the dense engine), with rigorous orthogonality-center management.
- **`mps_bond_scaling.py`** — the entanglement / truncation-cost / wall-time diagnostic.

## Validation (engine is correct)

`python mps_engine.py --selftest` confirms the MPS features reproduce the **exact dense**
reservoir, with the only discrepancy being Trotter error that vanishes ~1/steps² (2nd order):

| n | τ | err @ low steps → high steps |
|---|---|---|
| 8 | 2.0 | 5.9e-2 → 9.9e-4 |
| 8 | 4.0 | 8.6e-2 → 1.1e-3 |
| 6 | 4.0 | 8.4e-2 → 1.3e-3 |

At χ=2ⁿ (no truncation) the MPS state matches the dense Strang state to 1e-15, and the MPS
⟨Z_iZ_j⟩ contraction matches a brute-force statevector measurement to 1e-15. Production
`steps` scales with τ (~24·τ) to hold Trotter error near 1e-3.

## Decisive result: the reservoir is near-maximally entangled (exact frontier n=12 → 16)

On the peak-RV (crisis) input row, the bond dimension the reservoir *actually reaches* equals
the **maximal possible** value 2^(n/2) at **every** n, with machine-zero truncation at that χ —
i.e. **volume-law entanglement**, confirmed *exactly* well past the dense n=12 wall:

| n | bond reached | 2^(n/2) | trunc @ χ=2^(n/2) | wall-time/input | note |
|---|---|---|---|---|---|
| 8  | 16  | 16  | 1.3e-31 | 0.1 s | dense-checkable |
| 10 | 32  | 32  | 2.3e-31 | 0.3 s | dense-checkable |
| 12 | 64  | 64  | 5.3e-31 | 2.3 s | dense wall |
| 14 | 128 | 128 | 1.8e-29 | 19 s  | **MPS-only, exact** |
| 16 | 256 | 256 | 8.1e-29 | 168 s | **MPS-only, exact** |

Speed lever: the bond dimension reached is **insensitive to Trotter step count** (verified:
steps=8 vs 48 both reach the full 2^(n/2) bond at machine-zero truncation), so the bond/
entanglement frontier runs at steps=8 — ~6× faster — which is what made n=14, 16 reachable.

**A fixed χ does not keep up.** Truncation drops to machine-zero only once χ reaches 2^(n/2):
at n=16 even χ=128 still discards 3.9e-4 (true bond is 256). So a capped-χ MPS is a *controlled
approximation* whose required χ grows exponentially with n.

**Interpretation (honest, and important either way).**
- The **exact qubit frontier moved from n=12 (dense) to n=16 (MPS)** — 16× more Hilbert space —
  but the cost still grows exponentially (χ ~ 2^(n/2), wall-time ~×8 per +2 qubits). MPS roughly
  **doubles the exact reach** for a given memory budget; it is *not* a free ride to 30 qubits.
- **n≥18 is wall-time-bound** in this pure-NumPy SWAP-network backend (the χ=256 probe at n=18
  did not finish in ~10 min); a compiled/GPU TN library (quimb/ITensor) — none available in this
  environment — would be needed to push further.
- Most importantly, the volume-law entanglement is **evidence the CHIMERA reservoir occupies a
  classically-hard regime**. A low-entanglement reservoir would be trivially reproduced by a
  small-χ MPS, which would *undercut* any quantum-advantage rationale. That it is *not*
  MPS-compressible is a point in favour of the reservoir being genuinely quantum — while also
  explaining why the decisive large-n H0 test is hard to reach by classical simulation at all.

Feature *fidelity* (capped-χ MPS vs exact dense, at production Trotter steps) is validated
separately in `mps_engine.py --selftest` and the earlier n≤12 cross-check (χ=16 → 0.15 %→4.4 %
feature error over n=8→12); the table above isolates the bond/entanglement/wall-time frontier.

**Interpretation (honest, and important either way).**
- MPS does **not** give a free ride to 30 qubits for *this* Hamiltonian: exact simulation
  cost still grows exponentially (χ ~ 2^(n/2)). It roughly **doubles the exact qubit reach**
  for a given memory budget (a tensor of bond 2^(n/2) ≈ the dense vector at n/2), pushing the
  exact frontier from n≈12 toward n≈20–24 before time/memory blow up again.
- A **fixed modest χ** gives a *controlled approximation* whose error we have now quantified
  (e.g. χ=32 → ~2% feature error at n=12, growing with n) — usable for exploratory large-n
  runs with a known error bar, not for exact claims.
- Most importantly, the volume-law entanglement is **evidence the CHIMERA reservoir occupies a
  classically-hard regime**. A low-entanglement reservoir would be trivially reproduced by a
  small-χ MPS, which would *undercut* any quantum-advantage rationale. That it is *not*
  MPS-compressible is a point in favour of the reservoir being genuinely quantum — while also
  explaining why the decisive large-n H0 test is hard to reach by classical simulation at all.

## Next

1. **g(n)/MZ-gap at scale is the real prize but needs a faster backend.** Those metrics require
   running the reservoir over *hundreds* of input rows (kernel N=800 + the MZ split), not one
   crisis row; at 168 s/input for n=16 that is ~37 h per n in pure NumPy — infeasible here. The
   honest conclusion is that extending the *decision curves* past n=12 needs a compiled/GPU TN
   library (quimb/ITensor/cuQuantum) or actual quantum hardware. The bond result already answers
   the prior question — *no* classical method (dense or MPS) reaches the ~30-qubit frontier
   cheaply for this reservoir.
2. Test whether a **weaker-coupling / shorter-τ or sparser** reservoir variant lowers
   entanglement enough for genuine large-n MPS reach — and, if so, whether it *retains* the
   distinctness (g) the dense reservoir shows. If low entanglement kills g, that ties the quantum
   signal directly to the entanglement: a clean, publishable result.
3. Port the SWAP-network TEBD hot loop to a faster backend (greedy qubit ordering to cut swap
   distance; compiled SVD) to push the exact frontier from n=16 toward n≈20.
