# V3 research — Track B (weather) exploration (NOT part of the V1 submission)

> **Status: exploratory. The competition submission is V1 (Track A), frozen at git tag
> `v1-submission`.** Nothing in this folder is referenced by the V1 paper, README, or
> `cli.py reproduce`, and no V1 file was modified to produce it. V2 (Track-A extensions) and V3
> (this, Track B) are both side research.
>
> **Revert to / rebuild the exact V1 submission at any time:**
> ```bash
> git archive v1-submission -o EIGENNEXUS_Challenge_Phase3.zip
> ```

## Track-B spec (confirmed from the official Phase-3 brief)
> *Track B — Weather Time-Series Forecasting:* "Using **real-world weather station data**
> (temperature, pressure, humidity, wind), design a QRC that forecasts atmospheric variables over
> short horizons." Suggested sources: **NOAA ISD/ASOS**, ECMWF ERA5, NOAA GFS. Recommended Track-B
> **baselines: Persistence, ARIMA, ESN, NWP-style**. Metrics: **RMSE, MAE, and Valid Prediction
> Time (VPT)** (Lyapunov-normalized horizon at which forecast error exceeds a threshold). Also
> required across both tracks: the common **MNIST** benchmark and a demonstration across **qubit
> counts (5/10/15)** under **depolarizing + amplitude-damping** noise.

