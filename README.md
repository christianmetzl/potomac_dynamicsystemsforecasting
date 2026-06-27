# CHIMERA-QRC — Regime-Aware Quantum Reservoir Computing for S&P 500 Realized Volatility

**Team EIGENNEXUS** · Global Industry Challenge 2026 (qBraid · MITRE · JonesTrading) · **Track A — Financial Volatility**
Christian Metzl (Team Lead / Architect) · Fares Eldibani (Data Science) · Juan Manuel Aguiar Hualde (PhD Physics)

This repository is the **agent-reproducible companion** to our Phase-2 paper. Every headline number, table, and figure in the paper is produced by a script here, run on public data included in the repo. It is designed so that a reviewer — or an autonomous agent — can `pip install -r requirements.txt` and `bash run_all.sh` to regenerate the results end-to-end.

---

## TL;DR — what this is and what it honestly shows

**CHIMERA-QRC** is a delay-embedding quantum reservoir for volatility forecasting: eight lagged log realized-variance (RV) values are angle-encoded onto qubits (`RY(π·x)`), evolved under a fixed transverse-field Ising Hamiltonian `U = exp(-iHτ)`, and read out as single + pairwise Pauli-Z expectations (`⟨Z_i⟩, ⟨Z_iZ_j⟩`) into a ridge head that already contains the HAR information set — so any reservoir gain is **genuine nonlinearity beyond HAR**, not missing linear structure.

Honest headline findings (all reproduced by the scripts below):

