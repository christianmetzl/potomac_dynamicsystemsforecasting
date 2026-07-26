# CHIMERA-QRC: A Pre-Registered, Adversarially-Controlled Study of Quantum Reservoir Computing for S&P 500 Realized-Volatility Forecasting
### Team EIGENNEXUS — C. Metzl, F. Eldibani, J. M. Aguiar Hualde · Track A (Financial Volatility) · GIC 2026 Phase 3

**Abstract.** We contribute a pre-registered, adversarially controlled **evaluation instrument**
for quantum reservoir computing and apply it to S&P 500 realized-volatility forecasting on four
devices from three QPU vendors (IonQ, IQM, Rigetti). The full audit reruns offline in one command
(`cli.py verify`), and every hardware prediction is bound to a prior commit by a hash-preimage
commitment. Two measurements stand on their own: an empirical quantum-complexity metric — the
reservoir's MPS bond dimension is essentially full, **χ_eff ≈ 2^(n/2)**, at the
classical-simulability boundary — and a cross-platform **coherence-budget wall** (Fig. 3), whose
readout-corrected fingerprint separates coherent circuit routing from depolarizing and damping
noise; every bootstrapped regime verdict sits **9.7–23.9σ** beyond shot noise. Applied to
forecasting, the instrument returns a well-characterized negative. At simulable scale (≤16
qubits) the reservoir is *distinct but not more accurate* than the strongest fair baselines —
HAR-X and size-matched ESN/RFF under HAC-DM, Holm and MCS — so **H0 is refuted**. The finding
survives a second reservoir family (Heisenberg — not Ising-specific) and a second domain
(weather), and the program falsified four of its own pre-registered predictions under controls;
a same-session cross-seed control shows the n=8 scrambling is specific to the seed-0 instance,
not a size law. For a trading desk the practical lever turns out to be simpler than quantum
hardware: vol-timing a plain RV forecast roughly halves the 2008 drawdown, and quantum adds no
economic value at this scale.

## 1. Focus, track selection, and problem framing
We target **Track A: financial volatility** — one-step-ahead forecasting of S&P 500 realized
variance (RV) and the tracking of volatility regime transitions, the domain where JonesTrading's
risk, allocation and derivatives pricing live. RV is long-memory, multi-scale, regime-switching
and non-Gaussian; this is precisely the structure reservoir computing exploits. Our central
yardsticks are the Echo State Network (ESN, the classical analog of QRC) and the strongest
econometric models: HAR (*Heterogeneous AutoRegressive*, Corsi 2009) and, critically for
Phase 3, **HAR-X** — HAR augmented with the same realized-measure features we feed the quantum
reservoir. We also report GARCH/GJR-GARCH, AR(3), persistence, LSTM, and an RFF/RBF kernel,
and we implement the challenge's common MNIST benchmark on the identical engine.

**Thesis.** We pre-registered H0 and then attacked our own result with fair controls. The
dominant accuracy lever is *which features are encoded*, not quantum nonlinearity. What survives
for the reservoir — kernel distinctness, lower seed variance, full-rank entanglement (classical-
simulation hardness) — is necessary for advantage but not sufficient.
**Relation to prior work.** The closest study (Li et al. 2025/26, QRC for realized volatility)
presents the approach as a competitive, noise-resilient proof of concept. We add the
control-hardened, pre-registered evaluation it omits — the decisive HAR-X control, HAC-DM with
Holm and MCS, and explicit capability and per-layer-noise audits — which turns an encouraging
proof of concept into a falsifiable result.

