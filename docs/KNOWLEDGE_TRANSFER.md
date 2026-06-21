# CHIMERA-QRC — Knowledge Transfer & Project State
*Last updated: 2026-06-20 · Owner: Christian Metzl (Team EIGENNEXUS) · Status: **Phase 3 Finalist**, GIC 2026*

> **Purpose.** This file is the single source of truth for the CHIMERA-QRC project. It lets a new collaborator — human or a fresh Claude conversation — pick up exactly where we are, with every verified number, decision, and next step. Pair it with `TRANSFER_PROMPT.md` to bootstrap a new session.

---

## 1. Who & what

- **Project:** CHIMERA-QRC — a regime-aware **Quantum Reservoir Computing** model for forecasting S&P 500 **realized volatility**.
- **Competition:** Connected DMV **Global Industry Challenge (GIC) 2026** — qBraid (compute) · MITRE · JonesTrading. Theme: "Dynamic Systems Forecasting." **Track A — Financial Volatility.**
- **Team EIGENNEXUS:** Christian Metzl (Team Lead / Architect — connect@christianmetzl.com, aqora.io/christianmetzl); Fares Eldibani (Data Science — faresdibany@gmail.com); Juan Manuel Aguiar Hualde (PhD Physics — juanmanuel.aguiar@gmail.com).
- **Stage:** Phase 1 ✅ → Phase 2 ✅ (submitted) → **Phase 3 (Final)** — shortlisted; full Phase-3 requirements/QC-access/deadline land on Aqora "by end of the week" (as of 2026-06-20).
- **CHIMERA** = **C**haotic **H**ybrid **I**ntelligence via **M**ulti-scale **E**ntangled **R**eservoir **A**rchitecture.

---

## 2. The project in one page

**What it is.** A delay-embedding quantum reservoir: eight lagged log-realized-variance values are angle-encoded onto qubits, evolved under a fixed transverse-field Ising Hamiltonian, and read out as single- and pairwise-Pauli-Z expectations into a ridge head that **already contains the HAR information set** — so any reservoir gain is genuine nonlinearity *beyond* HAR, not missing linear structure.

