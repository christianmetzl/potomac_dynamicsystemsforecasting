# CHIMERA-QRC: A Pre-Registered, Adversarially-Controlled Study of Quantum Reservoir Computing for S&P 500 Realized-Volatility Forecasting
### Team EIGENNEXUS — C. Metzl, F. Eldibani, J. M. Aguiar Hualde · Track A (Financial Volatility) · GIC 2026 Phase 3

> *Content for the 5-page Phase-3 write-up (11-pt Times New Roman, single-spaced), to be
> placed after the required GIC_2026 cover page. Every number is produced by a script in this
> repository and reproducible via `python3 cli.py run <action>` (fast path: `--quick`).*

**Abstract.** We contribute a **pre-registered, adversarially-controlled evaluation instrument**
for quantum reservoir computing — reproducible **offline in one command** (`cli.py verify`), with
every hardware prediction bound to a prior commit by a **hash-preimage commitment** — and apply it
to S&P 500 realized-volatility forecasting across **four devices from three QPU vendors** (IonQ,
IQM, Rigetti). Two measurements stand on their own: an empirical **quantum-complexity metric** (the
reservoir's MPS bond dimension is essentially full, **χ_eff ≈ 2^(n/2)**, marking the
classical-simulability boundary) and a cross-platform **coherence-budget wall** (Fig. 3) whose
readout-corrected fingerprint separates **coherent circuit routing from depolarizing/damping
noise**, each bootstrapped regime verdict **9.7–23.9σ** beyond shot noise. Applied honestly, the instrument
returns a **well-characterized negative**: at simulable scale (≤16 qubits) the reservoir is
*distinct but not more accurate* than the strongest fair baselines — **HAR-X**, size-matched
ESN/RFF, under HAC-DM + Holm + MCS (**H0 refuted**) — robust across a second **Heisenberg** reservoir
family (not Ising-specific) and a second (weather) domain, and our program **falsified four of its
own pre-registered predictions** under controls (a same-session cross-seed control shows the n=8
scrambling is *seed-0-instance-specific, not a size law*). **Desk takeaway:** vol-timing a simple RV
forecast ≈halves the 2008 drawdown; quantum adds no economic value at this scale.

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

**This paper's honest thesis.** We pre-registered H0 and *attacked our own result* with fair
controls: the dominant accuracy lever is *which features are encoded*, not quantum nonlinearity.
What survives for the reservoir — kernel distinctness, lower seed variance, full-rank entanglement
(classical-simulation hardness) — is *necessary, not sufficient* for advantage.
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
reproduces it to ≈3.9×10⁻¹⁶ and compiles, at n=8, to **380 native gates** (220 two-qubit + 160
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
n=12). (g is at fixed ridge regularization; the qualitative separation, not the exact value, is the claim.)
At ≤12–16 qubits the map remains classically simulable, so distinctness is **necessary, not sufficient** for accuracy — and §5.3 shows that,
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
**saturate/decline** (n=8→12: g 133→30 at N_sub=800; D_eff 1.8→1.5). **H0 is refuted in this regime**
— the empirical case *for* enriching the encoding.

**5.2 Encoding density (Axis B) — mechanism confirmed.** Feeding the extra qubits genuinely new
realized-measure information (signed return/leverage, downside-semivariance share, jump share)
restores the lost structure: at n=10, informed vs idle qubits, kernel distinctness and rank
jump (**g 52→158, D_eff 1.5→3.1**), and effective rank grows with n (D_eff 1.81→3.14, n=8→12).
So the bottleneck is *fixable* — added qubits can carry new
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
**HAR-X is best or co-best everywhere; CHIMERA never beats it** and is indistinguishable from the
classical ESN/RFF after Holm (one raw loss to RFF at crisis n=8, p=0.049). **After Holm correction no comparison is significant in
either direction, and the 95% MCS retains all four models (n=10)** — a statistical tie. The earlier
"beats HAR" result was an artifact of a *feature-poor* HAR: the gain is the encoded realized
measures (a known SHAR/HARQ effect), not quantum nonlinearity. **By our
pre-registered criteria, H0 is refuted — we report this negative.** What honestly survives for
the quantum reservoir: it is **competitive** (within ≈0.8–2.1% RMSE of the best at every n),
with **lower per-seed dispersion than the recurrent ESN in 3 of 4 cells** (n=12: 0.009 vs 0.015)
and **beats it on the calm window** (raw p=0.018; n.s. after Holm).
A **tuned, size-unconstrained ESN** (45-config search to 800 nodes) confirms the control was not
crippled (0.6020 vs CHIMERA 0.6094, within noise of HAR-X); and **named canonical models** (SHAR,
HAR-CJ, HARQ, HEAVY-RM; MSE + QLIKE DM) — **none beats HAR-X**, with CHIMERA tying best on RMSE and
only a *raw, non-Holm* QLIKE/MZ edge (`cli.py run canonical`, `esn_tuning_robustness_findings.md`).

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
(per-layer single-qubit channels) is **not** removed by standardization (standardized error grows
with rate, vs **≈0** for readout-only depolarizing): the invariance is a *readout* property, not
circuit-level robustness; accumulated gate error is the real NISQ cost (§6).