## 2. QRC architecture (Fig. 1)
CHIMERA is a delay-embedding quantum reservoir. Inputs are angle-encoded `RY(π·x)`, one value
per qubit, onto `|0…0⟩`; the state evolves under a fixed transverse-field Ising Hamiltonian
`H = Σ_{i<j} J_ij Z_iZ_j + h_x Σ_i X_i` (`h_x=1`; `J` a random ≈50%-connected graph,
`connectivity=0.5`; `U=exp(−iHτ)`, `τ=2`); single- and pairwise Pauli-Z expectations
`⟨Z_i⟩,⟨Z_iZ_j⟩` form the feature vector. A ridge head consumes these features concatenated
with a linear block of the same inputs (including HAR), so any reservoir gain must be genuine
nonlinearity beyond the linear span of identical information. The same inputs feed the classical
controls, isolating quantum from classical. Four mechanisms extend the core (multi-scale τ-bank;
RZ measurement feedback; regime-adaptive Ising↔Heisenberg via BOCPD; dissipation-as-feature);
Phase 3 adds an encoding-density / data-re-uploading path (§5.2) and a sparse/tensor backend
(§5.5). The engine is pure NumPy; an explicit PennyLane circuit reproduces it to ≈3.9×10⁻¹⁶ and
compiles, at n=8, to 380 native gates (220 two-qubit + 160 one-qubit, 20 Trotter layers),
consistent with the ≈50%-connected graph.

![**Figure 1.** CHIMERA-QRC pipeline: lagged log-RV (and, in Axis B, realized-measure) inputs are angle-encoded onto qubits, evolved under a fixed random-coupled Ising Hamiltonian, and read out as single/pairwise Pauli-Z expectations into a ridge head fused with a linear block of the same inputs; a BOCPD detector selects the Hamiltonian for regime adaptivity.](figures/fig_architecture.png)

## 3. Theoretical and analytical justification
The quantum resources we exploit map onto RV's structure: (a) Hilbert-space dimensionality —
n qubits give 2ⁿ amplitudes and O(n²) measured Pauli features at O(n²) parameter cost;
(b) intrinsic nonlinearity from fixed unitary evolution, with no gradient training and no barren
plateaus; (c) delay-embedded memory (the headline model's memory is its explicit lag window, not
reservoir recurrence — a recurrent variant is probed in `v3_research`); (d) the Hamiltonian as
inductive bias. The central falsifiable mechanism is expressivity scaling, which we measure
directly via the geometric difference (Huang et al. 2021). The quantum kernel is poorly
reproducible by a matched classical reservoir: g(ESN→CHIMERA) ≈ 64 versus ≈3.7 for the control
(`cli.py run kernel`); against per-n feature-matched ESNs it is larger but non-monotonic
(≈125/158/88 at n=8/10/12, fixed ridge — the qualitative separation, not the value, is the
claim). At ≤12–16 qubits the map stays classically simulable, so distinctness is necessary but
not sufficient — and we measured exactly that: over 30 seeded n=8 instances,
per-instance entanglement shows no detectable correlation with forecast error (r=−0.19, p=0.32),
and **0/30 instances beat HAR-X** on both crisis and calm windows (bounding the beat-rate at
≤9.5%, exact one-sided 95%). Nor does instance quality detectably transfer — crisis and calm
rankings are unrelated (Spearman +0.01) — so best-of-N seed selection is selection on noise.
These tests detect only |r|≳0.5, so they exclude strong links, not weak ones
(`expressivity_accuracy_findings.md`; exploratory, uncorrected).

## 4. Data modeling strategy
**Datasets (all bundled in-repo).** Oxford-Man `.SPX` 5-minute realized variance, 2000–2020,
5,029 supervised days including the 2008 GFC (Heber et al. 2009; via R packages
`highfrequency`/`bvhar`); SPY daily OHLCV 2022–2026 (Garman–Klass proxy; retrieved via
Massive.com API, bundled); real MNIST (Keras `.npz` mirror).
**Preprocessing.** Log-RV target; features min-max scaled to [0,1] on train only; per-model
ridge penalty selected on a chronological validation tail; multi-seed ensembling. We verified
the pipeline is leakage-free (all features lagged ≥1 day; train-only scaling). **Baselines:**
HAR, HAR-X, GARCH(1,1), GJR-GARCH, AR(3), persistence, ESN (matched, 4×, and recurrent), RFF
kernel, LSTM. **Metrics:** RMSE(log-RV), QLIKE (Patton 2011), Mincer–Zarnowitz R²; significance
by Diebold–Mariano with a Newey–West HAC variance (HLN-corrected), Holm-adjusted across the
comparison family, plus the Model Confidence Set (Hansen–Lunde–Nason 2011). Holm and MCS are
scoped to this pre-registered family; the §3/§8 correlations are exploratory, uncorrected, and
none survives Holm.