**The honest headline findings (all reproduced by code):**
1. **Beats the matched classical reservoir, fairly.** At equal feature count the 8-qubit quantum reservoir beats ESN-108 and a 4× ESN-400 (Diebold–Mariano p<0.001) and joins HAR in the 95% Model Confidence Set, where the ESNs are excluded — at 2–30× lower seed variance.
2. **Best regime-transition tracking (Track A's mandate).** With the 2008 crisis in the test set, CHIMERA-3scale attains the best Mincer–Zarnowitz R² = **0.591** > HAR 0.559 ≫ ESN-108 0.089 / ESN-400 0.226.
3. **The quantum feature map is measurably distinct & more efficient.** Geometric difference g(ESN→CHIMERA) ≈ **62** vs a 4.3 classical–classical control (~14×); after removing HAR's linear structure the quantum kernel keeps ~**13×** higher residual alignment (~40× per feature, 3 seeds).
4. **It is a genuine quantum circuit.** Reproduced as an explicit PennyLane circuit matching the engine to Δ ≈ **5×10⁻¹⁶**, compiling to a shallow ~**380-gate** native circuit.

**Honest scope / ceiling.** On **calm-period point RMSE no method beats HAR** (expected — daily RV is near-optimal territory for HAR's linear long-memory form). At 8–12 qubits the reservoir is still classically simulable, so distinctness is *necessary but not sufficient*. **Unconditional quantum advantage is the falsifiable Phase-3 hypothesis, not a Phase-2 claim.**

---

## 3. Architecture (full technical spec)

- **Input / encoding.** Delay window of **8 multi-horizon lags** of log-RV: lags **{1, 2, 3, 4, 5, 10, 15, 22} days**. Min–max scaled to [0,1] **on the training split only** (no leakage). Encoded one value per qubit via **RY(π·x)**.
- **Reservoir.** Fixed transverse-field **Ising** Hamiltonian `H = Σ_{i<j} J_ij Z_iZ_j + h_x Σ_i X_i`, with `h_x = 1.0`, random couplings `J` from `generate_coupling_matrix(n_qubits, connectivity=0.5, seed)`. Unitary evolution `U = exp(−iHτ)`, **τ = 2.0** (single-scale); multi-scale variants use a τ-bank. A **Heisenberg-XXZ** variant is used for the regime-switching mode.
- **Readout.** `⟨Z_i⟩` (n) + `⟨Z_iZ_j⟩` (n(n−1)/2) → **36 features at n=8**, concatenated with the **HAR information set**, fed to a **ridge** head (penalty selected on a validation tail). Three-seed ensembling, seeds **(0,1,2)**.
- **Four innovations.** (i) multi-scale τ-bank; (ii) measurement-feedback (RZ); (iii) regime-adaptive **Ising↔Heisenberg switching** driven by **BOCPD** (Bayesian Online Changepoint Detection) on log-RV; (iv) **dissipation-enhanced expressivity** (calibrated amplitude damping — *noise-as-feature*).

---

## 4. Verified results (exact numbers — preserve these)

**Table 1 — RMSE of log realized variance (lower is better).** *Note: the 2025–26 window uses a Garman–Klass proxy; RMSE levels are not comparable across estimators, though within-window rankings (MCS, DM) are valid.*

| Window (estimator) | HAR | ESN-108 | ESN-400 | CHIMERA-1s | Notes |
|---|---|---|---|---|---|
| Calm 2014–20 (5-min RV) | 0.645 | 0.685 | 0.696 | **0.655** | DM(CHIMERA-3s vs ESN-108) = −3.9, p<.001; MCS = {HAR, ESN-108(borderline), CHIMERA-1s, CHIMERA-3s}; ESN-400 excluded |
| Crisis 2007–12 (GFC in test) | 0.629 | 0.714 | 0.717 | **0.639** | DM = −4.0, p<.001; ESN-400 excluded from MCS |
| Current 2025–26 (Garman–Klass) | 0.882 | 0.912 | 0.972 | **0.884** | MCS = {HAR, CHIMERA-1s} |

**Mincer–Zarnowitz R² (crisis window, forecast efficiency):** HAR 0.559 · ESN-108 0.089 · ESN-400 0.226 · CHIMERA-1s 0.547 · **CHIMERA-3scale 0.591 (best, beats HAR).**

**Kernel geometry (3 seeds):** g(ESN→CHIMERA) ≈ 62 ± 2 vs control g(ESN→ESN′) ≈ 4.3 ± 0.9 (~14×). Residual kernel-target alignment (post-HAR): quantum 0.0014 vs ESN 0.0001 (~13×; ~40× per feature).

**SDK reproduction (PennyLane):** engine vs exact-evolution circuit Δ ≈ 5.0×10⁻¹⁶; Trotter(20) Δ ≈ 0.04, Trotter(40) Δ ≈ 0.02; ~380 native gates (11 ZZ + 8 RX per layer × 20).

**Seed variance:** CHIMERA-1s vs matched ESN-108 → 30× (calm), 10× (crisis), 2× (current) → stated as **2–30× lower**.

---

## 5. Data provenance (public; cite correctly)

- **Oxford-Man Institute Realized Library, `.SPX` 5-minute realized variance** — daily 2000-01-03 to 2020-02-21 (5,052 days, incl. 2008 GFC), with close prices for GARCH alignment.
  - **Cite:** *Heber, G., Lunde, A., Shephard, N. & Sheppard, K. (2009). Oxford-Man Institute's Realized Library, University of Oxford.*
  - Original repository **discontinued**; `.SPX` series is publicly redistributed via the R packages **`highfrequency`** (`realized_library`, S&P 500 2000–2019, https://cran.r-project.org/package=highfrequency) and **`bvhar`** (`oxfordman`). The exact `.SPX` rows used are bundled in `repo/data/oxfordman_spx_full.csv`.
- **SPY daily OHLCV, 2022–2026** — **public end-of-day market data**, freely available from many sources (Stooq, Yahoo Finance). Retrieved via the **Massive.com (formerly Polygon.io)** API (https://massive.com) through a read-only workflow; converted to a Garman–Klass proxy. Bundled in `repo/data/massive_spy_daily.csv`; regenerable from any public daily-OHLCV source.
- **Compliance:** all data public; no proprietary data in any benchmark. *(A paid API for public data ≠ proprietary data — the rule targets private datasets, not the closing price of SPY.)*

---

## 6. Repository (the reproducible package)

Location in this bundle: `2_Reproducible_Repo/chimera-qrc/` (git-initialized; first commit present). One-command reproduction:

```bash
pip install -r requirements.txt
bash run_all.sh
```

**Module map:** engine — `qrc_engine.py`, `delay_qrc.py`, `multiscale_chimera.py`; baselines — `classical_baselines.py` (ESN), `har_garch_baselines.py`; data — `volatility_data.py` (has a `_find()` path-resolver so scripts run from anywhere); experiments — `vol_fair_benchmark.py` (calm Table 1 + MCS), `vol_crisis_benchmark.py` (regime MZ result), `kernel_analysis.py` (geometry, Fig 3), `sdk_demo.py` (PennyLane circuit), `gk_validation.py` (current window), `regime_adaptive_qrc.py` (BOCPD switching); `tests.py`; utilities — `benchmarks.py`, `compute_vpt_util.py`. Data in `data/`, figures in `figures/`.

**Reproducibility note:** every headline number above has been re-run from this package and matches. Numbers are deterministic given seeds (0,1,2); last-digit drift across NumPy/BLAS builds is possible.

---

## 7. Tooling stack

- **Quantum:** PennyLane 0.45.0 (statevector + the explicit-circuit SDK demo). Python ≥ 3.10.
- **Classical ML / stats:** numpy, scipy, pandas, statsmodels, arch.
- **Phase-3 compute (planned):** **qBraid** — the challenge's official platform — gives one-line vendor-agnostic access to QPUs (IonQ, Quantinuum, QuEra, Rigetti, IQM, Pasqal) and NVIDIA **GH200** GPUs for tensor-network/statevector simulation. SDK: `pip install qbraid>=0.11.0`; work on lab.qbraid.com.
- **Christian's broader stack (consistent across projects):** Lovable + Supabase + n8n + Claude API + Massive.com.

---

## 8. Phase 2 submission — status

- **File submitted:** `1_Phase2_Submission/EIGENNEXUS__Phase2_Version1.pdf` (naming convention `TeamName__PhaseX_VersionX.pdf`). Editable: `.docx`.
- **Structure:** 5 pages = official GIC cover (page 1, unmodified, "PHASE 2") + **3 content pages** (§1–§7 + AI disclosure) + references. 11-pt Times New Roman, single-spaced, 0.75" content margins.
- **Sections:** §1 overview/CHIMERA/sub-problem (1-day horizon); §2 architecture + Fig 1; §3 theory led by the measured kernel result + Fig 3; §4 led by regime transitions (MZ result) + Table 1 + Fig 2; §5 data; §6 platform (gate vs analog; verified SDK credential); §7 falsifiable H0 + scaling plan + impact + AI disclosure. **17 references** (data sources included).
- **Was the entire Phase-2 submission just this PDF?** Yes. The reproducible repo / agentic package are **Phase-3 finalist** deliverables (we built them ahead of schedule).

---

## 9. Phase 3 plan (summary — full doc: `3_Phase3_Planning/`)

**Central hypothesis H0:** the measured parameter-efficiency + kernel-distinctness gap becomes a *forecasting-accuracy* gap at scale, where classical simulation fails.
- **Confirm if** (out-of-sample, walk-forward): g keeps growing with qubit count **and** the regime-transition MZ-R² gap over HAR turns positive & significant beyond the ≈28–30-qubit exact-simulation frontier.
- **Refute if** g saturates **or** the gap stays ≤ 0. *(We commit to reporting a negative result.)*

**Three coupled scaling axes:** (A) system size 8→256 qubits, staged around the classical-simulability frontier; (B) **encoding density** — the input-bottleneck fix: extend lags + realized-semivariance/jumps → multivariate sector/index RV panel → **data re-uploading**, so added qubits carry new information; (C) reservoir/measurement budget (τ-bank, Ising↔Heisenberg, shot budget, noise-as-feature).

**Compute:** simulator-first backbone (statevector → tensor-network/MPS → GH200 GPU; **bond dimension tracked as a complexity metric**) carries the science even with zero hardware time. **Two architecture–hardware matches:** **QuEra Aquila** (256 neutral atoms; Rydberg Hamiltonian natively realizes our Ising reservoir with no gate compilation — preferred, reaches classically-hard scale) and **Quantinuum** (56 qubits, native arbitrary-angle ZZ gates ≈ our Trotter primitive, mid-circuit measurement ≈ our RZ feedback). Error mitigation: ZNE (Mitiq) + measurement mitigation (mthree), with a classical cross-check for every hardware run. **Fallback:** TN + density-matrix noise emulation.

**Phased plan:** A) simulator scaling sweep → the decisive H0 test; B) hardware validation at mid-scale (Quantinuum/IonQ); C) classically-hard frontier on QuEra Aquila. Each with a refutation gate.

**Phase-3 deliverables:** longer technical paper; **executable qBraid repository**; **agent-reproducible package** (largely done); a **qBraid "Skill."**

---

## 10. Key decisions & rationale (so they aren't relitigated)

- **Kernel-geometry experiment was the highest-leverage move** — it converts "quantum is different" from assertion to measurement (g ≈ 62 vs 4.3 control). It roughly doubled the realistic win odds.
- **Foreground regime transitions, not calm RMSE** — Track A's mandate is regime-shift forecasting, and that's where the model genuinely wins (MZ 0.591 > HAR).
- **Radical honesty about the ceiling** — explicitly stating "we don't beat HAR on calm point RMSE; advantage is a Phase-3 scaling hypothesis" *builds* credibility rather than costing it.
- **QA fixes applied:** §1 scoped to the **1-day horizon** (matches shown evidence; multi-step is Phase-3 H3); seed variance stated as the true **2–30×**; **Kobayashi & Motome** citation corrected to *"Edge of Many-Body Quantum Chaos in Quantum Reservoir Computing," Phys. Rev. Lett. 136, 040602 (2026)*; Huang et al. 2021 verified.
- **Data referencing fixed:** added Heber et al. (2009) attribution + public access links; framed SPY data as public/free-from-Stooq-Yahoo (Massive = retrieval tool, not gatekeeper).
- **Fares's Table 1 note adopted** (Garman–Klass comparability) with a within-window safeguard.
- **Figure forward-reference left as-is** — standard practice; "fixing" would worsen on-page order or risk pagination.
- **Two clarity edits still optional (not yet applied):** define **HAR** (Heterogeneous AutoRegressive) at first use — the one genuinely undefined headline term; and disambiguate **HLN** (Harvey–Leybourne–Newbold, the DM small-sample correction) from Hansen–Lunde–Nason (the MCS). Both tiny; do on next paper iteration.

---

## 11. Honest assessment

- **Phase-2 paper quality:** ~8.7/10 on a skeptical-panel read. Strongest aspects: the measured kernel mechanism, gold-standard data modeling, honest framing, real regime-transition result. Ceiling-cap: no unconditional advantage over HAR yet (by design, it's the Phase-3 bet).
- **Business value (Christian):** near-term ~zero as a trading product; **real and bankable** as research/IP/methodology and as credibility/capability for Capgemini FS + quantum GTM and QUATTRIVA; long-term = a discounted option on regime-transition forecasting in the $30B+ VIX-options/risk ecosystem.
- **Phase-3 honest prior:** a scaling advantage is *plausible* (the kernel result is the precondition) but not certain; the **multivariate / turbulent / regime-transition** setting is where it's most likely to appear first; calm univariate point-RMSE is where it's least likely.

---

## 12. References (the 17 used in the paper)

Li et al. 2026 (QRC for realized-vol forecasting, arXiv:2505.13933) · Kornjača et al. 2024 (large-scale analog QRC, 2407.02553) · Hou et al. 2026 (experimental QRC in correlated spins, PRL, 2508.12383) · Antoncich et al. 2026 (neutral-atom QRC, noise-as-feature, 2602.14641) · Ahmed, Tennie & Magri 2025 (robust QRC for chaotic dynamics, Proc. R. Soc. A 481, 20250550; 2506.22335) · Čindrak et al. 2026 (memory–nonlinearity trade-off, 2603.21371) · **Kobayashi & Motome 2026** (Edge of Many-Body Quantum Chaos in QRC, *PRL 136, 040602*) · **Huang et al. 2021** (Power of data in QML, *Nat. Commun. 12, 2631*) · Corsi 2009 (HAR-RV) · Patton 2011 (QLIKE/robust vol loss) · Hansen, Lunde & Nason 2011 (Model Confidence Set, Econometrica) · Diebold & Mariano 1995 · Adams & MacKay 2007 (BOCPD, 0710.3742) · Bollerslev 1986 (GARCH) · Jaeger 2001 (ESN, GMD Report 148) · **Heber, Lunde, Shephard & Sheppard 2009** (Oxford-Man Realized Library) · **Massive.com / Polygon.io** (SPY OHLCV, https://massive.com).

---

## 13. Working style (standing instructions)

Never be lazy — always give maximum effort, aim for the most ambitious goal, be resilient and persistent through difficulty or repeated failure. Be rigorous and **honest** (report negatives; never overclaim). This is core to how Christian works toward world-changing innovation. Keep Capgemini and personal/QUATTRIVA work strictly separated.

---

## 14. Immediate next actions (Phase-3, spec-independent — start now)

1. **`scaling_sweep.py`** — parametrize qubit count n, encoding set, τ-bank; emit the two H0 curves: **g(n)** and **MZ-gap-over-HAR(n)**.
2. **Multivariate / data-re-uploading encoder** (Axis B) — extend beyond 8 univariate lags so added qubits carry new information.
3. **MPS / tensor-network backend** (Axis A, 30–80 qubits) with bond dimension logged.
4. **qBraid-SDK submission wrappers** + a QuEra Aquila analog-Hamiltonian mapping smoke-test.
5. **Lock the pre-registered H0 thresholds** into the repo before running (honest bounding).
6. On next paper pass: define **HAR** at first use; disambiguate **HLN**.
7. Finalize the Phase-3 proposal once the official brief is live on Aqora (format, page limits, required sections, assigned hardware, deadline).

---

## 15. Acronym glossary

CHIMERA (Chaotic Hybrid Intelligence via Multi-scale Entangled Reservoir Architecture) · QRC (Quantum Reservoir Computing) · RV (Realized Variance/Volatility) · HAR (Heterogeneous AutoRegressive) · GARCH / GJR-GARCH (Generalized AutoRegressive Conditional Heteroskedasticity / Glosten–Jagannathan–Runkle) · AR (AutoRegressive) · ESN (Echo State Network) · LSTM (Long Short-Term Memory) · RMSE (Root Mean Squared Error) · QLIKE (Quasi-Likelihood loss) · MZ (Mincer–Zarnowitz) · DM (Diebold–Mariano) · HLN (Harvey–Leybourne–Newbold DM correction) · MCS (Model Confidence Set) · KTA (Kernel–Target Alignment) · BOCPD (Bayesian Online Changepoint Detection) · GFC (Global Financial Crisis) · OHLCV (Open/High/Low/Close/Volume) · SPX (S&P 500 index series) · SPY (SPDR S&P 500 ETF) · VIX (Cboe Volatility Index) · MPS (Matrix Product State) · ZNE (Zero-Noise Extrapolation) · GIC (Global Industry Challenge).

---

## 16. Manifest of this package

```
EIGENNEXUS_CHIMERA-QRC_MASTER/
├── README_MASTER.md                        index of the package
├── KNOWLEDGE_TRANSFER.md                   this file
├── TRANSFER_PROMPT.md                      paste into a fresh Claude conversation
├── 1_Phase2_Submission/                    EIGENNEXUS__Phase2_Version1.pdf / .docx  (THE submission)
├── 2_Reproducible_Repo/                    chimera-qrc/ (git repo, run_all.sh) + chimera-qrc.bundle
├── 3_Phase3_Planning/                      CHIMERA-QRC_Phase3_Scaling_and_QC_Access_Plan.md
├── 4_Assets/                               architecture figure (png/svg)
└── 5_Archive_prior_versions/               Phase-1 deliverable + superseded Phase-2 drafts
```
