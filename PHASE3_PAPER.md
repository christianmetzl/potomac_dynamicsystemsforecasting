# CHIMERA-QRC: Regime-Aware Quantum Reservoir Computing for S&P 500 Realized-Volatility Forecasting
### Team EIGENNEXUS — C. Metzl, F. Eldibani, J. M. Aguiar Hualde · Track A (Financial Volatility) · GIC 2026 Phase 3

> *Content for the 5-page Phase-3 write-up (11-pt Times New Roman, single-spaced),
> to be placed after the required GIC_2026 cover page. Every number here is produced
> by a script in this repository and reproducible via `python3 cli.py reproduce`.*

## 1. Focus, track selection, and problem framing
We target **Track A: financial volatility** — specifically one-step-ahead forecasting of
S&P 500 **realized variance (RV)** and the tracking of volatility **regime transitions**.
RV is long-memory, multi-scale, regime-switching and non-Gaussian — the structure reservoir
computing exploits — and the domain where JonesTrading's risk, allocation and derivatives
pricing live. Per the rubric our central yardstick is the Echo State Network (ESN, the
classical analog of QRC); we also benchmark the strongest econometric model, the daily
**Heterogeneous AutoRegressive** model (HAR — *Heterogeneous AutoRegressive*; Corsi 2009),
plus GARCH/GJR-GARCH, AR(3), persistence, and an LSTM. We also implement the challenge's
common **MNIST** benchmark on the identical engine.

## 2. QRC architecture (Fig. 1)
CHIMERA is a delay-embedding quantum reservoir. Inputs are angle-encoded `RY(π·x)`, one
value per qubit, onto `|0…0⟩`; the state evolves under a fixed transverse-field **Ising**
Hamiltonian `H = Σ_{i<j} J_ij Z_iZ_j + h_x Σ_i X_i` (`h_x=1`, random `J`, `U=exp(−iHτ)`,
`τ=2`); single- and pairwise Pauli-Z expectations `⟨Z_i⟩,⟨Z_iZ_j⟩` form the feature vector.
A **ridge head consumes these features concatenated with the HAR linear set**, so any
reservoir gain is genuine nonlinearity *beyond* HAR. The identical inputs feed the ESN,
isolating the quantum-vs-classical reservoir. Four mechanisms extend the core: a multi-scale
τ-bank; measurement feedback (RZ); regime-adaptive Ising↔Heisenberg switching driven by
BOCPD; and dissipation-as-feature (calibrated amplitude damping). For Phase 3 we add an
**encoding-density (data-re-uploading) path** so that added qubits carry *new* information
(§5.2), and a **sparse/tensor backend** that scales beyond exact statevector simulation
(§5.4). The engine is pure NumPy; an explicit PennyLane circuit reproduces it to ≈5×10⁻¹⁶
and compiles to a shallow ≈380-gate native circuit (20 Trotter layers).

## 3. Theoretical and analytical justification
The exploited quantum resources map to RV's structure: (a) **Hilbert-space dimensionality** —
n qubits give 2ⁿ amplitudes and O(n²) measured Pauli features at O(n²) parameter cost;
(b) **intrinsic nonlinearity** from fixed unitary evolution (no gradient training, no barren
plateaus); (c) **fading memory** (echo-state property) for stable forecasts; (d) **Hamiltonian
as inductive bias** (Ising↔Heisenberg). The central, falsifiable mechanism is **expressivity
scaling**, which we measure directly. The quantum kernel is non-reproducible by the matched
classical reservoir — geometric difference (Huang et al. 2021) **g(ESN→CHIMERA) ≈ 62** vs a
classical–classical control of ≈4 (`cli.py run kernel`). At 8–12 qubits the map is still
classically simulable, so this distinctness is *necessary, not yet sufficient*, for an
unconditional accuracy gain. **Phase 3 tests whether enriching the encoding converts that
distinctness into accuracy, and quantifies the classical-simulation cost via bond dimension.**

