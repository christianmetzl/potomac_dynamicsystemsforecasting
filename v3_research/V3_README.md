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

## Track-B spec (now confirmed from the official Phase-3 brief)
> *Track B — Weather Time-Series Forecasting:* "Using **real-world weather station data**
> (temperature, pressure, humidity, wind), design a QRC that forecasts atmospheric variables over
> short horizons." Suggested sources: **NOAA ISD/ASOS**, ECMWF ERA5, NOAA GFS. Recommended Track-B
> **baselines: Persistence, ARIMA, ESN, NWP-style**. Metrics: **RMSE, MAE, and Valid Prediction
> Time (VPT)** (Lyapunov-normalized horizon at which forecast error exceeds a threshold). Also
> required across both tracks: the common **MNIST** benchmark and a demonstration across **qubit
> counts (5/10/15)** under **depolarizing + amplitude-damping** noise.

**How this V3 maps to the spec, honestly:**
| spec item | this V3 | gap to full spec |
|---|---|---|
| real-world weather station data | **Jena Climate** (MPI station, hourly T/p/rh/wind) ✓ | NOAA ISD/ASOS is the *suggested* source — Jena qualifies as real station data but isn't NOAA |
| forecast atmospheric variable | **temperature** at h=1, h=24 ✓ | could add pressure/humidity |
| baselines | Persistence ✓, ESN ✓, linear (AR-X, ≈ARIMA-lite) | ARIMA proper + an NWP-style reference not run |
| metrics | RMSE ✓, MAE ✓ | **VPT not yet computed** (needs autonomous rollout) |
| qubit-count + noise sweep | n=10 only here | 5/10/15 sweep + depol/amp-damp not yet run for weather |

So this V3 is a **valid, on-task Track-B exploration** (real weather, real baselines, real metrics),
but it is **not** a fully spec-complete Track-B *submission* — it omits VPT, a proper ARIMA, the
qubit/noise sweep, and ideally NOAA data. Those are the concrete steps to make it submission-grade
(see "next steps"). The submission remains V1 (Track A).

## Why V3 exists
Two reasons. (1) The user asked to explore Track B without touching the submission. (2) Weather is
**chaotic / nonlinear**, the opposite of realized volatility (which is linear-long-memory-dominated)
— so it is the regime with the *most* headroom for a nonlinear reservoir, and therefore the most
informative place to ask whether the quantum reservoir is at least *competitive* (or whether the
honest negative is universal). We run the **same CHIMERA engine** and the **same adversarial
protocol** as Track A (controls that nest a linear block; HAC-DM), so the comparison is apples-to-
apples with the submission.

## Data
**Jena Climate** (Max-Planck-Institute for Biogeochemistry), 2009–2016, 10-minute sampling, 14
atmospheric variables — the canonical weather time-series benchmark (Keras tutorials). Public
mirror on `storage.googleapis.com` (reachable here). Resampled to **hourly** (70,038 rows × 6 vars:
T, p, rh, VPmax, wv, Tdew), cached to `jena_hourly.npz`. `fetch_jena.py` reproduces it.

## Experiment — hourly temperature forecast (`v3_weather.py`)
Forecast T (°C) **h** hours ahead from a **10-qubit informed window** = [5 recent hourly T lags +
current p, rh, VPmax, wv, Tdew] (all 10 qubits informed, Axis-B style). Models share the same
information; CHIMERA/ESN/RFF **nest the linear block** (so a quantum win needs nonlinearity beyond
the linear span — identical discipline to Track A's HAR-X). Horizons h=1 (next hour) and h=24 (next
day). 5 seeds; metric RMSE/MAE (°C) and skill vs persistence; Diebold-Mariano (Newey-West HAC,
lag ≥ h) comparing CHIMERA to the best classical model.

### Results (full run; 5 seeds; ~26k-hr span; 70/30 chronological; test ≈ 7,800 hrs)

| horizon | Persistence | Linear (AR-X) | ESN (best) | RFF | CHIMERA | CHIMERA vs ESN |
|---|---|---|---|---|---|---|
| **h=1**  | 1.002 | 0.740 (26.2%) | **0.714 (28.7%)** | 0.728 (27.4%) | 0.725 (27.6%) | DM(HAC) +6.22, p<.001 (worse) |
| **h=24** | 3.111 | 3.029 (2.6%)  | **2.842 (8.6%)**  | 2.895 (7.0%)  | 2.905 (6.6%)  | DM(HAC) +4.86, p<.001 (worse) |

*(RMSE in °C; % = skill vs persistence. Numbers in `v3_weather_results.npy`.)*

**Result: honest negative, and instructive.** Reservoirs add real value over persistence and a
strong linear model — and *more so at the longer horizon*: at h=24 the linear model gets only 2.6%
skill while the reservoirs get ~7–9%, confirming that nonlinearity matters more as the horizon
grows. **But the *quantum* reservoir is competitive, not better** — CHIMERA trails the classical
ESN at both horizons (significantly, DM p<.001). So even in a chaotic/nonlinear domain with genuine
nonlinear headroom, the quantum reservoir does not beat a matched classical one.

## How to reproduce
```bash
python3 v3_research/fetch_jena.py                 # download + cache hourly weather (once)
python3 v3_research/v3_weather.py                 # h=1 and h=24, 5 seeds
python3 v3_research/v3_weather.py --quick         # fast smoke (h=1, 3 seeds)
```

## Next steps to make this a spec-complete Track-B submission (not yet done)
Now that the official spec is confirmed, the concrete gaps to a full Track-B submission are:
1. **Valid Prediction Time (VPT)** — the spec's chaotic-forecasting metric: autonomous closed-loop
   rollout, error-threshold horizon normalized by Lyapunov time (Lorenz-63 is the standard testbed;
   cf. Ahmed-Tennie-Magri 2025). The single most discriminating reservoir benchmark. Deferred so we
   don't ship a half-tested VPT harness.
2. **ARIMA** (proper Box-Jenkins) and an **NWP-style** reference (NOAA GFS / ECMWF), per the Track-B
   baseline list (we currently use persistence + ESN + a linear AR-X stand-in).
3. **Qubit-count sweep (5/10/15) + depolarizing/amplitude-damping noise** on the weather task (we
   have these for Track A; here only n=10, noiseless).
4. Ideally **NOAA ISD/ASOS** station data (the suggested source) and pressure/humidity targets, not
   just the Jena temperature series.

## Honest bottom line
Across Track A (realized volatility) and Track B (weather temperature), at simulable scale the
quantum reservoir is *competitive and distinct* but **not better** than strong classical baselines —
the negative is **domain-general**, not an artifact of the linear-long-memory nature of volatility.
Weather even gives the reservoir paradigm *more* to work with (reservoirs beat a linear model by a
wider margin, especially at h=24), yet a matched classical ESN still edges out the quantum reservoir
at every horizon. This strengthens, rather than weakens, the V1 thesis: the honest no-advantage
finding holds across two very different domains. The submission stays V1 (tag `v1-submission`).

*Caveats, stated plainly:* (i) this is a *valid on-task* Track-B exploration but **not a
spec-complete Track-B submission** — VPT, ARIMA/NWP baselines, the 5/10/15 qubit + noise sweep, and
ideally NOAA data are not yet done (see "next steps"); (ii) a single fixed reservoir family /
encoding was tested; (iii) Jena (MPI) is real station data but not the suggested NOAA source.
