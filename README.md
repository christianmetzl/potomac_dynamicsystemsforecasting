# CHIMERA-QRC — Regime-Aware Quantum Reservoir Computing for S&P 500 Realized Volatility

**Team EIGENNEXUS** · Global Industry Challenge 2026 (qBraid · MITRE · JonesTrading) · **Track A — Financial Volatility**
Christian Metzl (Lead / Architect) · Fares Eldibani (Data Science) · Juan Manuel Aguiar Hualde (PhD Physics)

[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_white.png" width="150">](https://account.qbraid.com/?gitHubUrl=https://github.com/christianmetzl/potomac_dynamicsystemsforecasting.git)

> One-command, offline, agent-reproducible. `pip install -r requirements.txt && python3 cli.py reproduce`

---

## What this is

CHIMERA-QRC is a delay-embedding **quantum reservoir**: lagged log realized-variance
values are angle-encoded (`RY(π·x)`) onto qubits, evolved under a fixed transverse-field
Ising Hamiltonian `U = exp(−iHτ)`, and read out as single + pairwise Pauli-Z expectations
(`⟨Z_i⟩, ⟨Z_iZ_j⟩`) into a **linear ridge head that already contains the HAR information
set** — so any reservoir gain is genuine nonlinearity *beyond* HAR, not missing linear
structure. The same engine runs the challenge's common **MNIST** benchmark.

The core engine is **pure NumPy** (no Qiskit/PennyLane needed for the science; PennyLane
only for the explicit-circuit SDK demo). All data is bundled, so everything runs offline.

## Quickstart

```bash
pip install -r requirements.txt
python3 cli.py list              # all reproducible actions (agent-executable Skill)
python3 cli.py run headline      # the Phase-3 story
python3 cli.py reproduce         # full Phase-2 + Phase-3 reproduction
```
or run any script directly, e.g. `python3 scaling_sweep_axisB.py`.

The **qBraid Skill** (`cli.py` + `qbraid_skill.yaml` + `SKILL.md`) is the agent-executable
interface required by the brief: an AI agent can enumerate actions, configure the reservoir,
run training, and reproduce every headline number end-to-end.

---

## Headline results (all script-backed; honest, pre-registered)

We pre-register the falsifiable thresholds in `preregistration.py` (transcribed from the
Phase-2 paper §7) **before** running, and report outcomes against them — including negatives.

### 1. The Phase-3 win — informed encoding (Axis B), crisis window
`python3 cli.py run axisB` → `results/scaling_axisB_findings.md`

At **n=10**, encoding *leverage + downside-semivariance asymmetry* on the 2 extra qubits
(vs leaving them idle):

| | CHIMERA (n=10, informed) | HAR | matched ESN (same inputs) |
|---|---|---|---|
| RMSE (log-RV) | **0.6123** | 0.6290 | — |
| MZ R² | **0.630** | 0.559 | 0.333 |
| Diebold–Mariano | **beats HAR, p=0.004** | — | **beats ESN, p=0.018** |

The quantum reservoir **significantly beats both the econometric gold standard (HAR) and the
classical reservoir (ESN) given identical inputs** — the gain is quantum-specific. **H4
confirmed** (effective rank grows with qubits under informed encoding). Honest limit: the win
is **non-monotonic** (peaks at n=10, fades by n=12), so the strictly pre-registered **H0
remains refuted** (g is not monotone). It is the *quality* of added information that matters.

### 2. The input-bottleneck mechanism
`python3 cli.py run scaling` → `results/scaling_sweep_findings.md`

With a *fixed* univariate-lag encoder, adding qubits does **not** help — g(n) and effective
rank saturate (idle qubits carry no new information). This pre-registered negative is the
empirical case *for* Axis B.

### 3. Common MNIST benchmark (cross-team expressivity)
`python3 cli.py run mnist` → `results/mnist_findings.md`

Accuracy grows with qubits (0.63 → 0.86 for n = 5 → 12); CHIMERA beats the linear-PCA
baseline at every n (real nonlinear lift) and tracks a matched ESN within ~1% — i.e. the
quantum reservoir has **sufficient expressivity**, the benchmark's stated purpose. Noise:
the classifier is **invariant to depolarizing** noise (a uniform Bloch contraction that
feature-standardization removes exactly) and **robust to amplitude damping** (<0.5% at 30%).

### 4. Scaling frontier + quantum-complexity metric
`python3 cli.py run tensor` → `results/tensor_findings.md`

A sparse-exact backend (`expm_multiply`, no dense propagator; matches the dense engine to
2.4×10⁻¹⁴) pushes past the dense n=12 wall toward n≈16. We measure the **entanglement /
bond dimension** of the all-to-all reservoir across a balanced cut: χ_eff grows toward its
2^(n/2) ceiling — i.e. classical MPS cost (~χ²) heads for the wall, the precondition the
quantum-advantage hypothesis needs.

### 5. Phase-2 results (reproduced)
`python3 cli.py run phase2` — kernel geometry g(ESN→CHIMERA) ≈ 62 vs ≈ 4 control; crisis
MZ R² 0.591 > HAR 0.559; explicit PennyLane circuit matches the engine to ≈ 5×10⁻¹⁶.

### Classical baselines (brief-named)
HAR, GARCH(1,1), GJR-GARCH, AR(3), persistence (`cli.py run baselines`), ESN (matched + 4×),
and LSTM (`cli.py run lstm`, pure NumPy). On daily 5-min RV, HAR is the strong bar; the
LSTM does *not* beat it (honest expected outcome).

---

## Repository layout

```
cli.py / qbraid_skill.yaml / SKILL.md   agent-executable reproduction interface (qBraid Skill)
preregistration.py                      pre-registered H0/H1/H4 confirm-refute thresholds
qrc_engine.py                           pure-NumPy reservoir (Ising/Heisenberg, RY, RZ, noise)
delay_qrc.py / multiscale_chimera.py    delay-embedding + multi-scale τ-bank wrappers
classical_baselines.py                  Echo State Network (matched classical reservoir)
har_garch_baselines.py                  HAR-RV, GARCH/GJR-GARCH, AR(3), persistence
lstm_baseline.py                        LSTM baseline (pure NumPy, manual BPTT)
volatility_data.py                      Oxford-Man loader, supervised builder, splits
feature_pool.py                         rich realized-measure features (Axis-B encoder)
vol_fair_benchmark.py / vol_crisis_benchmark.py   Table 1 / regime-transition benchmarks
kernel_analysis.py                      kernel geometry (g, KTA, effective dim)
sdk_demo.py                             explicit PennyLane circuit + Trotterisation
scaling_sweep.py                        H0 curves: g(n), MZ-gap(n), rank(n) + noise
scaling_sweep_axisB.py                  Axis-B head-to-head (informed vs idle qubits)
mnist_benchmark.py                      common cross-team MNIST benchmark (+ noise curve)
tensor_backend.py                       sparse/TN frontier + bond-dimension complexity
data/                                   Oxford-Man RV, SPY 2022-26, MNIST subset (all public)
figures/  results/                      generated figures + findings write-ups
```

## Data provenance (all public; no proprietary data)

- **Oxford-Man Realized Library `.SPX` 5-min realized variance**, 2000–2020 incl. the 2008 GFC
  (Heber, Lunde, Shephard & Sheppard 2009; redistributed via the R packages `highfrequency`
  and `bvhar`). Bundled in `data/oxfordman_spx_full.csv`.
- **SPY daily OHLCV 2022–2026** — public end-of-day data (Stooq/Yahoo), retrieved via
  Massive.com/Polygon; Garman–Klass proxy. Bundled in `data/massive_spy_daily.csv`.
- **MNIST** — fetched once from the public Keras `.npz` mirror; a seeded subset is cached in
  `data/mnist_subset.npz` for offline runs.

## Hardware plan (Phase 3)

Simulator-first: dense statevector ≤12 qubits, sparse/TN to ~16. QPU validation uses the
gate-Trotter circuit (`sdk_demo.py`, ~380 native gates) on **IonQ / IQM / IBM** via qBraid,
with ZNE (Mitiq) + measurement mitigation (mthree) and a classical cross-check for every
hardware run. *(QCi Dirac-3 is the separate optimization challenge's device, not this QRC
track.)*

## AI collaboration disclosure

Claude (Anthropic) assisted with code and drafting under the team's direction. All
formulations, design decisions, and results are the team's own and were produced by executing
team code on public data.