**5.5 Scaling frontier + quantum-complexity metric.** A sparse-exact backend (`expm_multiply`,
no dense propagator; matches the dense engine to **2.4×10⁻¹⁴**) reaches **n=16 exactly**. For
the random ≈50%-connected reservoir we measure the **bond dimension** χ_eff across a balanced
cut: it is **essentially full at every n, χ_eff ≈ 2^(n/2)** (16→255.9 for n=8→16) — an exact MPS
gets **zero compression** (S ≈ 1.7–3.2 nats): the reservoir admits **no low-bond-dimension
(MPS/TEBD) shortcut**, exact cost stays exponential — the precondition any beyond-frontier
advantage would need, though none appears at the scale we can test. **Capability + efficiency checks.** An
information-processing-capacity probe (Dambre et al. 2012; `cli.py run capacity`) finds the quantum
reservoir **not more** — slightly *less* — nonlinearly expressive than a matched RFF/ESN:
no excess expressivity to exploit. A frontier check (`cli.py run frontier`) adds that
g(n) does **not** widen toward n=16 (it declines; D_eff/rank grow but a matched ESN keeps pace).
**Robustness (supporting study).** *Second family:* a **Heisenberg (XXZ)** reservoir — equally
kernel-distinct (g≈55) — also fails to beat HAR-X (0.650 vs 0.642, 8 seeds, full-sample config), so
the negative is **not Ising-specific** (`cli.py run second_family`). *Efficiency:* with input held fixed, a *smaller*
QRC cannot substitute for a *larger* classical reservoir — quantum accuracy **saturates** while the
classical curves improve; per feature the static maps are comparable, so the negative is
**saturation, not per-feature inferiority** (weather RMSE °C: CHIMERA 0.85 at its qubit-range
ceiling vs RFF 0.78 / recurrent ESN 0.71 at larger budgets). *Domain/architecture:* the *same* engine/protocol on chaotic **weather** (5 stations) and the
autonomous **VPT** metric still show no advantage; the **recurrent** QRC is competitive-not-better
— unitary evolution is non-dissipative, lacking the contraction behind ESN "generalized
synchronization" (Ahmed–Tennie–Magri 2025). We then **fixed the mechanism**: engineered
memory-qubit damping traces the pre-registered inverted-U, lifting autonomous VPT ≈+60% to
**parity** with the matched ESN — not better (`results/dissipative_qrc_findings.md`).

## 6. Quantum platform and resource planning
Simulator-first on qBraid: statevector ≤12 qubits, sparse/TN to ≈16, GPU beyond.
**Resource estimates** (gate-Trotter, 20 layers): n=8/10/12 use **220/480/760 two-qubit +
160/200/240 one-qubit** gates, yielding **36/55/78 observables** — all Z-basis-diagonal, so **one
S-shot set (S≈2–8k, ε≈1/√S) reads every observable** (statevector build ≤~1 min over this range).


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
Execution also surfaced a **platform-level finding**: negative-angle rotations are **silently lost
server-side on the IonQ route** (RY(π)RY(−π) → net RY(π)), corrupting ZNE's negated folds; we
hardened the emitter (mod-2π) and validated the diagonal calibration on-device. The routing-free **IonQ Forte-1 campaign** then ran under the pre-committed manifest: a
smoke gate measured a **2,000-gate/circuit ceiling** on the native route, so per abort rule it ran
scale-1-only (500 shots — a disclosed, cost-forced deviation, s.e.≈0.004).
**Raw 0.104 — below the 0.196 depolarized limit** and every superconducting n=8 number: a
**signal-bearing hardware execution** of this reservoir (**prediction (ii) confirmed**;
`results/qpu_hardware_findings.md`). A pre-registered **hardware scaling program**
(`results/qpu_scaling_outlook.md`) then refuted our own statements on metal (Fig. 3): Garnet turns **signal-bearing at n=10/n=12** while
the **same-session seed-0 n=8 anchor** stays scrambled — but a pre-registered cross-seed
control (**S7**) found an **independent seed-1 n=8 instance signal-bearing** in the same session,
so the n=8 scrambling is **specific to the seed-0 instance, not a size law** (seed-1 n=10 also signal-bearing) — and the newer-generation **Emerald is
signal-bearing at the very size Garnet scrambles**, reproduced in a **same-window two-chip
pair**: generation-dependent at fixed size, temporally controlled. The program characterizes
reservoir size, encoding density, shot budget and noise, with
in one view (raw mean feature error vs size-matched fully-depolarized limit; 4k shots, IonQ 500):