**How this V3 now maps to the spec (after the most recent work):**
| spec item | this V3 | status |
|---|---|---|
| real-world weather **station** data | **NOAA ISD** (Chicago O'Hare, the *suggested* source) **and** Jena Climate (MPI station) | ✓ suggested source now used |
| forecast atmospheric variable | **temperature** at h=1, h=24 | ✓ (pressure/humidity left as extension) |
| baselines: Persistence, ARIMA, ESN, NWP | Persistence ✓, **ARIMA ✓** (proper Box-Jenkins), ESN ✓, linear AR-X ✓ | ✓ except NWP-style (needs external forecast feed) |
| metrics: RMSE, MAE, **VPT** | RMSE ✓, MAE ✓, **VPT ✓** (Lorenz-63, static **and** recurrent) | ✓ |
| qubit-count **5/10/15** + depol/amp-damp noise | **n=5/10/15 sweep ✓**, noise at n=5 ✓ (Track A covers n≤10 fully) | ✓ |

So V3 is now a **substantively spec-aligned Track-B exploration**: the suggested NOAA source, the
named ARIMA/Persistence/ESN baselines, RMSE/MAE/VPT (including the architecturally-correct recurrent
QRC), and the 5/10/15 qubit + noise sweep are all done. Remaining gaps are an NWP-style reference
(needs an external numerical-forecast feed) and pressure/humidity targets. **The submission remains
V1 (Track A); this stays side research.**

## Why V3 exists
Two reasons. (1) The user asked to explore Track B without touching the submission. (2) Weather is
**chaotic / nonlinear**, the opposite of realized volatility (linear-long-memory-dominated) — so it
is the regime with the *most* headroom for a nonlinear reservoir, and therefore the most informative
place to ask whether the quantum reservoir is at least *competitive* (or whether the honest negative
is universal). We run the **same CHIMERA engine** and the **same adversarial protocol** as Track A
(controls that nest a linear block; HAC-DM), so the comparison is apples-to-apples with V1.

## Data
- **NOAA ISD** (the brief's *suggested* source) — hourly station records for **Chicago O'Hare**
  (USAF 725300 / WBAN 94846), 2010–2016, from the public `noaa-isd-pds` S3 bucket. Parsed mandatory
  fixed-width fields (T, dewpoint, sea-level pressure, wind), derived RH / saturation vapour
  pressure (Magnus), resampled to a regular hourly grid → **61,368 hourly rows × 6 vars**
  (`noaa_hourly.npz`, format identical to Jena). `fetch_noaa.py` reproduces it.
- **Jena Climate** (MPI Biogeochemistry), 2009–2016, the canonical weather-forecasting benchmark.
  Resampled to hourly → **70,038 rows × 6 vars** (`jena_hourly.npz`). `fetch_jena.py` reproduces it.

Using both lets us check the result is not a single-station artifact.

## Experiment 1 — hourly temperature forecast (`v3_weather.py`)
Forecast T (°C) **h** hours ahead from a **10-qubit informed window** = [5 recent hourly T lags +
current p, rh, VPmax, wv, Tdew] (all 10 qubits informed, Axis-B style). Models share the same
information; CHIMERA/ESN/RFF **nest the linear block** (so a quantum win needs nonlinearity beyond
the linear span — identical discipline to Track A's HAR-X). Horizons h=1 and h=24, 5 seeds; RMSE/MAE
(°C) + skill vs persistence; Diebold-Mariano (Newey-West HAC, lag ≥ h) vs the best classical model.

### NOAA — Chicago O'Hare (the suggested source; `--data noaa_hourly.npz`)
| horizon | Persistence | Linear (AR-X) | ESN (best) | RFF | CHIMERA | CHIMERA vs best |
|---|---|---|---|---|---|---|
| **h=1**  | 1.086 | 0.899 (17.3%) | **0.880 (19.0%)** | 0.887 (18.4%) | 0.888 (18.2%) | DM(HAC) +5.94, p<.001 (worse) |
| **h=24** | 4.549 | 4.105 (9.8%)  | **3.996 (12.2%)** | 4.029 (11.4%) | 4.050 (11.0%) | DM(HAC) +2.08, p=.037 (worse) |

### Jena (MPI station)
| horizon | Persistence | Linear (AR-X) | ESN (best) | RFF | CHIMERA | CHIMERA vs best |
|---|---|---|---|---|---|---|
| **h=1**  | 1.002 | 0.740 (26.2%) | **0.714 (28.7%)** | 0.728 (27.4%) | 0.725 (27.6%) | DM(HAC) +6.22, p<.001 (worse) |
| **h=24** | 3.111 | 3.029 (2.6%)  | **2.842 (8.6%)**  | 2.895 (7.0%)  | 2.905 (6.6%)  | DM(HAC) +4.86, p<.001 (worse) |

*(RMSE in °C; % = skill vs persistence. `v3_weather_results_noaa.npy`, `v3_weather_results.npy`.)*

**Result: the same honest negative, on both stations including the suggested NOAA source.**
Reservoirs add real value over persistence and a strong linear model — and *more so at the longer
horizon* (at Jena h=24 the linear model gets 2.6% skill while reservoirs get ~7–9%, confirming
nonlinearity matters more as the horizon grows). **But the *quantum* reservoir is competitive, not
better** — CHIMERA trails the classical ESN at every horizon on both datasets (significantly by
HAC-DM). On NOAA it lands within ~0.01 °C of the ESN yet is still significantly worse — the closest
it gets, but not ahead.

## Experiment 2 — ARIMA baseline (`arima_weather.py`)
The brief names ARIMA. ARIMA(3,0,2) one-step (h=1) on Jena: **RMSE 0.741 °C** (26.1% skill vs
persistence 1.002) — essentially the linear AR-X bar, and **CHIMERA (0.725) edges it**, as it edges
the linear block. Multi-step ARIMA needs seasonal SARIMA (24-h cycle); the linear AR-X serves as the
multi-step linear/ARIMA-family bar in Experiment 1.

## Experiment 3 — qubit-count (5/10/15) + noise sweep (`v3_weather_sweep.py`)
The spec's cross-track requirement, on the weather task (Jena T+1h; n≤12 dense, n=15 sparse-exact;
depol/amp-damp density-matrix channels at n=5; Track A covers the full n≤10 noise frontier):

| n (qubits) | noiseless RMSE (°C) | skill vs persistence | noise (depol / amp-damp) |
|---|---|---|---|
| 5  | 0.864 | −5.8% | 0.864 / 0.864 (Δ≈0, invariant) |
| 10 | 0.692 | +15.2% | — |
| 15 | **0.677** | **+17.0%** | — |

**Accuracy improves monotonically with qubit count** (0.864 → 0.692 → 0.677), with diminishing
returns from 10→15. Readout-level depolarizing/amplitude-damping noise at n=5 is **invariant** under
per-feature standardization — the same mechanism documented in Track A's noise study (the apparent
"noise invariance" of readout-only channels is a standardization effect; per-layer noise does
degrade). More qubits help the quantum model, yet (Experiment 1) it still only ties the classical
ESN — the no-advantage is not a too-few-qubits artifact.

## Experiment 4 — Valid Prediction Time, static reservoirs (`lorenz_vpt.py`)
VPT is the brief's chaotic-forecasting metric: autonomous closed-loop rollout, horizon (in Lyapunov
times) at which normalized error first exceeds 0.4. Lorenz-63 (σ=10, ρ=28, β=8/3), 25 ICs, 3 seeds.

