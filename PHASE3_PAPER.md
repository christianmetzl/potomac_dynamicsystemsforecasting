# CHIMERA-QRC: A Pre-Registered, Adversarially-Controlled Study of Quantum Reservoir Computing for S&P 500 Realized-Volatility Forecasting
### Team EIGENNEXUS — C. Metzl, F. Eldibani, J. M. Aguiar Hualde · Track A (Financial Volatility) · GIC 2026 Phase 3

> *Content for the 5-page Phase-3 write-up (11-pt Times New Roman, single-spaced), to be
> placed after the required GIC_2026 cover page. Every number is produced by a script in this
> repository and reproducible via `python3 cli.py run <action>` (fast path: `--quick`).*

## 1. Focus, track selection, and problem framing
We target **Track A: financial volatility** — one-step-ahead forecasting of S&P 500 **realized
variance (RV)** and the tracking of volatility **regime transitions**, the domain where
JonesTrading's risk, allocation and derivatives pricing live. RV is long-memory, multi-scale,
regime-switching and non-Gaussian — the structure reservoir computing exploits. Our central
yardsticks are the Echo State Network (ESN, the classical analog of QRC) and the strongest
econometric models (HAR — *Heterogeneous AutoRegressive*, Corsi 2009 — and, critically for
Phase 3, **HAR-X**: HAR augmented with the same realized-measure features we feed the quantum
reservoir). We also report GARCH/GJR-GARCH, AR(3), persistence, LSTM, and an RFF/RBF kernel,
and we implement the challenge's common **MNIST** benchmark on the identical engine.

**This paper's honest thesis.** We pre-registered a falsifiable advantage hypothesis (H0) and
then *attacked our own result* with the strongest fair controls. The finding is a **carefully
bounded negative**: at simulable scale (≤16 qubits) the quantum reservoir shows **no
statistically significant forecasting advantage** over strong classical baselines once they
are given the same information; the dominant lever is *which features are encoded*, not the
reservoir's quantum nonlinearity. We report what *does* survive — measurable kernel
distinctness, lower seed variance, and full-rank entanglement (classical-simulation hardness) —
as quantum-specific *properties* that are necessary, not sufficient, for advantage.
**Vs. prior work.** The closest study (Li et al. 2025/26 — QRC for realized volatility) presents
the approach as a competitive, noise-resilient *proof-of-concept*; we add the control-hardened,
pre-registered evaluation it omits — the decisive **HAR-X** control, HAC-DM/Holm/MCS, and explicit
capability and per-layer-noise audits — turning an encouraging proof-of-concept into a falsifiable
result.

## 2. QRC architecture (Fig. 1)
CHIMERA is a delay-embedding quantum reservoir. Inputs are angle-encoded `RY(π·x)`, one value
per qubit, onto `|0…0⟩`; the state evolves under a fixed transverse-field **Ising** Hamiltonian
`H = Σ_{i<j} J_ij Z_iZ_j + h_x Σ_i X_i` (`h_x=1`; `J` a **random ≈50%-connected** graph,
`connectivity=0.5`; `U=exp(−iHτ)`, `τ=2`); single- and pairwise Pauli-Z expectations
`⟨Z_i⟩,⟨Z_iZ_j⟩` form the feature vector. A **ridge head consumes these features concatenated
with a linear block of the same inputs (incl. HAR)**, so any reservoir gain is genuine
nonlinearity *beyond* the linear span of identical information. The identical inputs feed the
classical controls, isolating quantum-vs-classical. Four mechanisms extend the core (multi-scale
τ-bank; RZ measurement feedback; regime-adaptive Ising↔Heisenberg via BOCPD; dissipation-as-
feature); Phase 3 adds an **encoding-density / data-re-uploading path** (§5.2) and a
**sparse/tensor backend** (§5.5). The engine is pure NumPy; an explicit PennyLane circuit
reproduces it to 3.9×10⁻¹⁶ and compiles, at n=8, to **380 native gates** (220 two-qubit + 160
one-qubit, 20 Trotter layers) — consistent with the ≈50%-connected graph.