## 4. Data modeling strategy
**Datasets (all public).** Oxford-Man `.SPX` 5-minute realized variance, 2000–2020, 5,052
days incl. the 2008 GFC (Heber et al. 2009; via R packages `highfrequency`/`bvhar`); public
SPY daily OHLCV 2022–2026 (Garman–Klass proxy); and real MNIST (Keras `.npz` mirror) for the
common benchmark. **Preprocessing:** log-RV target; multi-horizon lags min-max scaled to
[0,1] on train only; HAR components in the readout; chronological train/validation/test
splits; per-model ridge selected on a validation tail; three-seed ensembling. **Baselines:**
HAR, GARCH(1,1), GJR-GARCH, AR(3), persistence, ESN (matched + 4×), LSTM. **Metrics:**
RMSE(log-RV), QLIKE (Patton 2011), Mincer–Zarnowitz R²; significance by Diebold–Mariano
(HLN-corrected) and the Model Confidence Set (Hansen–Lunde–Nason 2011).

## 5. Phase-3 execution — concrete results
**Pre-registration (honesty).** Before running, we fixed the confirm/refute thresholds in
`preregistration.py` (H0/H1/H4, transcribed from our Phase-2 §7). All outcomes below are
reported against them, including negatives. Headline numbers and wall-clock are in
`results/*_findings.md`; all reproducible via `cli.py`.

**5.1 The input-bottleneck mechanism (pre-registered negative).** With a *fixed* univariate
8-lag encoder, increasing n leaves the extra qubits without new input: g(n) and effective
feature-rank **saturate/decline** (n=8→12: g 125→31, D_eff 1.8→1.5) and crisis MZ does not
beat HAR. By our criteria **H0 is refuted in this regime** — and this is precisely the case
*for* enriching the encoding.

**5.2 Encoding density (Axis B) — the headline result.** We feed the extra qubits genuinely
new realized-measure information (signed return/leverage, downside-semivariance share, jump
share). At **n=10**, vs leaving those qubits idle, on the crisis window (GFC in test, 3 seeds):

| Model (n=10) | RMSE(log-RV) | MZ R² | DM vs HAR | DM vs matched-ESN |
|---|---|---|---|---|
| **CHIMERA (informed)** | **0.6123** | **0.630** | **−, p=0.004** | **−, p=0.018** |
| HAR | 0.6290 | 0.559 | — | — |
| ESN (same rich inputs) | — | 0.333 | n.s. | — |

CHIMERA **significantly beats both HAR and the matched ESN given identical inputs** — the
gain is quantum-specific (the ESN with the same features cannot beat HAR). Kernel distinctness
and rank jump vs idle qubits (g 52→158, D_eff 1.5→3.1). **H4 (effective-rank scaling) is
CONFIRMED** (D_eff grows 1.81→3.10→3.14 with n under informed encoding). *Honest limit:* the
advantage is **non-monotonic** (peaks at n=10, fades by n=12: g 158→88, MZ no longer beats
HAR), so the strictly pre-registered **H0 remains REFUTED** — it is the *quality* of added
information that matters, not raw qubit count. This is the first significant beat-HAR-on-RMSE
result in the project, and we report its limits rather than overclaiming.