![**Figure 3.** Cross-platform coherence-budget wall: mean raw feature error vs the **instance-matched** depolarized limit mean|F_exact| (black ticks; 4k shots, IonQ 500). Five configs are signal-bearing (below the limit), two scrambled (Garnet n=8 seed-0 0.228; Rigetti 0.223). The adjacent Garnet n=8 seed-1 (0.159) vs seed-0 (0.228) pair — same chip and session — refutes a *size* law. Seed-0 limits 0.196/0.179/0.214 at n=8/10/12; seed-1 carries its own 0.1806 — verdict unchanged (§6).](figures/fig_coherence_wall.png)

**Execution provenance (externally verifiable).** Every campaign ran against pre-committed
predictions — the ten funded ones under a committed manifest (abort/decision
rules fixed *before* each launch); every funded-campaign job embeds the repo commit hash and campaign tag
in qBraid's timestamped records — a hash-preimage commitment that predictions predate data —
and billing matched estimates to the half-credit (`results/CREDIT_BUDGET.md`: ≈64k credits).
Bootstrap from the committed counts re-derives every
number above and puts **each of the nine bootstrapped regime claims 9.7–23.9σ beyond shot noise**; a readout-corrected
fingerprint attributes the scrambled regime to predominantly coherent error
(`qpu_bootstrap`, `qpu_fingerprint`). Controls were bought where needed: a Rigetti
replication (day-drift), a same-session n=8 anchor (drift), a same-window
two-chip pair (generation). S5–S6 pre-committed; S7 executed (above).

## 7. Limitations (stated plainly)
(i) **No quantum advantage** is demonstrated at the ≤16-qubit simulable scale; HAR-X (classical,
linear) is the best model on this task. (ii) The RV sample ends Feb-2020 (COVID just outside); broader assets/periods are daily-proxy
supporting studies (v2_research — same negative), not 5-min RV.
(iii) Task-level noise: per-layer channels (§5.4) and shot noise; combined noisy-plus-shot execution is measured in the QPU campaigns (§6).
(iv) g is regularization- and configuration-dependent (qualitative gap only).
(v) Superconducting n=8 execution is a **characterized negative** (Fig. 3; day-scale drift
exceeds shot noise, so *regime* — not point value — is the robust claim), while n=10/n=12 and the
newer generation land inside their limits: the wall is instance- and generation-dependent, not
absolute (n=8 scrambling is seed-0-instance-specific — S7; and in a 30-instance ensemble the
scrambled instance is among the *sparsest*, so gate count **anti-predicts** the wall — §8). Mitigation recovery on hardware is at
best marginal (ZNE 0.223→0.217 on Rigetti; the ion chain is flat).
(vi) Distinctness and full-rank entanglement are *necessary, not sufficient*; whether they convert beyond the simulable frontier is open. A quantum-data probe shows the QRC natively reads
nonlinear *state* functionals a linear readout cannot, but the proper baseline — **classical shadows**
(Huang–Kueng–Preskill 2020) at matched budgets — **wins wherever real information is extracted**,
including the shadows-hard Tr(ρ³): closed negatively at simulable scale (`shadows_hard_findings.md`).

## 8. Stakeholder impact, milestone plan, AI disclosure
**The durable asset is the audit instrument** — and our data shows it is *necessary*. Coupling density
buys expressivity (→entanglement r=+0.65, p<0.001) while raising gate cost **and tightening** the bar
(→limit r=−0.40, p=0.03); yet that prior **mis-ranks the two instances we measured** — denser,
tighter-bar seed-1 was signal-bearing, sparser seed-0 scrambled (`instance_ensemble_findings.md`).
Structure gives a tendency; measurement gives the answer. Hence **trust in a quantum yes/no**: a pre-registered,
vendor-neutral **workload→QPU qualification** earned by an instrument that **falsifies its own
predictions** — it split our runs **five signal-bearing, two scrambled** (Fig. 3) at ≈$70–$205 per
campaign. Target profiles only; no customers or LOIs claimed. **Desk impact** (`cli.py run economics`): vol-timing the GFC window **halves max drawdown
(−61%→−32%)** and lifts Sharpe **0.00→0.14** net of costs — risk control, not alpha — but **plain HAR**
captures it (CE fee −25bp/yr): the lever is **a simple RV forecast, not quantum hardware**.
**Milestone plan:** (i)–(vi) ✓ (§6). **AI disclosure:** Claude (Anthropic) assisted with code and drafting; all decisions and results are the team's own.

<!-- pagebreak -->

## References
Kornjača et al. 2024 · Zhu et al. 2025 · Ahmed, Tennie & Magri 2025 · Li et al. 2025 ·
Tandon et al. 2025 · Hou et al. 2025 · Čindrak et al. 2026 · Antoncich et al. 2026 ·
Kobayashi & Motome 2026 · Huang et al. 2021 · Huang, Kueng & Preskill 2020 (classical shadows) ·
Dambre et al. 2012 · Corsi 2009 · Patton 2011 · Hansen et al. 2011 · Harvey et al. 1997 ·
Diebold & Mariano 1995 · Bollerslev 1986 · Jaeger 2001 · Heber et al. 2009.
