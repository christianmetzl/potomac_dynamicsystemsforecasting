# V2 research — exploratory extensions (NOT part of the V1 submission)

> **Status: exploratory side research.** The competition submission is the Track-A paper, currently
> the latest **`v*-submission`** tag (`v1.5-submission` as of this update; original baseline recoverable at `v1-submission`). Nothing in *this V2
> folder* is referenced by the submitted paper, README, or `cli.py reproduce`, and no core V1 engine
> file was modified to produce it. (V3 — Track B — has a few results surgically folded into the paper
> by citation; V2 does not.)
>
> **Recover the exact ORIGINAL (pre-additions) submission at any time:**
> ```bash
> bash package_submission.sh    # builds the CURRENT submission zip from HEAD
> git archive v1-submission -o V1_original.zip   # or recover the pre-additions original
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

### Experiment C′ — Cross-asset, VERIFIED on high-quality data (`fetch_oxfordman_panel.py`)
The original C run had two caveats (daily GK proxy; calm 2013-2018). We removed **both** by
re-running the *identical* experiment on the **Oxford-Man Institute Realized Library** — the
standard academic realized-measures dataset (Heber-Lunde-Shephard-Sheppard): **true 5-minute
realized variance** for **10 liquid global equity indices** across regions (SPX, DJI, NDX, RUT,
FTSE, DAX, CAC, STOXX50E, N225, HSI), **2000-01 → 2016-09, including the 2008 GFC** (SPX 5-min
RV peaks near ~140% annualised around Lehman). 3,436 common trading days; 6 seeds; HAC-DM; Holm
across targets (SPX/DAX/N225, one per region). Provenance is honest: the Institute discontinued
hosting in 2022, so we pull a widely-mirrored copy of the library spreadsheet (vintage
2016-09-28) from a public GitHub mirror — this covers the GFC but **not** 2020 COVID.

**Crisis-inclusive split** (train < 2007-01-01 → test 2007-2016, spanning the GFC):

| target | HAR-X-cross RMSE | CHIMERA RMSE | CHIMERA DM vs HAR-X-cross | Holm p |
|---|---|---|---|---|
| SPX  | **0.6667** | 0.6995 | +4.43 (worse) | 0.000 |
| DAX  | **0.5290** | 0.5418 | +2.94 (worse) | 0.003 |
| N225 | **0.5766** | 0.5877 | +3.63 (worse) | 0.001 |

**Result: refuted — more decisively than before.** On proper 5-min RV over a genuine crisis,
HAR-X-cross is best for every region and CHIMERA (and ESN/RFF) are **significantly worse** — the
nonlinear maps overfit precisely where it matters. The MZ nuance recurs (CHIMERA MZ edges the
linear bar for DAX 0.425 vs 0.412 and N225 0.431 vs 0.418) but on the RMSE loss the DM test
scores, the linear baseline wins clearly.

**Robustness — calm split** (train < 2014-01-01 → test 2014-2016): HAR-X-cross still best;
CHIMERA **never** significantly differs (all Holm p > 0.05; DM slightly positive = marginally
worse). So the negative is not a crisis artifact — it holds in both regimes.

Reproduce (no API key needed; data is a public mirror, fetched once and cached to a small npz):
```bash
python3 v2_research/fetch_oxfordman_panel.py
python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_oxfordman.npz \
        --targets SPX DAX N225 --train-end 2007-01-01      # crisis-inclusive (headline)
python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_oxfordman.npz \
        --targets SPX DAX N225 --train-end 2014-01-01      # calm robustness
```
*COVID-inclusive extension — attempted via the Massive.com API (see C″).*

### Experiment C″ — Cross-asset-class ETFs via a live n8n→Massive pipeline (`build_massive_etf_panel.py`)
To get an *independent* cross-asset cut we built an end-to-end **n8n pipeline** (workflow
"CHIMERA V2 — Massive Multi-Asset Daily RV", id `5b6nLfOYIvHR888Q`) that calls the **Massive.com**
aggregates API (Polygon-compatible) from n8n's own infrastructure — which reaches Massive even
though this sandbox cannot. Honest findings from **direct probing of the plan** (reported, not
hidden):
- **5-minute intraday → `403 NOT_AUTHORIZED`** ("plan doesn't include this timeframe"): true
  5-min realized variance is **not available** on this tier.
- **Daily history → only ~5 years** (2021-06-28..2026-06-01) even when 2004 was requested:
  **no 2008 GFC, no 2020 COVID** on this tier.

So the Massive panel is, honestly, a **daily Garman-Klass proxy over a recent, crisis-light
window** — *not* a quality upgrade over Oxford-Man (true 5-min, GFC) or V1's `.SPX` (2000-01..
2020-02, GFC in-sample; COVID just outside — see C‴). Its value is a **third, independent
universe**: 10 cross-**asset-class** ETFs
(equity SPY/QQQ/DIA/IWM/EFA/EEM, bonds TLT, gold GLD, sectors XLF/XLE), 1,237 days, recent
regime. Targets one per asset class (SPY/TLT/GLD); train < 2024-06-01.

| target (class) | HAR-X-cross RMSE | CHIMERA RMSE | CHIMERA DM vs HAR-X-cross | Holm p |
|---|---|---|---|---|
| SPY (equity) | **0.8311** | 0.8517 | +2.42 (worse) | 0.028 |
| TLT (bonds)  | **0.6798** | 0.7029 | +2.56 (worse) | 0.028 |
| GLD (gold)   | **0.8349** | 0.8568 | +2.60 (worse) | 0.028 |

**Result: refuted again.** HAR-X-cross is best for every asset class; CHIMERA (and ESN/RFF) are
significantly worse after Holm. The honest negative holds on a *different* universe and the
*recent* regime too. Reproduce (the CSV is committed; re-fetching needs the n8n workflow + a
Massive key):
```bash
python3 v2_research/build_massive_etf_panel.py
python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_massive_etf.npz \
        --targets SPY TLT GLD --train-end 2024-06-01