**5.3 Common MNIST benchmark + noise.** Same engine, pixels→PCA(n)→n qubits→Pauli
readout→ridge. Accuracy **scales with qubits** (n=5/8/10/12: 0.632/0.798/0.831/0.859, 3
seeds), beats the linear-PCA baseline at every n (real nonlinear lift), and tracks a matched
ESN within ≈1% — validating **sufficient expressivity** (the benchmark's stated purpose).
**Noise (depolarizing & amplitude damping, rates 0.05–0.30):** the classifier is **invariant
to depolarizing noise** — a uniform Bloch contraction that per-feature standardization removes
exactly (accuracy identical to 4 decimals across all rates) — and **robust to amplitude
damping** (<0.5% change at 30%). This mechanistic robustness echoes the noise-as-feature
literature (Antoncich et al. 2026).

**5.4 Scaling frontier + quantum-complexity metric.** A sparse-exact backend
(`expm_multiply`, no dense propagator; verified to match the dense engine to **2.4×10⁻¹⁴**)
extends the study past the dense n=12 wall to **n=16 exactly** (the brief's upper range;
≈40 min/point on one CPU). For our **all-to-all** random-coupling reservoir we measure the
**bond dimension** χ_eff across a balanced cut: it is **full at every n, χ_eff = 2^(n/2)**
(16, 32, 64, 128, 256 for n = 8…16) — an exact MPS gets **zero compression** — while the
entanglement entropy grows (S ≈ 1.7 → 3.2 nats), so even an approximate MPS needs χ~e^S that
grows with n. Either way classical MPS cost rises with n: the reservoir is **genuinely hard
to simulate classically**, the precondition the advantage hypothesis needs. (Kernel
distinctness g under the *fixed* univariate encoder declines with n here — the same input
bottleneck as §5.1; the hardness result is encoder-independent, the distinctness result needs
§5.2's informed encoding.) See `figures/fig_tensor_complexity.png` / `results/tensor_findings.md`.

## 6. Quantum platform and resource planning
Simulator-first on qBraid: dense statevector ≤12 qubits (n=12 propagator build ≈ 7 min),
sparse/tensor-network to ≈16, GPU for larger. **QPU validation** uses the gate-Trotter
circuit (≈380 native gates, 20 layers; 2,000–8,000 shots/observable) on **IonQ / IQM / IBM**
via qBraid — native all-to-all / heavy-hex connectivity suits the fully-connected Ising
reservoir — with **ZNE (Mitiq) + measurement mitigation (mthree)** and a classical
cross-check for every hardware run. We characterize all four challenge axes: reservoir size
(§5.1/5.4), encoding density (§5.2), shot budget, and noise (§5.3). *(QCi Dirac-3 is the
separate optimization challenge's device, not this QRC track.)*

## 7. Stakeholder impact, milestone plan, AI disclosure
Earlier, more reliable volatility-regime-shift detection feeds portfolio hedging, dynamic
risk limits and derivatives pricing; in the $30B+ daily VIX-options market, marginal gains in
transition timing carry material P&L (JonesTrading). **Phase-3 milestone plan:** (i)
pre-register thresholds ✓; (ii) scaling + encoding-density sweeps ✓; (iii) common MNIST +
noise ✓; (iv) sparse/TN frontier + bond-dimension ✓; (v) gate-Trotter QPU validation
(IonQ/IQM/IBM) — simulator cross-checked; fallback = TN + density-matrix noise emulation.
**AI disclosure:** Claude (Anthropic) assisted with code and drafting under the team's
direction; all formulations, decisions, and results are the team's own, produced by executing
team code on public data.

## References
Kornjača et al. 2024 (arXiv:2407.02553) · Zhu et al. 2025 (PRR 7, 023290) · Ahmed, Tennie &
Magri 2025 (Proc. R. Soc. A 481) · Li et al. 2025 (arXiv:2505.13933) · Tandon et al. 2025
(arXiv:2505.22837) · Hou et al. 2026 (PRL; arXiv:2508.12383) · Čindrak et al. 2026
(arXiv:2603.21371) · Antoncich et al. 2026 (arXiv:2602.14641) · Kobayashi & Motome 2026
(PRL 136, 040602) · Huang et al. 2021 (Nat. Commun. 12, 2631) · Corsi 2009 · Patton 2011 ·
Hansen, Lunde & Nason 2011 · Diebold & Mariano 1995 · Bollerslev 1986 · Jaeger 2001 ·
Heber, Lunde, Shephard & Sheppard 2009.
