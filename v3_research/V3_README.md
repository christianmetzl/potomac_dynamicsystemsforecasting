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

## Honest scope caveat (read first)
The official **GIC-2026 Track-B brief is not in this repo**, so the precise Track-B task is
**inferred**, not known. We take Track B to be *weather/climate time-series forecasting* and use
the standard public benchmark and a standard target (temperature). If the real Track-B spec
differs (e.g. precipitation, a spatial field, a specific horizon/metric), the **engine and the
adversarial protocol transfer unchanged** — only the target series changes. We flag this openly so
nothing here is mistaken for a verified Track-B result.

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

## Natural next probe (not yet done)
A **chaotic-dynamics / valid-prediction-time (VPT)** benchmark (e.g. Lorenz-63, the standard RC
chaos task; cf. Ahmed-Tennie-Magri 2025) in *autonomous closed-loop* rollout — the single setting
where the reservoir-computing paradigm is strongest and where a quantum-vs-classical-reservoir
comparison is most discriminating. Deferred so we don't ship a half-tested VPT harness.

## Honest bottom line
Across Track A (realized volatility) and Track B (weather temperature), at simulable scale the
quantum reservoir is *competitive and distinct* but **not better** than strong classical baselines —
the negative is **domain-general**, not an artifact of the linear-long-memory nature of volatility.
Weather even gives the reservoir paradigm *more* to work with (reservoirs beat a linear model by a
wider margin, especially at h=24), yet a matched classical ESN still edges out the quantum reservoir
at every horizon. This strengthens, rather than weakens, the V1 thesis: the honest no-advantage
finding holds across two very different domains. The submission stays V1 (tag `v1-submission`).

*Caveats, stated plainly:* (i) the Track-B task is inferred (no official brief in-repo); (ii) a
single fixed reservoir family / encoding was tested; (iii) the most discriminating reservoir
benchmark — autonomous chaotic-dynamics VPT (Lorenz-63) — is deferred, not done.
