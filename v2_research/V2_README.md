# V2 research — exploratory extensions (NOT part of the V1 submission)

> **Status: exploratory. The competition submission is V1**, frozen at git tag
> `v1-submission`. Nothing in this folder is referenced by the V1 paper, README, or
> `cli.py reproduce`, and no V1 file was modified to produce it.
>
> **Revert to / rebuild the exact V1 submission at any time:**
> ```bash
> git archive v1-submission -o EIGENNEXUS_Challenge_Phase3.zip   # exact V1 package
> # or inspect: git checkout v1-submission
> ```

## Why V2 exists
V1's honest finding: at simulable scale (≤16 qubits), the quantum reservoir shows **no
statistically significant forecasting advantage** over strong classical baselines (HAR-X
is best); H0 refuted. V2 tests the most plausible "how could we make it see better?" leads
— **honestly, with the same rigor** (HAR-X control, HAC-DM, multiple seeds, Holm). Both are
genuine experiments; both returned negatives. We report them.

## Experiment A — Multi-horizon (`v2_multihorizon.py`)
*Hypothesis:* the quantum edge might appear at longer horizons, where HAR's linear form is
weaker. Direct h-step forecasts, crisis window, n=10, 8 seeds, HAC lag ≥ h−1.

| horizon | HAR-X RMSE | CHIMERA RMSE | CHIMERA DM vs HAR-X | Holm p |
|---|---|---|---|---|
| h=1  | **0.6034** | 0.6074 | +1.17 (worse) | 0.245 |
| h=5  | **0.7523** | 0.7662 | +1.74 (worse) | 0.245 |
| h=10 | **0.8305** | 0.8616 | +2.13 (worse, raw p=0.034) | 0.135 |
| h=22 | **0.9443** | 0.9682 | +1.65 (worse) | 0.245 |

**Result: refuted.** HAR-X is best at *every* horizon; CHIMERA is consistently slightly
worse (never significantly better; at h=10 significantly *worse* raw, n.s. after Holm). For
realized volatility the linear long-memory structure dominates *more* at longer horizons, not
less — the opposite of the hypothesis.

## Experiment B — Aim the lens + residual hybrid (`v2_aligned_residual.py`)
n=10, crisis window. HAR-X bar: RMSE 0.6034, MZ 0.618.

| variant | RMSE | MZ | DM vs HAR-X | p |
|---|---|---|---|---|
| CHIMERA (default τ=2) | 0.6125 | 0.636 | +2.25 (worse) | 0.025 |
| **CHIMERA (train-KTA-optimal config)** | 0.6397 | 0.590 | +3.78 (worse) | 0.000 |
| HAR-X + quantum-residual | 0.6096 | 0.627 | +2.09 (worse) | 0.037 |

**Result: refuted — and instructive.**
- **B1 "aim the lens" backfires:** selecting the reservoir that maximizes *train* kernel-target
  alignment makes out-of-sample forecasting **worse** (0.640 vs 0.613). High train-KTA configs
  (multi-τ, large field) over-fit the kernel to the training target. Train-KTA is *not* a safe
  selection criterion for OOS forecasting here — a useful methodological caution.
- **B2 residual hybrid** (let HAR-X do the linear bulk, quantum model the residual) does not beat
  HAR-X either; the quantum residual adds noise, not signal, at this scale.

## What V2 rules out, and what it doesn't
Ruled out (at ≤16 simulable qubits, S&P-500 RV): longer horizons, alignment-tuning, and
residual hybridization do **not** convert the reservoir's distinctness into accuracy. Combined
with V1, this is a thorough, honest mapping of where the quantum approach does **not** help.

**Not yet tested (require resources we don't have offline):**
- **Cross-asset / high-dimensional joint volatility** — needs a multi-index realized-measure
  panel; the bundled Oxford-Man CSV is `.SPX`-only. (Highest-value untested lead.)
- **Scale beyond the classical-simulation frontier** on real neutral-atom hardware — the one
  regime where "hard to copy" could become a real edge (needs qBraid QPU credits).

## Honest bottom line
V2 reinforces V1: at the scale we can simulate, the quantum reservoir is *competitive and
distinct* but not *better*, and the obvious simulator-side fixes don't change that. The open
question — whether advantage emerges past the classical frontier — remains genuinely open and
untested, framed without overclaiming. The submission stays V1.
