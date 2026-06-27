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
reproduces it to ≈5×10⁻¹⁶ and compiles, at n=8, to **380 native gates** (220 two-qubit + 160
one-qubit, 20 Trotter layers) — consistent with the ≈50%-connected graph (an all-to-all
reservoir would need ≈720).

![**Figure 1.** CHIMERA-QRC pipeline: lagged log-RV (and, in Axis B, realized-measure) inputs are angle-encoded onto qubits, evolved under a fixed random-coupled Ising Hamiltonian, and read out as single/pairwise Pauli-Z expectations into a ridge head fused with a linear block of the same inputs; a BOCPD detector selects the Hamiltonian for regime adaptivity.](figures/fig_architecture.png)

## 3. Theoretical and analytical justification
The exploited quantum resources map to RV's structure: (a) **Hilbert-space dimensionality** —
n qubits give 2ⁿ amplitudes and O(n²) measured Pauli features at O(n²) parameter cost;
(b) **intrinsic nonlinearity** from fixed unitary evolution (no gradient training, no barren
plateaus); (c) **fading memory** (echo-state property); (d) **Hamiltonian as inductive bias**.
The central, falsifiable mechanism is **expressivity scaling**, which we measure directly via
the geometric difference (Huang et al. 2021). The quantum kernel is poorly reproducible by a
matched classical reservoir: against the name-matched ESN-108 reference,
**g(ESN→CHIMERA) ≈ 62 vs ≈4 control** (`cli.py run kernel`); against per-n *feature-matched*
ESNs the gap is larger still (g ≈ 125 at n=8, rising to ≈158 at n=10). (g is reported at a fixed ridge
regularization; the qualitative ~15–40× separation over the classical–classical control, not
the exact value, is the claim.) Crucially, at ≤12–16 qubits the map remains classically
simulable, so distinctness is **necessary, not sufficient** for accuracy — and §5.3 shows that,
here, it is indeed *not* sufficient.

## 4. Data modeling strategy
**Datasets (all public).** Oxford-Man `.SPX` 5-minute realized variance, 2000–2020, 5,029
supervised days incl. the 2008 GFC (Heber et al. 2009; via R packages `highfrequency`/`bvhar`);
public SPY daily OHLCV 2022–2026 (Garman–Klass proxy); real MNIST (Keras `.npz` mirror).
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
**saturate/decline** (n=8→12: g 133→30, D_eff 1.8→1.5). **H0 is refuted in this regime** — the
empirical case *for* enriching the encoding.

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
at n=8/12) and is statistically indistinguishable from the classical ESN/RFF. **After Holm
correction no comparison is significant in either direction.** The earlier "beats HAR" result
was an artifact of comparing against a *feature-poor* HAR: the gain comes from the encoded
realized measures (a known SHAR/HARQ effect), not from quantum nonlinearity. **By our
pre-registered criteria, H0 is refuted — we report this negative.** What honestly survives for
the quantum reservoir: it is **competitive** (within ~0.5–1.5% RMSE of the best at every n),
**more stable than the recurrent ESN** (lower per-seed variance, e.g. n=12: 0.009 vs 0.015),
and it **beats the recurrent ESN on the calm window** (raw p=0.018; n.s. after Holm).

![**Figure 2.** Rigorous Axis-B (8 seeds, crisis window). HAR-X (rich features, linear) is the best or co-best model at every n; the quantum reservoir is competitive but shows no advantage that survives HAC-DM + Holm correction. Left: RMSE(log-RV). Right: Mincer–Zarnowitz R².](figures/fig_axisB_rigorous.png)

**5.4 Common MNIST benchmark + noise.** Same engine, pixels→PCA(n)→n qubits→Pauli readout→ridge.
Accuracy **scales with qubits** (n=5/8/10/12: 0.632/0.798/0.831/0.859, 3 seeds) and **beats the
linear-PCA baseline at every n** (real nonlinear lift), confirming **sufficient expressivity**
(the benchmark's purpose); a matched ESN **ties or slightly exceeds** CHIMERA (within ≈1% for
n≥8; 2.9% at n=5) — competitive, not dominant. **Noise:** the classifier is **invariant to
depolarizing** noise — provably, because depolarizing is a uniform Bloch contraction that
per-feature standardization removes exactly (accuracy identical across rates 0.05–0.30) — and
**robust to amplitude damping** (<0.5% at 30%). (Studied on MNIST for cross-team comparability;
shot noise and two-qubit gate error are addressed in the QPU plan, §6.)

**5.5 Scaling frontier + quantum-complexity metric.** A sparse-exact backend (`expm_multiply`,
no dense propagator; matches the dense engine to **2.4×10⁻¹⁴**) reaches **n=16 exactly**. For
the random ≈50%-connected reservoir we measure the **bond dimension** χ_eff across a balanced
cut: it is **full at every n, χ_eff = 2^(n/2)** (16→256 for n=8→16) — an exact MPS gets **zero
compression** — with entanglement entropy S ≈ 1.7–3.2 nats (peaking near n=14; S is noisier
than the rank). The reservoir is therefore **genuinely hard to simulate classically** — the
precondition any beyond-frontier advantage would need, even though no advantage appears at the
simulable scale we can test.

