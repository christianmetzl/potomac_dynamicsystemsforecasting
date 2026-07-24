# CHIMERA-QRC — Physics Work Package

**For:** J. M. Aguiar Hualde (Team EIGENNEXUS) · **Scope:** every calculation in the Phase-3 program — model definitions, protocols, rationale, assumptions, current hardware status · **Provenance:** every number in this document traces to a committed artifact in the repository; file pointers are given throughout. All definitions below were re-verified against the code at writing time.

---

## 1. Program in one paragraph

We test whether a small quantum reservoir computer (QRC) — a *fixed, untrained* quantum dynamical system used as a feature map — offers any advantage over fairly-matched classical methods for forecasting S&P 500 realized volatility (Track A), and we characterize *why or why not* across simulation, noise models, and three real QPU platforms. The program is pre-registered (hypotheses and thresholds committed before decisive runs), adversarially audited, and its headline is an honest negative with mechanism: **statistical parity with tuned classical baselines, no accuracy win in 12+ fair tests, and a measured hardware coherence-budget failure on superconducting devices** — with one decisive test (routing-free trapped-ion) in execution now.

## 2. The reservoir: model definitions (verified against `qrc_engine.py`, `qpu_run.py`)

### 2.1 Hamiltonian

*(Rendered versions: `docs/hamiltonian_light.png` / `docs/hamiltonian_dark.png`; LaTeX source: `docs/hamiltonian.tex`.)*

Transverse-field Ising on a random graph:

    H = Σ_{i<j} J_ij Z_i Z_j + h_x Σ_i X_i        (h_z term available, set to 0)

- **Couplings:** J_ij symmetric, random graph with edge probability (connectivity) **c = 0.5**; on edges, **J_ij ~ Uniform(0.5, 1.5)** — strictly positive (antiferromagnetic in this sign convention), seeded (`generate_coupling_matrix`, seed 0 for all hardware work).
- **Transverse field:** h_x = 1.0.
- **Evolution time:** τ = 2.0 (single-scale; the engine supports multi-τ, the hardware protocol uses one).
- n = 8 qubits for all hardware and the core benchmark; sweeps to n = 16 exact (sparse `expm_multiply`) in simulation.

### 2.2 Input encoding (delay embedding)

One volatility lag per qubit: input window w ∈ [0,1]^n (min-max normalized on the training split, clipped), encoded as product-state rotations **RY(π·w_q)|0⟩** on qubit q. Qubits beyond the input dimension stay |0⟩. This is a *static* (non-recurrent) reservoir read: state prep → evolve U = e^{-iHτ} → measure. The recurrent variant (V3 studies) carries a persistent density matrix with input-qubit reset each step.

### 2.3 Measurement & features

Single measurement setting: all observables are computational-basis-diagonal — **⟨Z_i⟩ (n of them) and ⟨Z_i Z_j⟩ (C(n,2))**, so one shot set yields all n + n(n−1)/2 features (36 at n=8). Features feed a **ridge regression** readout; in the benchmark the quantum features are *nested over* the linear/HAR-X block, so the QRC must add value beyond the classical information to win.

### 2.4 Hardware (Trotterized) form — `base_ops`

First-order Trotter, **L = 20 layers**, dt = τ/L = 0.1. Per layer: all ZZ terms as CX(i,j)·RZ(2·J_ij·dt)(j)·CX(i,j) [IsingZZ(φ) = exp(−iφ/2 · ZZ) with φ = 2·J_ij·dt], then RX(2·h_x·dt) on every qubit. Circuit size at n=8: **828 gates in expanded native form (440 two-qubit)**; the paper's "≈380 native gates (220 two-qubit)" counts each ZZ interaction as one entangling operation. Trotter systematic at L=20: **max feature deviation ≈ 0.039–0.04** vs the exact propagator — deliberately kept below hardware-relevant scales and always quoted alongside hardware errors.

**Equivalence guarantee (`--selftest`):** an independent QASM interpreter (not the engine, not PennyLane) simulates the *emitted string* and matches the exact-diagonalization engine to the Trotter systematic (0.0392); ZNE folding (below) is verified as a noiseless identity to ~1e-12. This is the "the QASM we submit IS the reservoir" proof.

**Angle convention (hardened):** all rotation angles are emitted **mod 2π**. Rationale: RY/RZ/RX(θ+2π) = −(same rotation), a global phase, so all measurement statistics are identical — and we *measured* (see §7.3) that one platform silently mishandles negative angles. ZNE fold circuits contain inverses (negated angles pre-hardening), so this protects the mitigation chain itself.

