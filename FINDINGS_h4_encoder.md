# Findings — H4 multivariate encoder (Axis B): the input-bottleneck reversal

**Runs:** `python scaling_sweep.py --encoding {univariate,multivariate} --ns 8 10`
**Figure:** `figures/fig_encoder_comparison.png` (via `plot_encoder_comparison.py`)

## Headline

When the qubits added beyond 8 carry **new information** (downside realized semivariance
`rsv` + jump-robust `medrv` at n=10), the input-bottleneck collapse measured under the
univariate encoder **reverses**:

| metric | n=8 (identical control) | n=10 univariate | n=10 multivariate (H4) |
|---|---|---|---|
| g(ESN→CHIMERA) | 62.7 | **34.6**  (−45%) | **76.9**  (+23%) |
| g-curve status (pre-registered) | — | saturating | **growing** (Δg ≥ 2×control) |
| kernel D_eff | 1.81 | 1.53 | 2.22 |
| MZ-R²(CHIMERA) | 0.591 | 0.308 | 0.541 |
| MZ-gap vs HAR | +0.032 | **−0.251** | **−0.018** (≈ parity) |
| in 95% MCS | ✅ | ❌ | ✅ |

By construction the n=8 input is **bit-identical** across encoders (the panel's first 8
columns are the rv5 lags; max difference 0.0 on 5,029 common dates), so the divergence at
n=10 is caused *only* by what the 2 added qubits encode.

## Interpretation

This is direct, measured support for the Phase-2 paper's H4 ("scale qubit count in lockstep
with input richness so added qubits encode new information"). The univariate degradation was
**not** an intrinsic failure of the quantum reservoir — it was information starvation. Feed
the added qubits genuinely new measures and:

- **H0 curve 1 (kernel distinctness) reverses from collapsing to growing** — g(n) goes
  62.7→76.9 and is classified `growing` by the locked threshold, vs 62.7→34.6 (`saturating`)
  under univariate. This is the first scaling axis H0 requires.
- Effective rank rises (1.81→2.22) instead of falling (1.53).
- CHIMERA returns to the 95% Model Confidence Set (excluded under univariate).

## Honest scope (what this does NOT yet show)

- **The regime-transition accuracy gap is recovered but not yet positive.** mz_gap goes
  −0.251 → −0.018 (≈ HAR parity), but remains ≤ 0 and insignificant (boot p=0.64,
  DM p=0.29). So new information **halts the collapse and restores distinctness**, but has
  not (at n=10) converted into *beating* HAR on regime-transition efficiency — exactly the
  scale-dependent question H0 targets. Pre-registered verdict: `INCONCLUSIVE` (promising),
  correct for n=10 ≪ the ~30-qubit decisive frontier.
- **D_eff growth is modest** (+0.41 per 2 qubits, just under the 0.5 "rising" bar → still
  classified `saturating`). The two new measures are correlated with rv5 (~0.93); richer,
  less-redundant inputs (cross-asset, intraday/order-flow per the paper's H4) should help.
- **n=12+ was not reached:** even with eigh-cached evolution, the dense 2ⁿ statevector walls
  at n=12 (>12 min/point). Completing the curve to where g-growth either persists or
  saturates is what the **MPS / tensor-network backend (item 3)** is for.

## Update — data re-uploading (encoding `multivariate_reupload`, R=2)

`scaling_sweep.py --encoding multivariate --reupload 2` makes n qubits absorb 2n panel
features by interleaving a second encoding between evolutions (Pérez-Salinas 2020). Result:

| n | g (R=1) | g (R=2) | D_eff (R=1→R=2) | MZ-gap (R=2) | DM point-loss (R=2) |
|---|---|---|---|---|---|
| 8 | 62.7 | **188.8** | 1.81 → **3.95** | −0.065 | **−2.52 (p=0.012) → CHIMERA beats HAR** |
| 10 | 76.9 | 118.2 | 2.22 → 2.09 | −0.119 | −1.25 (p=0.21) |

**What re-uploading buys (honest):**
- A large jump in **kernel distinctness and effective rank** — g ≈ 3× and D_eff ≈ 2× at n=8
  vs single-encode. Encoding *depth* is a strong expressivity lever, complementary to width.
- The **first point-forecast win over HAR**: at n=8, DM = −2.52 (p=0.012) on squared-error
  loss. Re-uploading the richer panel improves point RMSE where HAR was previously unbeaten.

**What it does NOT buy (honest):**
- It does **not** improve the **regime-transition MZ-gap**, which stays negative
  (−0.065 → −0.119). Re-uploading the (rv5-correlated ~0.93) measures trades a little
  MZ-efficiency for raw expressivity and point accuracy.
- The g(n) **curve still declines with n at fixed R** (188.8 → 118.2), echoing that naive
  n-scaling without proportionally *more new* information saturates even with depth.

**Synthesis.** Encoding density — width (new measures per qubit) and depth (re-uploading) —
clearly controls the quantum reservoir's distinctness/expressivity (confirming the paper's
H4 thesis) and even flips the point-RMSE comparison. But the **regime-transition MZ-gap (the
H0 objective) remains ≤ 0 and is the genuine open question** that no lever has cracked at
n ≤ 10 — consistent with H0 being a scale hypothesis, not an n≈10 phenomenon.

## Next

1. **MPS / tensor-network backend (item 3)** — the binding constraint: carry the
   multivariate (R=1 and R=2) sweeps past the n=12 dense wall toward the ~30-qubit frontier,
   logging bond dimension, to see where g-growth and the MZ-gap actually go at scale.
2. Enrich the panel with **less-redundant** information (cross-asset/sector RV covariance,
   intraday/order-flow, leverage/return-sign) so width-scaling carries new signal, not
   rv5-correlated copies.
3. A **Fisher-information capacity** metric (paper's 3rd adjudication axis) to characterize
   the expressivity gains re-uploading produces beyond g and D_eff.