![**Figure 1.** CHIMERA-QRC pipeline: lagged log-RV (and, in Axis B, realized-measure) inputs are angle-encoded onto qubits, evolved under a fixed random-coupled Ising Hamiltonian, and read out as single/pairwise Pauli-Z expectations into a ridge head fused with a linear block of the same inputs; a BOCPD detector selects the Hamiltonian for regime adaptivity.](figures/fig_architecture.png)

## 3. Theoretical and analytical justification
The exploited quantum resources map to RV's structure: (a) **Hilbert-space dimensionality** —
n qubits give 2ⁿ amplitudes and O(n²) measured Pauli features at O(n²) parameter cost;
(b) **intrinsic nonlinearity** from fixed unitary evolution (no gradient training, no barren
plateaus); (c) **delay-embedded memory** (the headline model's memory is its explicit lag
window, not reservoir recurrence — a recurrent variant is probed in `v3_research`);
(d) **Hamiltonian as inductive bias**.
The central, falsifiable mechanism is **expressivity scaling**, which we measure directly via
the geometric difference (Huang et al. 2021). The quantum kernel is poorly reproducible by a
matched classical reservoir: against the name-matched ESN-108 reference,
**g(ESN→CHIMERA) ≈ 64 vs ≈3.7 control** (`cli.py run kernel`); against per-n *feature-matched*
ESNs the gap is larger but **non-monotonic** (g ≈125 at n=8, peaking ≈158 at n=10, falling ≈88 at
n=12). (g is at fixed ridge regularization; the qualitative ~15–40× separation, not the exact
value, is the claim.)
Crucially, at ≤12–16 qubits the map remains classically
simulable, so distinctness is **necessary, not sufficient** for accuracy — and §5.3 shows that,
here, it is indeed *not* sufficient.

## 4. Data modeling strategy
**Datasets (all bundled in-repo).** Oxford-Man `.SPX` 5-minute realized variance, 2000–2020, 5,029
supervised days incl. the 2008 GFC (Heber et al. 2009; via R packages `highfrequency`/`bvhar`);
SPY daily OHLCV 2022–2026 (Garman–Klass proxy; retrieved via Massive.com API, bundled); real
MNIST (Keras `.npz` mirror).
**Preprocessing:** log-RV target; features min-max scaled to [0,1] on **train only**; per-model
ridge penalty selected on a chronological validation tail; multi-seed ensembling. We verified
the pipeline is leakage-free (all features lagged ≥1 day; train-only scaling). **Baselines:**
HAR, **HAR-X**, GARCH(1,1), GJR-GARCH, AR(3), persistence, ESN (matched + 4×, recurrent), RFF
kernel, LSTM. **Metrics:** RMSE(log-RV), QLIKE (Patton 2011), Mincer–Zarnowitz R²; significance
by **Diebold–Mariano with a Newey–West HAC variance** (HLN-corrected), **Holm**-adjusted across
the comparison family, and the Model Confidence Set (Hansen–Lunde–Nason 2011).

## 5. Phase-3 execution — concrete results
**Pre-registration (honesty).** Before running, we fixed the confirm/refute thresholds in
`preregistration.py` (H0/H1/H4, from our Phase-2 §7). All outcomes — including negatives — are
reported against them. Full numbers/wall-clock: `results/*_findings.md`.

**5.1 The input-bottleneck mechanism (pre-registered negative).** With a *fixed* univariate
8-lag encoder, extra qubits receive no new input: g(n) and effective feature-rank
**saturate/decline** (n=8→12: g 133→30 at N_sub=800; the quick-mode rerun reproduces the same
monotone decline at lower magnitude, cf. §7(iv); D_eff 1.8→1.5). **H0 is refuted in this regime**
— the empirical case *for* enriching the encoding.

**5.2 Encoding density (Axis B) — mechanism confirmed.** Feeding the extra qubits genuinely new
realized-measure information (signed return/leverage, downside-semivariance share, jump share)
restores the lost structure: at n=10, informed vs idle qubits, kernel distinctness and rank
jump (**g 52→158, D_eff 1.5→3.1**), and effective rank grows with n (D_eff 1.81→3.10→3.14,
n=8→12; near-flat 10→12). So the bottleneck is *fixable* — added qubits can carry new
information. The decisive question is whether this converts into forecasting **accuracy**.