```

### Experiment C‴ — the COVID-2020 regime (the one crisis no other panel reaches) (`fetch_covid_panel.py`)
*Why:* V1's `.SPX` ends 2020-02-21 (COVID's eve), the Oxford-Man mirror ends 2016, and the
Massive tier starts 2021 — so the **March-2020 COVID shock was untested**. This panel closes that
gap: daily OHLC for **8 global equity indices** (SPX, DAX, CAC, FTSE, OMXS, N225, KOSPI, HSI),
**2006-10 → 2022-06, containing both the 2008 GFC and the 2020 COVID crash** (public mirror
`andymogul/SpilloverVolPrediction`). *Honest quality note:* this is a **daily Garman-Klass
proxy**, not true 5-min RV (GK understates the spike — SPX reads ~81% annualised in Mar-2020 vs
higher true intraday RV); its sole purpose is to add the COVID regime, not to upgrade quality.
COVID-era test: train < 2020-01-01 → **test = 2020–2022 (the COVID crash + recovery)**, targets
SPX/DAX/N225, 6 seeds, HAC-DM, Holm.

| target | HAR-X-cross RMSE | CHIMERA RMSE | CHIMERA DM vs HAR-X-cross | Holm p |
|---|---|---|---|---|
| SPX  | **0.8877** | 0.8898 | +0.40 | 1.000 |
| DAX  | **0.8076** | 0.8092 | +0.39 | 1.000 |
| N225 | **0.7782** | 0.7836 | +1.22 | 0.671 |

**Result: no quantum advantage in the COVID regime either** (all Holm p ≫ 0.05). *Honest nuance,
reported:* unlike the GFC test (where CHIMERA was significantly *worse*), in the COVID era CHIMERA
is statistically **tied** with HAR-X-cross — neither better nor worse — and the nonlinear maps
(ESN/RFF) even edge slightly ahead on SPX/DAX (not significant). So the headline (no advantage)
holds through COVID; the "significantly worse in crises" pattern is GFC-specific, not universal.
Reproduce:
```bash
python3 v2_research/fetch_covid_panel.py
python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_covid.npz \
        --targets SPX DAX N225 --train-end 2020-01-01
```

## What V2 rules out, and what it doesn't
Ruled out (at ≤16 simulable qubits): longer horizons (A), alignment-tuning (B1),
residual hybridization (B2), and **cross-asset high-dimensional spillovers — now verified across
FOUR independent universes: US single stocks (C), global equity indices on true 5-min RV through
the 2008 GFC (C′), cross-asset-class ETFs in the recent regime via a live Massive pipeline (C″),
and 8 global indices through the 2020 COVID crash (C‴)** — all fail to convert the reservoir's
distinctness into a forecasting-accuracy advantage over strong linear baselines. Both major
crises of the century (2008 GFC, 2020 COVID) are now covered. Combined with V1 (1-day univariate),
this is a thorough, honest mapping across five distinct settings: the quantum reservoir is
consistently *competitive and distinct* but not *better* at any simulable scale we can test.

**The one regime still untested** (requires resources beyond this environment):
- **Scale beyond the classical-simulation frontier** on real neutral-atom hardware (50–256
  qubits) — the only regime where "hard to copy" could become a genuine edge, since there a
  classical ESN/RFF can no longer replicate the feature map. Needs qBraid QPU credits;
  `qbraid_submit.py` is the ready, one-flag submission path.

## Honest bottom line
Across five settings (V1 1-day univariate; V2 multi-horizon, alignment-tuned, residual-hybrid,
and cross-asset — the last verified across FOUR independent universes: US single stocks, global
equity indices on true 5-min realized variance through the 2008 GFC, recent cross-asset-class
ETFs via a live Massive.com pipeline, and 8 global indices through the 2020 COVID crash — so both
major crises of the century are covered), at every scale we can classically simulate (≤16 qubits)
the quantum reservoir is *competitive and distinct* but **not better** than strong linear baselines
— and neither the obvious simulator-side fixes, nor a genuine crisis-inclusive intraday dataset,
nor a different asset-class universe, nor the COVID shock change that. This is a comprehensive,
honest map of where the approach does not help. The single remaining open question — whether advantage emerges *past*
the classical-simulation frontier on real hardware — is genuinely open and untested, framed
without overclaiming. The submission stays the Track-A paper (latest `v*-submission` tag).