## 5. Phase-3 execution — concrete results
**Pre-registration.** Before running anything, we fixed the confirm/refute thresholds in
`preregistration.py` (H0/H1/H4, from our Phase-2 §7). All outcomes, including the negatives, are
reported against those thresholds. Full numbers and wall-clock times: `results/*_findings.md`.

**5.1 The input-bottleneck mechanism (pre-registered negative).** With a fixed univariate
8-lag encoder, extra qubits receive no new input, and both g(n) and effective feature-rank
saturate or decline (n=8→12: g 133→30 at N_sub=800; D_eff 1.8→1.5). H0 is refuted in this
regime — which is itself the empirical case for enriching the encoding.

**5.2 Encoding density (Axis B) — mechanism confirmed.** Feeding the extra qubits genuinely new
realized-measure information (signed return/leverage, downside-semivariance share, jump share)
restores the lost structure: at n=10, informed versus idle qubits, kernel distinctness and rank
jump (g 52→158, D_eff 1.5→3.1), and effective rank grows with n (D_eff 1.81→3.14, n=8→12). The
bottleneck is therefore fixable; added qubits can carry new information. The decisive question
is whether this converts into forecasting accuracy.

**5.3 The decisive, adversarially controlled test.** We compare CHIMERA against the strongest
fair baselines — HAR-X (the same rich features used linearly, no reservoir), a true recurrent
ESN, and an RFF kernel — all sharing the identical information set and nesting HAR-X, so a
quantum win requires nonlinearity beyond the linear span. With 8 seeds, HAC-DM, two windows, and
Holm correction (`cli.py run axisB_rig`):

| RMSE(log-RV) | HAR-X | recurrent ESN | RFF | CHIMERA | best |
|---|---|---|---|---|---|
| crisis n=8 | **0.6255** | 0.6386 | 0.6302 | 0.6379 | HAR-X |
| crisis n=10 | 0.6034 | **0.5996** | 0.6047 | 0.6074 | ESN |
| crisis n=12 | **0.5906** | 0.6023 | 0.5964 | 0.6031 | HAR-X |
| calm n=10 | **0.6244** | 0.6445 | 0.6264 | 0.6291 | HAR-X |