1. **Beats the classical reservoir, fairly.** At matched feature count the 8-qubit quantum reservoir beats the ESN-108 and a 4× ESN-400 (Diebold–Mariano *p* < 0.001) and joins HAR in the 95% Model Confidence Set, where the ESNs are excluded — at 5–10× lower seed variance.
2. **Tracks regime transitions best (Track A's mandate).** With the 2008 crisis in the test set, **CHIMERA-3scale attains the best Mincer–Zarnowitz R² = 0.591**, above HAR (0.559) and far above the classical reservoirs, whose tracking collapses through the transition (ESN-108 0.089, ESN-400 0.226).
3. **The quantum feature map is measurably distinct and more efficient.** Geometric difference (Huang et al. 2021) **g(ESN→CHIMERA) ≈ 62 vs a 4.3 classical–classical control (~14×)**; after removing HAR's linear structure, the quantum kernel retains **~13× higher residual alignment** than the ESNs (~40× per feature, 3 seeds).
4. **It is a genuine quantum circuit.** Reproduced as an explicit PennyLane circuit matching the engine to **Δ ≈ 5×10⁻¹⁶**, compiling to a shallow **~380-gate** native circuit (gate-model implementable).

Honest scope: on **calm-period point RMSE no method beats HAR** (expected — daily RV is near-optimal territory for HAR's linear long-memory form), and at 8–12 qubits the reservoir is still classically simulable. The Phase-2 claim is regime-transition tracking + parameter-efficient frontier-membership versus the classical reservoir — the *precondition* for advantage at scale — not beating HAR. The unconditional-advantage question is the falsifiable Phase-3 hypothesis (see below).

---

## Quickstart

```bash
pip install -r requirements.txt
bash run_all.sh          # runs the 4 headline experiments (a few minutes total)
```

Or run any experiment individually, e.g. `python3 kernel_analysis.py`.

---

## Repository layout

```
.
├── README.md                  this file
├── requirements.txt
├── run_all.sh                 one-command reproduction of the headline results
│
│   # ---- core engine ----
├── qrc_engine.py              pure-NumPy quantum reservoir: Pauli ops, Ising/Heisenberg H,
│                              RY encoding, RZ feedback, exp(-iHτ) evolution, Pauli-Z readout,
│                              amplitude-damping / depolarizing noise channels
├── delay_qrc.py               DelayEmbeddingQRC: one delay window -> reservoir feature vector
├── multiscale_chimera.py      MultiScaleCHIMERA: τ-bank wrapper (single- or multi-scale)
├── classical_baselines.py     EchoStateNetwork (matched classical reservoir)
├── har_garch_baselines.py     HAR-RV, GARCH(1,1)/GJR-GARCH baselines
├── benchmarks.py              chaotic-systems utilities (Lorenz, normalisation)
├── compute_vpt_util.py        valid-prediction-time utility
├── volatility_data.py         Oxford-Man loader, supervised builder, chronological splits
│
│   # ---- experiments (each prints the paper's numbers) ----
├── vol_fair_benchmark.py      Table 1 (calm window) + DM + Model Confidence Set
├── vol_crisis_benchmark.py    crisis split (GFC in test): RMSE / QLIKE / MZ R² + MCS  [regime result]
├── kernel_analysis.py         geometric difference, kernel-target alignment, effective dim  [Fig 3]
├── sdk_demo.py                explicit PennyLane circuit + Trotterised gate version
├── regime_adaptive_qrc.py     BOCPD changepoint detection + Ising↔Heisenberg switching
├── gk_validation.py           independent 2022–2026 SPY series (Garman–Klass proxy)
├── tests.py                   sanity tests (engine, encoding, readout)
│
├── data/
│   ├── oxfordman_spx_full.csv     Oxford-Man .SPX 5-min realized variance, 2000–2020 (incl. GFC)
│   └── massive_spy_daily.csv      SPY daily OHLCV 2022–2026 (self-ingested via Massive.com/Polygon)
└── figures/
    ├── fig_architecture.png       CHIMERA-QRC pipeline (paper Fig 1)
    ├── fig_cross_window.png       relative RMSE vs HAR (paper Fig 2)
    └── fig_kernel.png             kernel geometry (paper Fig 3)
```

---

## Experiment → claim → expected output

| Script | Produces | Expected headline numbers |
|---|---|---|
| `vol_fair_benchmark.py` | Calm-window benchmark, Table 1, MCS | HAR 0.645 / ESN-108 0.685 / CHIMERA-1s 0.655 RMSE(logRV); CHIMERA & HAR in 95% MCS, ESNs excluded; DM *p*<0.001 vs ESN |
| `vol_crisis_benchmark.py` | Crisis split (GFC 2008 in test) | **CHIMERA-3scale MZ R² = 0.591 > HAR 0.559 ≫ ESN-108 0.089 / ESN-400 0.226**; CHIMERA in MCS, ESN-400 excluded |
| `kernel_analysis.py` | Kernel geometry | **g(ESN→CHIMERA) ≈ 62** vs **3.7–4.3** classical control; residual-KTA (post-HAR) **~13×** the ESN (~40× per feature) |
| `sdk_demo.py` | Explicit quantum circuit | engine vs PennyLane exact **max\|Δ\| ≈ 5×10⁻¹⁶**; Trotter(40) within ~2%; **~380** native gates at 20 layers |
| `gk_validation.py` | Independent current-window check | 2022–2026 SPY (Garman–Klass): MCS = {HAR, CHIMERA} |

Reservoir feature maps use seeds {0,1,2} and are ensembled; kernel metrics are reported across 3 seeds. Numbers are deterministic given the seeds and may vary at the last digit across NumPy/BLAS builds.

---

## Architecture (one screen)

- **Encoding.** Delay window `x_t = [log-RV(t), …, log-RV(t-k)]`, 8 multi-horizon lags (1,2,3,4,5,10,15,22 d), min-max scaled to [0,1] on train only; one value per qubit via `RY(π·x)`.
- **Reservoir.** Fixed transverse-field Ising `H = Σ_{i<j} J_ij Z_iZ_j + h_x Σ_i X_i` (`h_x = 1`, random `J`), evolved `U = exp(-iHτ)`; Heisenberg-XXZ variant for regime switching.
- **Readout.** `⟨Z_i⟩` (n) + `⟨Z_iZ_j⟩` (n(n-1)/2) = 36 features at n=8, concatenated with the HAR information set → ridge head (penalty selected on a validation tail).
- **Four innovations.** (i) multi-scale τ-bank; (ii) measurement feedback (RZ); (iii) regime-adaptive Ising↔Heisenberg switching driven by BOCPD on log-RV; (iv) dissipation-enhanced expressivity (calibrated amplitude damping, noise-as-feature).

---

## Data provenance

Both datasets are public; no proprietary data enters any benchmark.

- **Oxford-Man Institute Realized Library, `.SPX` 5-minute realized variance** — daily, 2000-01-03 to 2020-02-21 (5,052 days, **including the 2008 GFC**), with close prices for GARCH alignment.
  Cite as: *Heber, G., Lunde, A., Shephard, N. & Sheppard, K. (2009). Oxford-Man Institute's Realized Library, University of Oxford.* The original repository has been **discontinued**; the `.SPX` 5-minute RV series remains publicly available via the R packages [`highfrequency`](https://cran.r-project.org/package=highfrequency) (`realized_library`, S&P 500 2000–2019) and [`bvhar`](https://cran.r-project.org/package=bvhar) (`oxfordman`). The exact `.SPX` rows used here are included in `data/oxfordman_spx_full.csv`.
- **SPY daily OHLCV, 2022–2026** — public end-of-day market data, freely available from many sources (e.g. [Stooq](https://stooq.com), Yahoo Finance). We retrieved it via the **Massive.com (formerly Polygon.io)** API (https://massive.com) through a read-only workflow and converted it to a Garman–Klass proxy. The series is included in `data/massive_spy_daily.csv` and can equivalently be regenerated from any public daily-OHLCV source.

---

## Phase-3 plan (the falsifiable bet)

**H0:** the measured parameter-efficiency gap becomes a forecasting-accuracy gap at neutral-atom scale. Concretely, beyond the classical-simulation frontier (≈30 qubits exact; bounded tensor-network rank), **H0 is confirmed if the geometric difference g keeps growing with qubit count and the regime-transition MZ-R² gap over HAR turns positive and significant out-of-sample — refuted if g saturates or that gap stays ≤ 0.**

- **Backbone:** statevector ≤24–28 q → tensor-network/GPU 50–80 q, sweeping qubit count, **encoding density** (more lags, cross-asset/sector RV covariance, intraday/order-flow, data re-uploading — so added qubits encode new information, not the same 8 DOF), shot budget, and noise.
- **Targeted QPU:** QuEra Aquila (neutral-atom, analog Rydberg, up to ~256 atoms via Bloqade/qBraid) at a scale classical simulation can't reach; trapped-ion (IonQ/Quantinuum) gate-based check with ZNE + mthree. Fallback: tensor-network + density-matrix noise emulation.
- **Advantage adjudication:** kernel–target alignment, Fisher-information capacity, and the geometric difference metric (Huang et al. 2021) alongside RMSE / QLIKE / MZ.

The same signal-agnostic architecture was proposed for atmospheric forecasting in Phase 1 (9-spin experimental QRC matching thousand-node classical reservoirs; Hou et al. 2026), supporting CHIMERA-QRC as a general-purpose chaotic-systems engine.

---

## AI collaboration disclosure

Claude (Anthropic) assisted with code and drafting under the team's direction. All formulations, design decisions, and results are the team's own and were produced by executing team code on public data.