| model (static delay-window) | VPT (Lyapunov times) |
|---|---|
| Persistence | 0.07 |
| Linear | 0.20 |
| **RFF** (best static) | **1.18** |
| CHIMERA | 0.49 |
| *(recurrent reference: ESN)* | *2.42* |

**Matched-paradigm (both static): CHIMERA 0.49 does not beat RFF 1.18 — no quantum advantage on
VPT.** The recurrent ESN (2.42) far exceeds all static maps, but that 0.49-vs-2.42 gap is an
*architecture* difference (static vs recurrent), not quantum-vs-classical — which is why RFF is the
fair classical bar here, and why we then built the recurrent QRC (Experiment 5).

## Experiment 5 — the recurrent CHIMERA, the architecturally-correct QRC (`recurrent_qrc.py`)
The static delay-window QRC keeps no quantum state between steps — wrong for autonomous chaotic
rollout. The QRC literature (Fujii-Nakajima 2017; Kornjača 2024; Li 2025) uses a **persistent
quantum state** with distinct input + memory qubits: each step resets only the input qubits, keeps
the memory qubits, and evolves the whole system (the quantum state *is* the reservoir memory).
Built density-matrix-exact (n=8 = 3 input + 5 memory) and run on the **fair recurrent-vs-recurrent**
Lorenz-63 VPT test:

| model | VPT (Lyapunov times) |
|---|---|
| **Recurrent-CHIMERA (n=8)** | **0.50 ± 0.22** (one-step train R² = 1.000) |
| ESN, **size-matched** (36 nodes) | 0.61 |
| ESN, strong (300 nodes) | 2.34 |

**Even in the architecturally-correct, size-matched recurrent paradigm, the quantum reservoir is
competitive, not better** (0.50 vs the matched ESN's 0.61 — the *closest* a quantum reservoir comes
to a classical equivalent anywhere in this project). Scaling within reach helps (n=7→8 raised VPT
0.21→0.50). **Diagnosed mechanism (a citable, honest insight):** one-step R² is a perfect 1.000 yet
autonomous VPT is low — **unitary quantum evolution is norm-preserving (non-dissipative), so it
lacks the contraction that gives classical ESNs their autonomous stability ("generalized
synchronization")** — exactly the stability problem of Ahmed-Tennie-Magri (2025, a Challenge
reference). A large dissipative ESN therefore far exceeds any n≤8 unitary reservoir. *Open frontier:*
engineered dissipation + the 100+ qubit regime (Kornjača 2024) — beyond exact simulation.

## How to reproduce
```bash
python3 v3_research/fetch_noaa.py                          # NOAA ISD hourly (suggested source)
python3 v3_research/v3_weather.py --data noaa_hourly.npz   # forecast on NOAA, h=1 & h=24
python3 v3_research/fetch_jena.py                          # Jena hourly (cross-check station)
python3 v3_research/v3_weather.py                          # forecast on Jena, h=1 & h=24
python3 v3_research/arima_weather.py                       # named ARIMA baseline (h=1)
python3 v3_research/v3_weather_sweep.py                    # 5/10/15 qubit + noise sweep (n=15 ~30 min)
python3 v3_research/lorenz_vpt.py                          # VPT, static reservoirs
python3 v3_research/recurrent_qrc.py                       # VPT, recurrent QRC vs ESN (fair)
```