*(plain HAR for reference: crisis 0.6290, calm 0.6454 — HAR-X's rich features cut RMSE sharply.)*
HAR-X is best or co-best everywhere; CHIMERA never beats it and is indistinguishable from the
classical ESN/RFF after Holm (one raw loss to RFF at crisis n=8, p=0.049). After Holm correction
no comparison is significant in either direction, and the 95% MCS retains all four models
(n=10) — a statistical tie. The earlier "beats HAR" result was an artifact of a feature-poor
HAR: the gain is the encoded realized measures (a known SHAR/HARQ effect), not quantum
nonlinearity. **By our pre-registered criteria, H0 is refuted, and we report this
negative.** What does survive for the quantum reservoir: it is competitive (within ≈0.8–2.1%
RMSE of the best at every n), it shows lower per-seed dispersion than the recurrent ESN in 3 of
4 cells (n=12: 0.009 vs 0.015), and it beats the ESN on the calm window (raw p=0.018; not
significant after Holm). A tuned, size-unconstrained ESN (45-config search to 800 nodes)
confirms the control was not crippled (0.6020 vs CHIMERA 0.6094, within noise of HAR-X). Named
canonical models (SHAR, HAR-CJ, HARQ, HEAVY-RM; MSE and QLIKE DM): none beats HAR-X, with
CHIMERA tying best on RMSE and holding only a raw, non-Holm QLIKE/MZ edge
(`cli.py run canonical`, `esn_tuning_robustness_findings.md`).

![**Figure 2.** Rigorous Axis-B (8 seeds, crisis window). HAR-X (rich features, linear) is the best or co-best model at every n; the quantum reservoir is competitive but shows no advantage that survives HAC-DM + Holm correction. Left: RMSE(log-RV). Right: Mincer–Zarnowitz R².](figures/fig_axisB_rigorous.png)

**5.4 Common MNIST benchmark and noise.** Same engine: pixels→PCA(n)→n qubits→Pauli
readout→ridge. Accuracy scales with qubits (n=5/8/10/12: 0.632/0.798/0.831/0.859, 3 seeds;
n=15 sparse-exact continues the trend, 0.878 vs 0.852 for a paired n=12 on a matched subset,
closing the brief's 5/10/15 example) and beats the linear-PCA baseline at every n — real
nonlinear lift, confirming sufficient expressivity. A matched ESN ties or slightly exceeds
CHIMERA (within ≈1% for n≥8; 2.9% at n=5): competitive, not dominant. On noise, the classifier
is invariant to depolarizing noise — a uniform Bloch contraction that per-feature
standardization removes exactly, with accuracy identical across rates 0.05–0.30 — and robust to
amplitude damping (<0.5% at 30%). A converse check (`cli.py run noise_circuit`): per-layer
single-qubit channels interleaved with the evolution are *not* removed by standardization
(standardized error grows with rate, versus ≈0 for readout-only depolarizing) — the invariance
is a readout property, not circuit robustness; accumulated gate error is the real NISQ cost
(§6).

**5.5 Scaling frontier and the quantum-complexity metric.** A sparse-exact backend
(`expm_multiply`, no dense propagator; matches the dense engine to 2.4×10⁻¹⁴) reaches n=16
exactly. For the random ≈50%-connected reservoir we measure the bond dimension χ_eff across a
balanced cut: it is essentially full at every n, **χ_eff ≈ 2^(n/2)** (16→255.9 for n=8→16), and
an exact MPS gets zero compression (S ≈ 1.7–3.2 nats). The reservoir admits no
low-bond-dimension (MPS/TEBD) shortcut; exact cost stays exponential — the precondition any
beyond-frontier advantage would need, though none appears at testable scale.
Capability checks agree: an information-processing-capacity probe (Dambre et al. 2012;
`cli.py run capacity`) finds the reservoir slightly *less* nonlinearly expressive than a matched
RFF/ESN — no excess expressivity to exploit — and g(n) does not widen toward n=16
(`cli.py run frontier`: it declines; D_eff and rank grow but a matched ESN keeps pace). Robustness studies close the loop. Second
family: a Heisenberg (XXZ) reservoir, equally kernel-distinct (g≈55), also fails to beat HAR-X
(0.650 vs 0.642, 8 seeds, full-sample config), so the negative is not Ising-specific
(`cli.py run second_family`). Efficiency: with input held fixed, a smaller QRC cannot substitute
for a larger classical reservoir — quantum accuracy saturates while the classical curves keep
improving; per feature the static maps are comparable, so the negative is saturation, not
per-feature inferiority (weather RMSE °C: CHIMERA 0.85 at its qubit-range ceiling vs RFF 0.78 /
recurrent ESN 0.71 at larger budgets). Domain and architecture: the same engine and protocol on
chaotic weather data (5 stations) and the autonomous VPT metric still show no advantage, and the
recurrent QRC is competitive but not better — unitary evolution is non-dissipative, lacking the
contraction behind ESN "generalized synchronization" (Ahmed–Tennie–Magri 2025). We then fixed
that mechanism: engineered memory-qubit damping traces the pre-registered inverted-U, lifting
autonomous VPT by ≈60% to parity with the matched ESN — parity, not advantage
(`results/dissipative_qrc_findings.md`).

## 6. Quantum platform and resource planning
Simulator-first on qBraid: statevector to 12 qubits, sparse/TN to ≈16, GPU beyond.
Resource estimates (gate-Trotter, 20 layers): n=8/10/12 use 220/480/760 two-qubit plus
160/200/240 one-qubit gates, yielding 36/55/78 observables — all Z-basis-diagonal, so one
S-shot set (S≈2–8k, ε≈1/√S) reads every observable (statevector build ≲1 min).

QPU validation uses this gate-Trotter circuit on IonQ, IQM and Rigetti via qBraid — the
random-sparse Ising needs fewer two-qubit gates than all-to-all, easing NISQ mapping — with ZNE, measurement mitigation, and a classical cross-check on every run. The
submission path is executable now (`cli.py run qsubmit`): on a simulator it (i) reproduces the
engine to 3.9×10⁻¹⁶ (the per-run classical cross-check), (ii) characterizes the shot budget
(ε≈1/√S; feature error 0.046→0.0066 at S=256→16k; gate-Trotter(20) adds ≈0.04), and
(iii) demonstrates zero-noise extrapolation under a depolarizing sweep. On real hardware, the
full mitigated protocol ran first on Rigetti Cepheus-1-108q (12 logged cloud jobs; bit order
auto-detected; readout 2.3%/6.4%). After lattice routing, scale-1 already exceeds the coherence
budget — the accumulated two-qubit-gate cost §5.4 predicts, measured on metal (ZNE marginal;
a 4k-shot replication showed the beyond-limit regime stable under day-scale drift). The
pre-registered Garnet protocol replicated the regime on a second vendor (raw 0.230 exceeds our
routing-free 0.171 forecast — prediction (iii) confirmed). Execution also surfaced a
platform-level finding: negative-angle rotations are silently lost server-side on the IonQ
route (RY(π)RY(−π) arrives as net RY(π)), which corrupts ZNE's negated folds; we hardened the
emitter (mod-2π) and validated the diagonal calibration on-device. The routing-free IonQ
Forte-1 campaign then ran under the pre-committed manifest. A smoke gate measured a
2,000-gate-per-circuit ceiling on the native route, so per abort rule the campaign ran
scale-1-only (500 shots — a disclosed, cost-forced deviation, s.e.≈0.004). Raw error 0.104,
below the 0.196 depolarized limit and below every superconducting n=8 number: a
**signal-bearing** hardware execution of this reservoir (prediction (ii) confirmed;
`results/qpu_hardware_findings.md`). A pre-registered hardware scaling program
(`results/qpu_scaling_outlook.md`) then refuted our own statements on metal (Fig. 3). Garnet
turns signal-bearing at n=10 and n=12 while the same-session seed-0 n=8 anchor stays scrambled;
a pre-registered cross-seed control (S7) found an independent seed-1 n=8 instance signal-bearing
in the same session, so the n=8 scrambling is specific to the seed-0 instance, not a size law
(seed-1 n=10 is signal-bearing as well). The split is **33σ**: the same-session instances
differ in raw error by 0.069 under the committed bootstrap, independent of any limit convention.
The newer-generation Emerald is signal-bearing at the
very size Garnet scrambles, reproduced in a same-window two-chip pair — generation-dependent at
fixed size, temporally controlled. The program spans reservoir size, encoding density, shot
budget and noise; Fig. 3 collects the hardware verdicts. The criterion is exactly **SNR > 1** —
raw error is mean|F−F_exact|, the limit is mean|F_exact| — so the bar is instance-matched
(signal magnitude is a circuit property, not an n property) and the test transfers to any
quantum feature map:

![**Figure 3.** Cross-platform coherence-budget wall: mean raw feature error vs the **instance-matched** depolarized limit mean|F_exact| (black ticks; 4k shots, IonQ 500). Five configs signal-bearing, two scrambled. The adjacent Garnet n=8 seed-1 (0.159) vs seed-0 (0.228) pair — same chip and session — refutes a *size* law. Seed-0 limits 0.196/0.179/0.214; seed-1 carries its own 0.1806 (§6).](figures/fig_coherence_wall.png)

**Execution provenance (externally verifiable).** Every campaign ran against pre-committed
predictions — the ten funded ones under a committed manifest whose abort and decision rules were
fixed before each launch. Every funded-campaign job embeds the repo commit hash and campaign tag
in qBraid's timestamped records, a hash-preimage commitment that the predictions predate the
data, and billing matched estimates to the half-credit (`results/CREDIT_BUDGET.md`: ≈64k
credits). Bootstrap from the committed counts re-derives every number above and puts each of the
nine bootstrapped regime claims 9.7–23.9σ beyond shot noise; a readout-corrected fingerprint
attributes the scrambled regime to predominantly coherent error (`qpu_bootstrap`,
`qpu_fingerprint`). Controls were bought where needed: a Rigetti replication
(day-drift), a same-session n=8 anchor, and a same-window two-chip pair (generation). S5–S6 are
pre-committed; S7 executed (above).

The instrument's discipline was exercised live in the final days. A
pre-registered secondary arm (H-EMBED — does logical→physical placement drive the seed-0 n=8
scrambling?) was made execute-ready (label permutation exact to 9.0×10⁻¹⁶; depolarized limit
provably identical between arms; scoring rule and vacuity guard committed before launch,
`results/h_embed_prerun.md`), then aborted by its own committed rule when the target device
stopped accepting work: ~21 h and 24 probes without a completion while the route advertised it
online with an empty queue. A matched-pair control — the identical one-qubit probe, same route,
second device, completed in 182 s — localized the fault to the device, and the committed
`route_health_probe.py` reproduces it in minutes. Nothing was scored; the arm remains open
(`results/h_embed_outcome.md`).

## 7. Limitations
(i) No quantum advantage is demonstrated at the ≤16-qubit simulable scale; HAR-X, a classical
linear model, is the best model on this task. (ii) The RV sample ends Feb-2020 (COVID falls just
outside); broader assets and periods are daily-proxy supporting studies (v2_research — same
negative), not 5-min RV. (iii) Task-level noise: per-layer channels (§5.4) and shot noise;
combined noisy-plus-shot execution is measured in the QPU campaigns (§6). (iv) g is
regularization- and configuration-dependent, so we use it qualitatively only.
(v) Superconducting n=8 execution is a characterized negative (Fig. 3; day-drift exceeds shot
noise, so the regime, not the point value, is the robust claim), while n=10/n=12 and the newer
generation land inside their limits. The wall is instance- and generation-dependent, not
absolute: the n=8 scrambling is seed-0-instance-specific (S7), and in a 30-instance ensemble the
scrambled instance is among the sparsest, so gate count anti-predicts the wall (§8). Mitigation
recovery on hardware is at best marginal (ZNE 0.223→0.217 on Rigetti; the ion chain is flat).
(vi) Distinctness and full-rank entanglement are necessary but not sufficient (measured, §3);
whether they convert beyond the simulable frontier remains open. A quantum-data probe shows the
QRC natively reads nonlinear state functionals a linear readout cannot, but the proper
baseline — classical shadows (Huang–Kueng–Preskill 2020) at matched budgets — wins wherever real
information is extracted, including the shadows-hard Tr(ρ³): closed negatively at simulable
scale (`shadows_hard_findings.md`).

## 8. Stakeholder impact, milestone plan, AI disclosure
The durable asset is the audit instrument, and our data shows it is necessary.
Structure mis-ranked both instances we measured on metal, and across 30 instances no
structural quantity survives multiplicity correction as a predictor of the hardware bar, nor
predicts accuracy at all. Structure does not give the answer; measurement does
(`instance_ensemble_findings.md`, exploratory). What follows is trust in a quantum yes/no: a
pre-registered, vendor-neutral workload→QPU qualification, earned by an instrument that
falsifies its own predictions. It split our runs five signal-bearing, two scrambled (Fig. 3) at
≈$70–$205 per campaign. The economics are measured, not modelled
(`results/AUDIT_ECONOMICS.md`): the 13-campaign, four-device program settled at 64,048.25
credits — about $650 at the only rate we measurably paid (≈$14 per ≈1,380 credits) — and the
gate flagged 29.3% of our own settled hardware spend (four campaigns, 18,793.25 credits) as
scrambled at ≥9.7σ: features that would otherwise have entered a pipeline as data. The
audit is a rounding error of any serious pilot budget (1.3% of $50k;
0.065% of $1M), and re-running every verdict is free: this zip, extracted into a clean directory
with no API key, passes `cli.py verify` end-to-end — the judge's path; a self-contained browser
replay (`docs/verify_replay.html`) covers reviewers who prefer not to run it. Auditing a new
workload is mechanical; this repository is the pilot kit: (i) compute the workload's
instance-matched depolarized limit offline, before any hardware is bought; (ii) qualify the route
with the near-zero-cost health probe; (iii) run the orientation probe, two calibrations, and the
scale-1 windows (folds where the gate ceiling allows); (iv) score mean error against the
limit with a multinomial-bootstrap σ from the raw counts; (v) apply the pre-committed abort and
decision rules as written. Every step ran at least once on real hardware here; none is
hypothetical. Target profiles only; no customers or LOIs are claimed. On desk impact
(`cli.py run economics`): vol-timing the GFC window halves max drawdown (−61%→−32%) and lifts
Sharpe from 0.00 to 0.14 net of costs — risk control, not alpha — but plain HAR captures it
(CE fee −25bp/yr). The lever is a simple RV forecast, not quantum hardware.
**AI disclosure:** Claude (Anthropic) assisted with code and drafting; all decisions and results
are the team's own. Milestones (i)–(vi) all ✓ (§6).

<!-- pagebreak -->

## References
Ahmed, O., Tennie, F. & Magri, L. (2025). Robust quantum reservoir computers for forecasting chaotic dynamics: generalized synchronization and stability. *Proceedings of the Royal Society A* 481, 20250550. arXiv:2506.22335.

Antoncich, L., Moodley, Y., Varetto, U., Wang, J., Wurtz, J., Chen, J., Elahi, P. J. & Myers, C. R. (2026). Quantum reservoir computing with neutral atoms on a small, complex, medical dataset. arXiv:2602.14641.

Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics* 31(3), 307–327.

Čindrak, S., et al. (2026). Memory–nonlinearity trade-off across quantum reservoir computing frameworks. arXiv:2603.21371.

Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics* 7(2), 174–196.

Dambre, J., Verstraeten, D., Schrauwen, B. & Massar, S. (2012). Information processing capacity of dynamical systems. *Scientific Reports* 2, 514.

Diebold, F. X. & Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business & Economic Statistics* 13(3), 253–263.

Hansen, P. R., Lunde, A. & Nason, J. M. (2011). The model confidence set. *Econometrica* 79(2), 453–497.

Harvey, D., Leybourne, S. & Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting* 13(2), 281–291.

Heber, G., Lunde, A., Shephard, N. & Sheppard, K. (2009). Oxford-Man Institute's Realized Library. Oxford-Man Institute, University of Oxford.

Hou, Y., Hua, J., Wu, Z., Xia, W., Chen, Y., Li, X., Li, Z., Peng, X. & Du, J. (2025). High-accuracy temporal prediction via experimental quantum reservoir computing in correlated spins. arXiv:2508.12383; *Physical Review Letters* (2026).

Huang, H.-Y., Broughton, M., Mohseni, M., Babbush, R., Boixo, S., Neven, H. & McClean, J. R. (2021). Power of data in quantum machine learning. *Nature Communications* 12, 2631.

Huang, H.-Y., Kueng, R. & Preskill, J. (2020). Predicting many properties of a quantum system from very few measurements. *Nature Physics* 16, 1050–1057.

Jaeger, H. (2001). The "echo state" approach to analysing and training recurrent neural networks. GMD Report 148, German National Research Center for Information Technology.

Kobayashi, K. & Motome, Y. (2026). Edge of many-body quantum chaos in quantum reservoir computing. *Physical Review Letters* 136, 040602. arXiv:2506.17547.

Kornjača, M., et al. (2024). Large-scale quantum reservoir learning with an analog quantum computer. arXiv:2407.02553.

Li, Q., Mukhopadhyay, C., Bayat, A. & Habibnia, A. (2026). Quantum reservoir computing for realized volatility forecasting. *Physical Review Research*; arXiv:2505.13933.

Patton, A. J. (2011). Volatility forecast comparison using imperfect volatility proxies. *Journal of Econometrics* 160(1), 246–256.

Tandon, A., et al. (2025). Quantum reservoir computing for corrosion prediction in aerospace: a hybrid approach for enhanced material degradation forecasting. arXiv:2505.22837.

Zhu, C., et al. (2025). Minimalistic and scalable quantum reservoir computing enhanced with feedback. *npj Quantum Information* 11; arXiv:2412.17817.