## 6. Quantum platform and resource planning
Simulator-first on qBraid: dense statevector ≤12 qubits, sparse/tensor-network to ≈16, GPU for
larger. **Resource estimates** (gate-Trotter, 20 layers; readout is single-basis because all
`⟨Z_i⟩,⟨Z_iZ_j⟩` are diagonal in the computational basis, so one set of S shots yields **all**
n+C(n,2) observables):

| n | two-qubit gates | one-qubit gates | observables | shots S (ε≈1/√S) | sim wall-clock |
|---|---|---|---|---|---|
| 8 | 220 | 160 | 36 | 2k–8k (ε≈.011–.022) | <1 s/state |
| 10 | 480 | 200 | 55 | 2k–8k | ~sec |
| 12 | 760 | 240 | 78 | 2k–8k | ~1 min build |
| 16 (sparse) | — | — | 136 | — | ~40 min/point |

*(wall-clock is hardware-dependent — measured on a single CPU here; it is an engineering, not a scientific, quantity.)*

**QPU validation** uses this gate-Trotter circuit on **IonQ / IQM / IBM** via qBraid — the
random-sparse Ising needs *fewer* two-qubit gates than an all-to-all reservoir, easing NISQ
mapping (trapped-ion all-to-all natively supports the arbitrary couplings) — with **ZNE +
measurement mitigation** and a classical cross-check for every run. The submission path is
**executable now** (`qbraid_submit.py`, `cli.py run qsubmit`): on a simulator it (i) reproduces
the engine to **3.9×10⁻¹⁶** via the exact circuit (the classical cross-check we run for every
hardware execution), (ii) characterizes the **shot budget** — mean feature error 0.046 / 0.013
/ 0.0066 at S = 256 / 4k / 16k shots, the ε≈1/√S law, with the gate-Trotter(20) approximation
adding ≈0.04 — and (iii) demonstrates **zero-noise extrapolation** recovering toward the
noiseless value under a depolarizing sweep. It is one flag (`--device`) from a real backend,
pending qBraid credit allocation. We thus characterize all four challenge axes: reservoir size
(§5.1/5.5), encoding density (§5.2/5.3), shot budget, and noise (§5.4). *(QCi Dirac-3 is the
separate optimization challenge's device.)*

## 7. Limitations (stated plainly)
(i) **No quantum advantage** is demonstrated at the ≤16-qubit simulable scale; HAR-X (classical,
linear) is the best model on this task. (ii) The S&P 500 RV sample ends Feb-2020 — the 2008 GFC
is in-sample, the 2020 COVID shock just outside it; broader assets/periods untested. (iii) Noise is studied on MNIST with single-qubit
channels at the readout; full noisy-circuit and shot-noise simulation is deferred to the QPU
runs. (iv) g is regularization-dependent (we report the qualitative gap, not a tuned value).
(v) **No real-QPU run yet** (simulator cross-checked; pending qBraid credit allocation).
(vi) Distinctness and full-rank entanglement are *necessary, not sufficient* for advantage —
whether they convert beyond the classical-simulation frontier is the open question.

## 8. Stakeholder impact, milestone plan, AI disclosure
Earlier, reliable volatility-regime-shift detection feeds portfolio hedging, dynamic risk limits
and derivatives pricing; in the $30B+ daily VIX-options market, marginal gains in transition
timing carry material P&L (JonesTrading). A credible *negative* at simulable scale is itself
decision-useful: it tells practitioners the near-term lever is informed realized-measure
features, not quantum hardware. **Milestone plan:** (i) pre-register ✓; (ii) scaling +
encoding-density sweeps ✓; (iii) adversarial HAR-X/ESN/RFF test ✓; (iv) MNIST + noise ✓;
(v) sparse/TN frontier + bond dimension ✓; (vi) gate-Trotter QPU validation (IonQ/IQM/IBM) —
simulator cross-checked; fallback = TN + density-matrix noise emulation. **AI disclosure:**
Claude (Anthropic) assisted with code and drafting under the team's direction; all formulations,
decisions, and results are the team's own, produced by executing team code on public data.

## References
Kornjača et al. 2024 (arXiv:2407.02553) · Zhu et al. 2025 (PRR 7, 023290) · Ahmed, Tennie &
Magri 2025 (Proc. R. Soc. A 481) · Li et al. 2025 (arXiv:2505.13933) · Tandon et al. 2025
(arXiv:2505.22837) · Hou et al. 2025 (arXiv:2508.12383) · Čindrak et al. 2026 (arXiv:2603.21371)
· Antoncich et al. 2026 (arXiv:2602.14641) · Kobayashi & Motome 2026 (PRL 136, 040602) · Huang
et al. 2021 (Nat. Commun. 12, 2631) · Corsi 2009 · Patton 2011 · Hansen, Lunde & Nason 2011 ·
Diebold & Mariano 1995 · Bollerslev 1986 · Jaeger 2001 · Heber, Lunde, Shephard & Sheppard 2009.