## What this means for our V1 findings in finance
This was the point of running Track B, and the answer is that **V3 strengthens, rather than
weakens, the V1 conclusion** — in three concrete ways:

1. **It kills the most natural objection to V1.** A skeptic could say V1's no-advantage is an
   artifact of *choosing realized volatility* — a linear-long-memory series with little nonlinear
   headroom, so of course a nonlinear quantum reservoir can't pull ahead. V3 takes the **same engine
   and the same adversarial protocol to the opposite regime** — chaotic, nonlinear weather, where a
   nonlinear reservoir has the *most* to gain (reservoirs beat the linear model by a *wider* margin,
   especially at h=24). The quantum reservoir still only **ties** a matched classical ESN, on **two**
   stations (NOAA *and* Jena) and on the **chaotic VPT** metric. So the negative is **domain-general
   and metric-general**, not a property of volatility. That is the single most credibility-relevant
   result for V1: the finding generalizes to where you'd *most* expect a win.

2. **It stress-tests the one architectural caveat V1 carried — and the caveat holds.** V1 (and
   V2/v3_weather) used the **static delay-embedding** QRC. The honest open question was whether a
   *recurrent* quantum reservoir (the literature's architecture for autonomous dynamics) would do
   better. We built it and tested it fairly (Experiment 5): even there, at simulable scale, it is
   **competitive, not better** (0.50 vs matched ESN 0.61) — with a *diagnosed* reason
   (non-dissipative unitary dynamics → weak generalized synchronization). So switching to the
   "better" architecture does **not** overturn the negative.

3. **Specifically for RV, it shows V1 picked the right architecture and the conclusion is robustly
   scoped.** RV forecasting is a **one-step-ahead, linear-long-memory** problem. The place a
   recurrent / large quantum memory could matter is **autonomous multi-step chaotic rollout (VPT)**
   — a regime RV does not live in (V1's recurrent-CHIMERA one-step R² is a perfect 1.000; the
   difficulty in VPT is the *rollout*, not the one-step map RV actually needs). So the static QRC was
   the appropriate choice for RV, and even the QRC's best shot (recurrence) targets a regime RV
   doesn't occupy. Net: **RV is a domain where a quantum reservoir is *least* favored, weather is
   where it is *most* favored, and it wins in neither** — the strongest honest form a negative can
   take.

The qubit-count evidence reinforces this: more qubits *do* help the quantum model (n=5→10→15:
0.864→0.692→0.677, Experiment 3; and V1's `frontier_scaling.py` shows D_eff/rank growing with n),
yet a matched classical reservoir keeps pace — so the no-advantage is not a too-small-reservoir
artifact either. The one genuinely open frontier is the same one V1 already names honestly:
**100+ qubit recurrent reservoirs with engineered dissipation** (Kornjača 2024), beyond exact
classical simulation. V3 doesn't just restate that caveat — it **sharpens the mechanism** (why a
unitary reservoir lacks autonomous stability), which is a stronger, more citable position than V1
had on its own.

## Honest bottom line
Across Track A (realized volatility) and Track B (weather temperature on two stations), and across
RMSE / MAE / QLIKE / Mincer-Zarnowitz / VPT / information-processing-capacity, in **static and
recurrent** paradigms, at simulable scale the quantum reservoir is *competitive and distinct* but
**not better** than strong classical baselines. The negative is **domain-, metric-, and
architecture-general** — which is exactly what makes V1's honest no-advantage finding credible rather
than a single-task artifact. The submission stays V1 (tag `v1-submission`).

*Caveats, stated plainly:* (i) a single fixed reservoir family / encoding was tested per paradigm;
(ii) noise channels for weather were exercised at n=5 (Track A covers n≤10 fully); (iii) no
NWP-style baseline and only temperature targets; (iv) the 100+ qubit recurrent + engineered-
dissipation regime is untested (beyond exact simulation) and remains the honest open frontier.