**5.3 The decisive, adversarially-controlled test (the honest headline).** We compare CHIMERA
to the strongest fair baselines — **HAR-X** (the same rich features used *linearly*, no
reservoir), a **true recurrent ESN**, and an **RFF kernel** — all sharing the identical
information set and *nesting* HAR-X, so a quantum win requires nonlinearity beyond the linear
span. With **8 seeds, HAC-DM, two windows, and Holm correction** (`cli.py run axisB_rig`):

| RMSE(log-RV) | HAR-X | recurrent ESN | RFF | CHIMERA | best |
|---|---|---|---|---|---|
| crisis n=8 | **0.6255** | 0.6386 | 0.6302 | 0.6379 | HAR-X |
| crisis n=10 | 0.6034 | **0.5996** | 0.6047 | 0.6074 | ESN |
| crisis n=12 | **0.5906** | 0.6023 | 0.5964 | 0.6031 | HAR-X |
| calm n=10 | **0.6244** | 0.6445 | 0.6264 | 0.6291 | HAR-X |

*(plain HAR for reference: crisis 0.6290, calm 0.6454 — HAR-X's rich features cut RMSE sharply.)*
**HAR-X is best or co-best everywhere; CHIMERA never beats it** (slightly worse; raw-significant
at n=8/12) and is indistinguishable from the classical ESN/RFF after Holm (one raw-significant
loss to RFF at crisis n=8, p=0.049). **After Holm correction no comparison is significant in
either direction, and the 95% Model Confidence Set retains all four models in both windows
(n=10)** — a statistical tie. The earlier "beats HAR" result
was an artifact of comparing against a *feature-poor* HAR: the gain comes from the encoded
realized measures (a known SHAR/HARQ effect), not from quantum nonlinearity. **By our
pre-registered criteria, H0 is refuted — we report this negative.** What honestly survives for
the quantum reservoir: it is **competitive** (within ≈0.8–2.1% RMSE of the best at every n),
with **lower per-seed dispersion than the recurrent ESN in 3 of 4 cells** (s.d., e.g. n=12: 0.009
vs 0.015), and it **beats the recurrent ESN on the calm window** (raw p=0.018; n.s. after Holm).
A **tuned, size-unconstrained ESN** (45-config validation-tail search, to 800 nodes) confirms the
control was not crippled: tuned ESN 0.6020 vs CHIMERA 0.6094, within noise of HAR-X
(`results/esn_tuning_robustness_findings.md`) — tuning the classical side only firms the negative.
**Named canonical baselines** (`cli.py run canonical`): **SHAR, HAR-CJ, HARQ** (RQ≈RV² proxy) and
**HEAVY-RM**, under MSE- *and* QLIKE-loss DM — **none beats HAR-X** (a fair, strong stand-in, not a
strawman), and CHIMERA ties the best on RMSE with only a *raw, non-Holm* QLIKE/MZ edge
(`results/canonical_baselines_findings.md`).

![**Figure 2.** Rigorous Axis-B (8 seeds, crisis window). HAR-X (rich features, linear) is the best or co-best model at every n; the quantum reservoir is competitive but shows no advantage that survives HAC-DM + Holm correction. Left: RMSE(log-RV). Right: Mincer–Zarnowitz R².](figures/fig_axisB_rigorous.png)

**5.4 Common MNIST benchmark + noise.** Same engine, pixels→PCA(n)→n qubits→Pauli readout→ridge.
Accuracy **scales with qubits** (n=5/8/10/12: 0.632/0.798/0.831/0.859, 3 seeds; **n=15
sparse-exact continues the trend**, 0.878 vs 0.852 for a paired n=12 on a matched subset —
closing the brief's 5/10/15 example) and **beats the linear-PCA baseline at every n** (real
nonlinear lift), confirming **sufficient expressivity**; a matched ESN **ties or slightly
exceeds** CHIMERA (within ≈1% for n≥8; 2.9% at n=5) — competitive, not dominant. **Noise:** the classifier is **invariant to
depolarizing** noise (a uniform Bloch contraction that per-feature standardization removes exactly;
accuracy identical across rates 0.05–0.30) and **robust to amplitude damping** (<0.5% at 30%). **Honesty check (`cli.py run noise_circuit`):** a
per-Trotter-layer density-matrix study shows the *converse* — noise interleaved with the evolution
(per-layer single-qubit channels, a proxy for the ≈220 two-qubit gates' accumulated error) is
**not** removed by standardization (standardized error grows with rate, vs **≈0** for readout-only
depolarizing): the invariance above is a *readout* property, not a circuit-level robustness claim;
accumulated gate error over the 380-gate circuit — dominated on hardware by two-qubit gates — is
the real NISQ cost (§6).

**5.5 Scaling frontier + quantum-complexity metric.** A sparse-exact backend (`expm_multiply`,
no dense propagator; matches the dense engine to **2.4×10⁻¹⁴**) reaches **n=16 exactly**. For
the random ≈50%-connected reservoir we measure the **bond dimension** χ_eff across a balanced
cut: it is **essentially full at every n, χ_eff ≈ 2^(n/2)** (16→255.9 for n=8→16) — an exact MPS
gets **zero compression** — with entanglement entropy S ≈ 1.7–3.2 nats. The reservoir therefore admits
**no low-bond-dimension (MPS/TEBD) shortcut** —
exact cost stays exponential (full entanglement is *necessary, not sufficient* for true classical
hardness) — the precondition any beyond-frontier advantage would need, even though no advantage
appears at the simulable scale we can test. **Capability + efficiency checks.** An
information-processing-capacity probe (Dambre et al. 2012; `cli.py run capacity`) finds the quantum
reservoir **not more** — slightly *less* — nonlinearly expressive than a matched RFF/ESN:
no excess expressivity to exploit. A frontier check (`cli.py run frontier`) adds that
g(n) does **not** widen toward n=16 (it declines; D_eff/rank grow but a matched ESN keeps pace).
**Robustness (supporting study, `v3_research/`).** *Efficiency:* with input held fixed, a *smaller*
QRC cannot substitute for a *larger* classical reservoir — quantum accuracy **saturates** while the
classical curves improve; per feature the static maps are comparable, so the negative is
**saturation, not per-feature inferiority** (weather °C; CHIMERA at its qubit-range ceiling, classical
at their larger-budget plateaus):

| reservoir | CHIMERA (≤55 feat) | RFF (static) | ESN (recurrent) |
|---|---|---|---|
| RMSE (°C) | 0.85 | 0.78 | 0.71 |

*Domain/architecture:* the *same* engine/protocol on chaotic **weather** (5 stations, +0–78%
unpredictability) and the autonomous **VPT** metric still show no advantage; the **recurrent** QRC is
competitive-not-better — unitary evolution is non-dissipative, lacking the contraction behind ESN
"generalized synchronization" (Ahmed–Tennie–Magri 2025). We then **demonstrated the mechanism by
fixing it**: engineered memory-qubit damping shows the pre-registered inverted-U in the damping
rate and lifts autonomous VPT ≈+60% (replicated on fresh starts), raising the recurrent QRC from
clearly-behind to **statistical parity** with the size-matched ESN — not better
(`results/dissipative_qrc_findings.md`).

## 6. Quantum platform and resource planning
Simulator-first on qBraid: statevector ≤12 qubits, sparse/TN to ≈16, GPU beyond.
**Resource estimates** (gate-Trotter, 20 layers; readout is single-basis — all `⟨Z_i⟩,⟨Z_iZ_j⟩`
are computational-basis-diagonal, so one S-shot set yields **all** n+C(n,2) observables):

| n | two-qubit gates | one-qubit gates | observables | shots S (ε≈1/√S) | sim wall-clock |
|---|---|---|---|---|---|
| 8 | 220 | 160 | 36 | 2k–8k (ε≈.011–.022) | <1 s/state |
| 10 | 480 | 200 | 55 | 2k–8k | ~sec |
| 12 | 760 | 240 | 78 | 2k–8k | ~1 min build |


**QPU validation** uses this gate-Trotter circuit on **IonQ / IQM / Rigetti** via qBraid — the
random-sparse Ising needs *fewer* two-qubit gates than an all-to-all reservoir, easing NISQ
mapping — with **ZNE + measurement mitigation** and a classical cross-check per run. The submission path is
**executable now** (`cli.py run qsubmit`): on a simulator it (i) reproduces
the engine to **3.9×10⁻¹⁶** (the per-run classical cross-check),
(ii) characterizes the **shot budget** (ε≈1/√S; feature error
0.046→0.0066 at S=256→16k; gate-Trotter(20) adds ≈0.04), and (iii) demonstrates **zero-noise
extrapolation** under a depolarizing sweep. **Executed on real hardware:** the full mitigated
protocol ran first on **Rigetti Cepheus-1-108q** (12 logged cloud jobs; bit order
auto-detected; readout 2.3%/6.4%): after lattice routing, scale-1 already exceeds the
coherence budget — the accumulated two-qubit-gate cost §5.4 predicts, measured on metal
(ZNE marginal; a 4k-shot replication showed the beyond-limit regime stable under day-scale
drift). The pre-registered **Garnet protocol** replicated the regime on a second vendor
(raw 0.230 > our routing-free 0.171 forecast — **prediction (iii) confirmed**).
Cross-platform execution also surfaced a **platform-level finding**: negative-angle rotations
are **silently lost server-side on the IonQ route** (an RY(π)RY(−π) identity pair executed as
net RY(π); the client-side JSON provably contained both) — corrupting ZNE's negated fold
gates. We hardened the emitter (angles mod 2π; diagonal-only calibrations) and validated
on-device: P(|0⁸⟩)=0.996 vs 0.0 pre-fix. The decisive routing-free **IonQ Forte-1 campaign
then executed** under the pre-committed manifest: a smoke gate measured a **2,000-gate/circuit
device ceiling** on both access routes, so per abort rule it ran scale-1-only (500 shots,
readout 0.08%/0.65%). **Raw 0.104 — below the 0.196 depolarized limit** and every
superconducting n=8 number: the **first signal-bearing hardware execution** of this reservoir
(**prediction (ii) confirmed**, under our 0.149 forecast) — one pre-registered circuit
measuring the coherence wall from both sides (`results/qpu_hardware_findings.md`). A
pre-registered **hardware scaling program** (`results/qpu_scaling_outlook.md`) then refuted
our own statements on metal (table below): Garnet turns **signal-bearing at n=10/n=12** while
a **same-session n=8 anchor** stays scrambled — the size effect is **real and
drift-controlled** by the manifest's pre-committed decision rule (mechanism honestly open:
instance structure vs lattice embedding) — and the newer-generation **Emerald is
signal-bearing at the very size Garnet scrambles**, reproduced in a **same-window two-chip
pair**: generation-dependent at fixed size, temporally controlled. We thus characterize all
four challenge axes — reservoir size, encoding density, shot budget, noise — with the program
in one view (raw mean feature error vs size-matched fully-depolarized limit; 4k shots, IonQ 500):

| device | technology | n | raw error | limit | regime |
| --- | --- | --- | --- | --- | --- |
| IonQ Forte-1 | trapped-ion | 8 | **0.104** | 0.196 | **signal-bearing** (prediction (ii) ✓) |
| IQM Emerald | supercond., newer gen | 8 | **0.169–0.179** | 0.196 | **signal-bearing** (S3b refuted high; same-window pair) |
| IQM Garnet | superconducting | 10 / 12 | **0.159 / 0.190** | 0.179 / 0.214 | **signal-bearing** (S1/S2 refuted; anchor-controlled) |
| IQM Garnet | superconducting | 8 | 0.222–0.231 (3 days) | 0.196 | scrambled — the stable control |
| Rigetti Cepheus-1 | superconducting | 8 | 0.223–0.261 (2 days) | 0.196 | scrambled (drift band measured) |

**Execution provenance (externally verifiable).** All ten campaigns were pre-registered in a
committed manifest (budgets, abort and decision rules amended *before* each launch); every job
embeds the repo commit hash and campaign tag in qBraid's timestamped records — a hash-preimage
commitment that predictions predate data — and per-job billing matched estimates to the
half-credit (`results/CREDIT_BUDGET.md`: ≈64k credits; every rejected submission billed 0).
Controls were bought exactly where claims needed them: a Rigetti replication (day-drift band),
a same-session n=8 anchor (drift excluded from the size effect), a same-window two-chip pair
(generation effect temporally controlled). The S5/S6 outlook (hardware-in-the-loop
forecasting; hardware-native dissipation) is pre-committed the same way.

## 7. Limitations (stated plainly)
(i) **No quantum advantage** is demonstrated at the ≤16-qubit simulable scale; HAR-X (classical,
linear) is the best model on this task. (ii) The RV sample ends Feb-2020 (2008 in-sample,
COVID just outside); broader assets/periods are daily-proxy supporting studies
(v2_research — same negative), not 5-min RV.
(iii) Task-level noise: per-layer single-qubit channels (density-matrix, §5.4) and simulator
shot noise; combined noisy-plus-shot execution is measured in the QPU campaigns (§6).
(iv) g is regularization- and run-configuration-dependent (qualitative gap only).
(v) Superconducting n=8 execution is a **characterized negative** (§6 table; measured
day-scale drift exceeds shot noise, so *regime* — not point value — is the robust claim),
while n=10/n=12 and the newer generation land inside their limits: the wall is size/instance-
and generation-dependent, not absolute, mechanism unresolved. Mitigation *recovery* on
hardware is at best marginal (ZNE 0.223→0.217 on the Rigetti replicate; the ion chain is flat
— readout 0.08%/0.65% leaves nothing to correct, the gate ceiling forbids ZNE).
(vi) Distinctness and full-rank entanglement are *necessary, not sufficient* — whether they
convert beyond the simulable frontier is open. A quantum-data probe shows the QRC natively
reads nonlinear *state* functionals (purity, entanglement) a linear readout cannot — but the
proper baseline, **classical shadows** (Huang–Kueng–Preskill 2020), run head-to-head at
matched per-state budgets with an ensemble-prior guard, **wins wherever real information is
extracted**, including the shadows-hard Tr(ρ³): **closed negatively at simulable scale**;
hardware-native many-qubit inputs remain the one untested regime
(`results/shadows_hard_findings.md`).

## 8. Stakeholder impact, milestone plan, AI disclosure
Volatility forecasts feed hedging, risk limits and derivatives pricing — and we make the
impact **concrete** (`cli.py run economics`): a vol-timing backtest sizing S&P-500 exposure by
the one-step RV forecast **nearly halves the 2008 max drawdown (−61%→−32%)** — but a **plain
HAR** captures it; the quantum reservoir adds **no** economic value (negative CE fees). The
decision-useful lever is **vol-timing on a simple RV forecast, not quantum hardware**. **Milestone plan:** (i)–(v) — pre-registration, scaling/encoding sweeps,
the adversarial HAR-X/ESN/RFF test, MNIST + noise, sparse/TN frontier — all ✓; (vi) QPU
validation **executed on three vendors** (§6). **AI disclosure:** Claude (Anthropic) assisted
with code and drafting under the team's direction; all decisions and results are the team's own.

<!-- pagebreak -->

## References
Kornjača et al. 2024 · Zhu et al. 2025 · Ahmed, Tennie & Magri 2025 · Li et al. 2025 ·
Tandon et al. 2025 · Hou et al. 2025 · Čindrak et al. 2026 · Antoncich et al. 2026 ·
Kobayashi & Motome 2026 · Huang et al. 2021 · Huang, Kueng & Preskill 2020 (classical shadows) ·
Dambre et al. 2012 · Corsi 2009 · Patton 2011 · Hansen et al. 2011 · Harvey et al. 1997 ·
Diebold & Mariano 1995 · Bollerslev 1986 · Jaeger 2001 · Heber et al. 2009.
