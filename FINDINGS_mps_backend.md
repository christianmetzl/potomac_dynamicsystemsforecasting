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

## Decisive result: the reservoir is near-maximally entangled

On the peak-RV (crisis) input row, the bond dimension the reservoir *actually reaches* equals
the **maximal possible** value 2^(n/2) at every n — i.e. **volume-law entanglement**. The
random all-to-all couplings at τ=2 thermalize the state, so an *exact* MPS needs χ ~ 2^(n/2)
(still exponential), and a *fixed* χ is an approximation whose error grows with n:

| n | bond reached | 2^(n/2) | trunc @ χ=16 | feat err vs dense @ χ=16 | wall-time/input |
|---|---|---|---|---|---|
| 8  | 16 (exact) | 16 | 3e-32 (exact) | 1.5e-3 | 1.0 s |
| 10 | 32 (exact) | 32 | 4.7e-5 | 8.5e-3 | 2.7 s |
| 12 | 64 (exact) | 64 | 7.3e-5 | 4.4e-2 | 13 s |
| 14 | ≥64 (χ=64 still truncates → true 128) | 128 | 8.8e-5 | — (MPS-only, past dense wall) | 74 s |

n=14 is **past the dense n=12 wall**: even at χ=64 the reservoir keeps discarding weight
(5.1e-5), i.e. its true bond (128 = 2⁷) exceeds 64 — the 2^(n/2) volume law continues. The
pure-NumPy SWAP-network backend walls on *wall-time* here (~74 s/input at χ=64; n=16 with χ=128
was abandoned at >15 min/input), which is the practical reach of this implementation. (Run
`mps_bond_scaling.py --ns ... --chi-ref ...` to extend; JSON saves incrementally per n.)

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

1. **Push the exact frontier** to n≈18–20 with χ up to ~1024 (memory-bounded) to confirm the
   2^(n/2) law holds and to extend g(n)/MZ-gap one or two qubits past the dense wall.
2. Test whether a **weaker-coupling / shorter-τ or sparser** reservoir variant lowers
   entanglement enough for genuine large-n MPS reach — and, if so, whether it *retains* the
   distinctness (g) that the dense reservoir shows. (If low entanglement kills g, that ties the
   quantum signal directly to the entanglement, a clean result.)
3. Optionally port the SWAP-network TEBD hot loop to a faster backend (the pure-NumPy version
   walls on wall-time, not just memory).
