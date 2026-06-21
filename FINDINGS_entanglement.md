# Phase-3 Axis-A: is the kernel distinctness `g` caused by entanglement?

**Question.** The MPS study showed the Phase-2 reservoir is near-maximally (volume-law)
entangled, which is why no classical method reaches the ~30-qubit frontier cheaply. The natural
follow-up: is that entanglement *what makes the reservoir useful* — i.e. does the kernel
distinctness `g` (H0 "curve 1": geometric difference of the quantum kernel from the matched
ESN-108 kernel) *require* the entanglement, or is it incidental?

**Method (`entanglement_distinctness.py`).** A single clean knob — a global scale `α` on the
Ising coupling `J` — dials entanglement at fixed n, τ=2, fixed encoding/readout/inputs and a
fixed matched ESN:
- `α=0` → `J=0` → `H = hx·ΣX` → evolution is a *product* of single-qubit rotations → **zero
  entanglement** (separable reservoir);
- `α=1` → the exact Phase-2 reservoir (near-maximal entanglement);
- `α>1` → still more entanglement.
We measure, on the same N=800 train-kernel subsample used for `g`, both the bipartite
entanglement entropy `S` (von Neumann, central cut, exact from the statevector) and `g`.

## Result: `g` is NOT entanglement-bound — it peaks at LOW entanglement

| α | S (bits) | S/S_max | g | g / control |
|---|---|---|---|---|
| 0.00 (product state) | 0.00 | 0.00 | 55.3 | **6.7×** |
| 0.25 | 1.21 | 0.24 | **197.6** | **24.0×** ← peak |
| 1.00 (Phase-2) | 2.95 | 0.59 | 80.4 | 9.8× |
| 3.00 | 3.38 | 0.67 | 62.5 | 7.6× |

(n=10, τ=2, seed 0; classical-classical control g=8.25, S_max=5 bits.)

Three robust facts (confirmed at **n=12**, seed 0, which reproduces the *whole shape*: g=54.8 =
**9.1×** control at S=0 → peak 17.3× at α=0.25 → falling 12.2× at α=0.5 → 10.2× at α=0.75):
1. **At zero entanglement, `g` is already 6.7–9× the classical control.** The quantum kernel's
   distinctness comes from the *nonlinear single-qubit quantum feature map* (RY encoding →
   transverse-field rotation → Z/ZZ readout), **not** from entanglement.
2. **`g` is maximised at LOW entanglement** (α≈0.25, ~¼ of maximal entropy) — ~24× control —
   and then **declines** as entanglement rises toward volume-law.
3. Across the whole dial **corr(g, S) ≈ −0.24** (weakly *negative*). The Phase-2 reservoir
   (α=1) is on the *falling* side: it is **over-entangled relative to the g-optimum**.

## Why this matters (two unlocks)

- **The classical scale frontier is reachable after all — for the right reservoir.** A
  weakly-coupled reservoir (α≈0.1–0.25) has *higher* `g` than Phase-2 *and* low entanglement
  (S/S_max≈0.24 → a concentrated Schmidt spectrum → small bond dimension), so it is
  **MPS-simulable to large n cheaply**. The MPS wall we hit was a property of the *over-coupled*
  Phase-2 choice, not of useful quantum reservoirs in general.
- **It reframes the quantum-advantage story.** The kernel-geometry advantage is a *single-qubit
  nonlinearity* effect, present without entanglement. Entanglement is therefore **neither
  necessary nor beneficial for `g`** here — a sharper, more honest claim than "entanglement is
  the resource", and a caution against equating volume-law entanglement with usefulness.

## Important caveats / next

1. **`g` is distinctness, not accuracy.** The α≈0.25 peak coincides with *low* effective kernel
   rank (D_eff≈1.8). The decisive next test: does the low-entanglement reservoir retain the
   **regime-transition MZ-gap** (H0 "curve 2"), or do `g` and predictive accuracy decouple?
   If the weak-coupling reservoir keeps accuracy, run it through the MPS backend to push the
   *decision curves* (not just bond dimension) well past n=12.
2. Single τ, two n (10, 12), one seed each beyond n=10. Worth a seed sweep for error bars.
3. If the spec fixes the reservoir coupling, this becomes a characterisation of *that* choice
   rather than a design lever — but the "g without entanglement" finding stands regardless.