## 3. Task, data, learning protocol

- **Data:** S&P 500 realized volatility (5-min RV), log-RV target, horizon 1 day; delay-embedded lags as inputs; sample ends Feb-2020 (2008 crisis in-sample; COVID excluded — a stated limitation, §7 of the paper). Supporting daily-proxy studies (V2) cover cross-asset and COVID windows with the same conclusions.
- **Splits:** 70% train; **crisis and calm evaluation windows** are analyzed separately (regime-dependence is part of the pre-registration).
- **Baselines (all tuned, all size-matched):** HAR-X (the econometric standard — linear in RV aggregates), ESN (echo-state network, recurrent, matched feature count, tuned spectral radius/leak), RFF (random Fourier features — the static-kernel analogue of the QRC's feature map), LSTM (capacity-matched).
- **Statistics:** Diebold–Mariano tests with HAC variance (Harvey–Leybourne–Newbold small-sample correction), **Holm** multiple-comparison control, and the **Model Confidence Set** on the decisive four-model family (result: all four retained in both regimes — formal statistical parity). 8 seeds; s.d. reported.
- **Pre-registration:** thresholds and hypotheses (H0/H1/H4) locked in `preregistration.py` before decisive runs; hardware predictions committed before hardware execution (§7.2).

## 4. Simulation experiment catalog — what, why, outcome

| # | Experiment (artifact) | Question | Outcome |
|---|---|---|---|
| 1 | Axis-B benchmark (`axisB_rigorous.py`) | Does the QRC beat tuned classical baselines on RV, crisis & calm? | **Parity.** No significant wins after HAC-DM+Holm; MCS retains all four models in both windows. |
| 2 | Scaling sweep (`scaling_sweep.py`) | How do memory curves, spectral gap, feature rank scale with n? | Diagnostics support reservoir validity; no advantage signal. |
| 3 | Information capacity (Dambre IPC, `information_capacity.py`) | Is the quantum feature map more nonlinearly expressive at matched size? | **No — slightly less** than matched RFF/ESN. |
| 4 | Efficiency frontier (`frontier_scaling.py`) | Can a small QRC substitute for a larger classical reservoir? Does classical irreproducibility g grow with n? | **No.** QRC saturates at its qubit ceiling (weather RMSE 0.85 °C vs classical 0.78/0.71 — lower is better); g *declines* with n (ρ = −0.90) though D_eff and rank grow. Higher dimension ≠ harder to replicate. |
| 5 | MNIST cross-team benchmark | Mandatory cross-team task; PCA(n) encodings | n=12: 0.852, n=15: 0.878 vs ESN 0.884 — competitive, not better. |
| 6 | Noise studies (`noisy_circuit.py`, per-layer channels) | Where does accumulated two-qubit error kill the reservoir? | Predicts the hardware coherence-budget failure later measured on metal (§7). |
| 7 | Weather negatives (5 stations incl. Denver/Rapid City) | Does the negative generalize across domains and chaoticity (+0–78% unpredictability)? | **Negative robust everywhere**; one statistical tie (Rapid City h=1). |
| 8 | Recurrent VPT (Lorenz-63; Jena/Denver weather) | Autonomous prediction: valid-prediction-time (Lyapunov-normalized) vs matched ESN | QRC below ESN — unitary evolution lacks the contraction behind ESN "generalized synchronization." |
| 9 | Engineered dissipation (`v3_research/dissipative_qrc.py`) | Can *deliberate* non-unitarity fix #8? Per-step amplitude damping (rate γ) on memory qubits | **Mechanism demonstrated:** pre-registered inverted-U in γ confirmed; VPT +60% (replicated on fresh starts), lifting QRC from clearly-behind to **parity** with matched ESN — not better. Channel implementation verified against Kraus form to ~1e-17. |
| 10 | Classical shadows head-to-head (`v3_research/shadows_hard_test.py`) | On *quantum-data* tasks (purity, Tr(ρ³)), does QRC beat the proper baseline (Huang–Kueng–Preskill shadows) at matched per-state budgets? | **Shadows win wherever information is extracted.** Apparent QRC wins at tiny budgets equal the trivial ensemble prior (guarded, discarded). Quantum-data question closed negatively at simulable scale. |

Amplitude damping definition used in #9: per memory qubit per step, Kraus K₀ = diag(1, √(1−γ)), K₁ = γ-amplitude lowering; implemented as a fast sliced-index channel on the density matrix, verified against the explicit Kraus contraction.

## 5. Overall scientific conclusion (committed: `results/OVERALL_QRC_CONCLUSION.md`)

Across 12+ fair, size-matched tests spanning finance, weather, images, chaotic systems, and quantum-data tasks: **the QRC wins none on accuracy.** The surviving true statements: per-feature parity of the static maps; dissipation as a genuine mechanism (noise as a resource); and the untested beyond-frontier regime (>40 qubits, hardware-native inputs) — reported as open, explicitly *less* encouraged by the within-reach trend (g declines with n).

## 6. Error/estimation budget — the numbers to keep in mind

| Term | Size | Source |
|---|---|---|
| Shot floor (mean abs feature error) | ≈ 1/√S: 0.016 @ 4k, 0.022 @ 2k, 0.045 @ 500 shots | binomial |
| Trotter systematic (L=20) | ≈ 0.04 max-feature | selftest vs exact engine |
| Fold identity (noiseless) | ~1e-12–1e-14 | selftest |
| **Fully-depolarized reference** | **0.1958** mean abs error | = mean |F_exact| over the 3 RV windows × 36 observables: a totally scrambled device drives all features → 0, so its error equals the mean feature magnitude. **Measured error above this line ⇒ coherent/structured error, not mere depolarization.** |
| Readout (measured): Rigetti | P(1|0)=2.26%, P(0|1)=6.39% | calibration jobs |
| Readout: IQM Garnet | 0.56% / 3.55% | calibration jobs |
| Readout: IonQ Forte-1 | ≈0.4%/qubit (excitation probe); hardened |0⁸⟩ prep measured 498/500 | probe + control |

## 7. Hardware program

### 7.1 Protocol anatomy (12 circuits per device; `qpu_run.py`)

1. **Orientation probe** (RY(π) on qubit 0 only): detects bitstring endianness — all three vendors key little-endian through this stack; auto-corrected. Binary question ⇒ 100 shots suffice (`--probe-shots`).
2. **Readout calibration:** |0…0⟩ prep as **rz-only** circuit (diagonal ⇒ exact under *any* subset of gates executing — see §7.3 for why that paranoia is warranted) and |1…1⟩ as RY(π)⊗n. Builds per-qubit 2×2 confusion matrices; mitigation = tensor-product inverse applied to the counts distribution (exact 2^8 inversion — mthree-style approximations unnecessary at n=8).
3. **3 RV windows × ZNE fold scales {1,3,5}:** global folding G(G†G)^k multiplies coherent exposure; linear and Richardson extrapolation to zero noise. **ZNE's validity assumption: scale 1 must be inside the coherence budget** — the Rigetti run demonstrates what happens when it is not.
4. **Classical cross-check:** every hardware feature vector is scored against the exact engine — |F_hw − F_exact| per stage of the mitigation chain.

Ops hardening (all production-tested): job-level checkpointing (completed counts and in-flight job IDs persisted; resume never re-bills), fail-fast on billed "insufficient credits", submit-retry on transient platform failures, per-job provenance: **each job embeds the repo commit hash in the platform's timestamped records** (hash-preimage argument ⇒ the pre-registration ordering is externally verifiable — no trust in our git dates required).

### 7.2 Pre-registered predictions (committed before execution)

Probe-calibrated depolarizing+readout stand-in models predicted the full chains (4k-shot config): Garnet 0.171 → 0.147, IonQ 0.149 → 0.122 (raw → Richardson). Three falsifiable statements: **(i)** monotone mitigation recovery on both devices; **(ii)** IonQ raw < superconducting raw; **(iii)** Garnet measured raw *exceeds* 0.171 (we chose not to model SWAP routing — the prediction is knowingly optimistic).

### 7.3 Executed so far — results and findings

> **Historical (mid-program) snapshot.** §7.3–7.4 were written during execution and describe an
> intermediate state. The **full program has since completed** — ten provenance-tagged campaigns
> across IonQ Forte-1, IQM Garnet, IQM Emerald, and Rigetti Cepheus-1 — with the authoritative,
> scored results in `results/qpu_hardware_findings.md`. Individual stale lines below are retained
> for provenance.

- **Rigetti Cepheus-1-108q (full protocol, 12 jobs):** raw 0.261 > depolarized limit 0.196 — after lattice routing (~10³ native 2q gates at scale 1) the circuit is *coherently scrambled*, not merely noise-flattened; readout mitigation is a no-op (gate ≫ readout error); ZNE cannot recover because scale 1 already exceeds the budget. **(iii)-analog confirmed, (i) refuted on this class** — a characterized negative that measures exactly what the §4-#6 noise study predicted.
- **IQM Garnet (first window, checkpointed):** raw 0.238 — same regime, second superconducting vendor; completion (8 circuits) funded and queued.
- **IonQ Forte-1:** the **negative-angle platform finding**: an RY(π)RY(−π) identity pair executed as **net RY(π)** (94.8% |1⁸⟩) while the client-side IonQ JSON provably contained both signed rotations — negative-angle rotations are lost server-side. Global-phase-equivalent hardening (mod-2π emission + diagonal calibration) validated on-device: 99.6% |0⁸⟩. Reported to qBraid with reproduction bundle (`results/platform_feedback_bundle/`) — **vendor confirmation pending**. The full scale-1 campaign (500-shot config, a disclosed cost deviation from the 4k prediction config) subsequently executed — raw 0.104, signal-bearing (`results/qpu_hardware_findings.md`).
- Also documented: qir-sv cloud simulator reproducibly deviates at n=12 (~9× shot floor) while n≤10 is exact — reported, confirmation pending.

### 7.4 Current campaign state (as of writing)

Campaign A (Garnet native route, 4k shots — *the pre-registered config*): orientation probe queued awaiting the device availability window; ~6,755 qBraid credits budgeted of a 60k allocation under a pre-committed manifest with abort rules (`results/qpu_campaign_manifest.md`). Campaign B (IonQ, ≈46k credits) follows sequentially after an explicit go decision, gated on a low-shot smoke test of the fold-5 circuit class (4,140 expanded gates — never yet billed at this length).

## 8. Assumptions register (the honest list)

1. **Readout noise model:** uncorrelated per-qubit confusion (tensor product). Cross-talk readout correlations are not modeled; at n=8 with the measured error rates this is second-order, but it is an assumption.
2. **ZNE noise-scaling assumption:** folding multiplies a *time-stationary, gate-proportional* noise channel. Violated when scale 1 exceeds the coherence budget (measured on Rigetti) or when noise is strongly coherent.
3. **Trotter order/depth fixed** (first-order, L=20): systematic ≈0.04 accepted and disclosed rather than extrapolated away.
4. **Prediction noise model:** per-2q-gate depolarizing + readout flips, *no routing/SWAP modeling* (declared before the runs; the basis of statement (iii)); the per-qubit split of prep vs readout error from the excitation probe is not identifiable — attributed to readout.
5. **Data limitation:** RV sample ends Feb-2020; COVID out-of-sample; V2 daily-proxy studies cover it with the same conclusion, at lower data quality.
6. **g (kernel irreproducibility) is regularization- and configuration-dependent** — reported as a qualitative gap only.
7. **Distinctness/rank are necessary, not sufficient** for advantage; conversion beyond the simulable frontier is untested (and the within-reach trend discourages extrapolation).
8. **500-shot IonQ config** is a disclosed deviation from the pre-registered 4k config (cost-driven); decisive claims (monotone recovery, cross-platform ordering) are read from the mean over 108 observables, s.e. ≈ 0.004 — resolvable at 500 shots.

## 9. Where everything lives

| Artifact | Content |
|---|---|
| `PHASE3_PAPER.md/pdf` | The 5-page submission |
| `results/qpu_hardware_predictions.md` | Pre-registered predictions + calibration inputs |
| `results/qpu_hardware_findings.md` | Rigetti characterized negative, scored |
| `results/qpu_campaign_manifest.md` | The 60k-credit campaign, per-job budget, abort rules |
| `results/qpu_ckpt_*.json` | Job-level checkpoints (counts + job IDs) |
| `results/platform_feedback_qbraid.md` + `_bundle/` | Both platform findings with reproduction evidence |
| `results/OVERALL_QRC_CONCLUSION.md` | The 12-test synthesis |
| `results/*_findings.md` | Per-experiment write-ups (capacity, frontier, dissipation, shadows, …) |
| `score_campaign.py` | Automated prediction-scoring for completed campaigns |
| `tests.py` (24 checks) · `cli.py reproduce` | One-command verification & reproduction |

**Suggested first checks for a fresh pair of physicist eyes:** (a) the depolarized-limit argument in §6 — it is load-bearing for the "coherently scrambled, not depolarized" claim; (b) the global-phase argument for mod-2π emission (§2.4) — trivial but everything downstream trusts it; (c) the ZNE validity condition vs the measured Rigetti chain; (d) whether the tensor-product readout model is adequate for Garnet's 3.55% P(0|1) at n=8.
