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

## Experiment C — Cross-asset spillovers (`v2_cross_asset.py`)
*Hypothesis (highest-value lead):* the high-dimensional, many-interacting-series setting is
where a high-dimensional quantum feature map is most likely to matter. Data: S&P-500 daily
OHLCV 2013-2018 (public; plotly/datasets mirror), Garman-Klass realized variance for a
10-stock cross-sector basket. Forecast each target's next-day log-RV from the lag-1 log-RV of
the FULL basket (cross-asset state → 10 qubits). Bar = HAR-X-cross (same cross-asset info,
linear). 6 seeds, HAC-DM, Holm across targets.

| target | HAR-X-cross RMSE | CHIMERA RMSE | CHIMERA DM vs HAR-X-cross | Holm p |
|---|---|---|---|---|
| AAPL | **0.8649** | 0.9083 | +2.79 (worse) | 0.017 |
| JPM  | **0.7578** | 0.7669 | +0.67 (worse) | 0.506 |
| XOM  | **0.7473** | 0.7629 | +1.58 (worse) | 0.230 |

**Result: refuted.** HAR-X-cross is best for every target; CHIMERA never wins (significantly
*worse* for AAPL after Holm; n.s. for JPM/XOM). Daily single-stock RV is very noisy
(MZ R² ≈ 0.03–0.32), so the nonlinear reservoirs (ESN, CHIMERA) tend to overfit the noise.
*Honest nuance:* on the **MZ** (forecast-efficiency) metric the nonlinear maps sometimes edge
ahead (e.g. JPM: CHIMERA MZ 0.206 vs HAR-X 0.046; XOM: RFF 0.411 vs 0.310) — but on the
**RMSE loss** that the DM test evaluates, the linear baseline wins. We report both; the
headline (RMSE/DM) shows no quantum advantage. *Caveat:* 2013-2018 daily GK proxy, no
GFC-scale crisis.

**Verify with high-quality data (recommended).** To remove both caveats — proper intraday
5-min realized variance, liquid index ETFs, and a long *crisis-inclusive* window (2004→, incl.
2008 GFC + 2020 COVID) — run `fetch_massive_panel.py` with a Massive.com/Polygon API key
**where that API is reachable** (this sandbox blocks it by network policy), then re-run:
```bash
MASSIVE_API_KEY=...  python3 v2_research/fetch_massive_panel.py --mode rv5 --start 2004-01-01
python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_hq.npz
```
The experiment code is unchanged; only the data improves. (Fetcher provided ready-to-run; not
executed here because `api.polygon.io`/`massive.com` return 000 under the sandbox policy.)

## What V2 rules out, and what it doesn't
Ruled out (at ≤16 simulable qubits): longer horizons (A), alignment-tuning (B1),
residual hybridization (B2), and **cross-asset high-dimensional spillovers (C)** all fail to
convert the reservoir's distinctness into a forecasting-accuracy advantage over strong linear
baselines. Combined with V1 (1-day univariate), this is a thorough, honest mapping across
five distinct settings: the quantum reservoir is consistently *competitive and distinct* but
not *better* at any simulable scale we can test.

**The one regime still untested** (requires resources beyond this environment):
- **Scale beyond the classical-simulation frontier** on real neutral-atom hardware (50–256
  qubits) — the only regime where "hard to copy" could become a genuine edge, since there a
  classical ESN/RFF can no longer replicate the feature map. Needs qBraid QPU credits;
  `qbraid_submit.py` is the ready, one-flag submission path.

## Honest bottom line
Across five settings (V1 1-day univariate; V2 multi-horizon, alignment-tuned, residual-hybrid,
and cross-asset), at every scale we can classically simulate (≤16 qubits) the quantum reservoir
is *competitive and distinct* but **not better** than strong linear baselines — and the obvious
simulator-side fixes don't change that. This is now a comprehensive, honest map of where the
approach does not help. The single remaining open question — whether advantage emerges *past*
the classical-simulation frontier on real hardware — is genuinely open and untested, framed
without overclaiming. The submission stays V1 (tag `v1-submission`).
