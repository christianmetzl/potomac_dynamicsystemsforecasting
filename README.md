# CHIMERA-QRC — Regime-Aware Quantum Reservoir Computing for S&P 500 Realized Volatility

**Team EIGENNEXUS** · Global Industry Challenge 2026 (qBraid · MITRE · JonesTrading) · **Track A — Financial Volatility**
Christian Metzl (Lead / Architect) · Fares Eldibani (Data Science) · Juan Manuel Aguiar Hualde (PhD Physics)

[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_white.png" width="150">](https://account.qbraid.com/?gitHubUrl=https://github.com/christianmetzl/potomac_dynamicsystemsforecasting.git&redirectUrl=LAUNCH_ME.ipynb)

> One-command, offline, agent-reproducible. `pip install -r requirements.txt && python3 cli.py reproduce`

---

**License.** Proprietary — free to view, clone, and execute **for GIC 2026 judging and results
verification only**; any other use, commercial or otherwise, requires the team's written
permission (see `LICENSE`). Bundled datasets keep their own terms.

## The one-paragraph version

We built the **evaluation instrument** most quantum-ML work is missing — pre-registered,
adversarially-controlled, and **reproducible offline in one command** (`python3 cli.py verify`), with
every hardware prediction **hash-committed to a prior commit before the data existed**. Run across
**four devices from three QPU vendors** (IonQ, IQM, Rigetti), it yields two measurement assets that
stand on their own — an empirical **quantum-complexity metric** (`χ_eff ≈ 2^(n/2)`, marking the
classical-simulability boundary) and a cross-platform **coherence-budget wall** that separates
coherent circuit error from depolarizing/damping noise — and one honest verdict: **at
classically-simulable scale (≤16 qubits) the quantum reservoir is *distinct but not more accurate*
than the strongest fair baseline, HAR-X**, robust across a second (Heisenberg) reservoir family and a
second (weather) domain. Our own program **falsified four of its own pre-registered predictions**
under controls. The negative is the finding; the reusable audit machinery and the two instruments are
the assets. *A browser replay of the whole audit, plus these core findings, is in
[`docs/verify_replay.html`](docs/verify_replay.html).*

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

**Run on qBraid, step by step:**
1. Click **Launch on qBraid** at the top of this README — qBraid clones this repository into
   your qBraid Lab workspace and opens `LAUNCH_ME.ipynb` (Run All = install + full audit).
2. Alternatively, open a terminal in the cloned repository directory.
3. `pip install -r requirements.txt` — Python 3.9+ (results generated on 3.11); CPU-only,
   no GPU, no other system dependencies.
4. `python3 cli.py verify` — the one-command offline integrity audit (engine tests, QASM
   self-test, credit reconciliation, bootstrap CIs, noise fingerprint; ~2–5 min), or
   `python3 cli.py headline --quick` for the ~10-minute Phase-3 story.
5. Optional full pass: `python3 reproduce.py`. Everything runs offline — no API key, credits,
   or accounts needed (optional QPU re-execution via `qpu_run.py` is the sole exception).

**Compute environment.** All classical computation is CPU-only (pure NumPy/SciPy) — **no GPU is
used or required** anywhere in this repository. The committed results were generated on a 4-core
Intel Xeon @ 2.10 GHz container; everything reproduces on laptop-class hardware, and the only
non-CPU compute is the 13 QPU campaigns themselves (IonQ Forte-1, IQM Garnet/Emerald, Rigetti
Cepheus-1-108q via qBraid). GPU statevector simulation is a scaling option beyond n≈16 (§ paper
5.5), not something any reported number depends on.

**⏱ ~10-20-minute judge verification (recommended first run; depends on core count):**
```bash
pip install -r requirements.txt
python3 cli.py headline --quick   # the Phase-3 story: prereg → decisive test → canonical
                                  # baselines → MNIST → frontier (~5-10 min; verdicts match
                                  # the full runs; authoritative numbers: results/*_findings.md)
```

**Full reproduction:**
```bash
python3 reproduce.py             # full Phase-2 + Phase-3 reproduction (~1-2 hr)
python3 reproduce.py --quick     # fast full pass; python3 reproduce.py headline --quick = the 10-min check
python3 cli.py list              # all reproducible actions (agent-executable Skill)
```
`reproduce.py` is a thin wrapper over `cli.py` (the Skill driver); either works, or run any
script directly, e.g. `python3 scaling_sweep_axisB.py`.

**Everything reproduces offline** — all datasets required for the results are committed under
`data/` and `v{2,3}_research/` (provenance below), so no qBraid account, credits, or network are
needed to reproduce. The real-QPU campaigns are committed *evidence* (job IDs + counts, verified
via qBraid's platform records and re-derived by `cli.py run credit_audit` / `qpu_bootstrap`),
not re-executed by reproduction.

The **qBraid Skill** (`cli.py` + `qbraid_skill.yaml` + `SKILL.md`) is the agent-executable
interface required by the brief: an AI agent can enumerate actions, configure the reservoir,
run training, and reproduce every headline number end-to-end.

**Evidence map:** `results/OVERALL_QRC_CONCLUSION.md` tabulates every independent fair test
in this project (12+ rows: volatility, weather×5 stations, VPT static/recurrent, capacity,
efficiency frontier, noise, quantum-data) with its verdict and artifact — the one-page view
of why the honest negative is domain-, metric-, and architecture-general.

**One-command integrity audit:** `python3 cli.py verify` runs — and *asserts* — the full
self-check suite offline: engine tests, QASM=reservoir self-test, whole-program credit
reconciliation, shot-noise bootstrap CIs, and the coherent-vs-damping noise fingerprint.
Prefer not to run it? Open `docs/verify_replay.html` in any browser — a self-contained, offline
replay of an *actual* `cli.py verify` run (28 numbered checks, each with its real measured value <
threshold; 28/28 PASS) plus the paper's core findings. Nothing hand-typed. For
the objections a skeptical reviewer will raise (weather in a finance paper, 500 vs 4k shots,
the depolarized-limit argument, day-drift, data access, run authenticity), see
`results/ANTICIPATED_OBJECTIONS.md` — each answered with a pointer to committed evidence.

## Expected inputs & outputs

**Inputs (all bundled or auto-fetched; nothing to configure):** public datasets ship in
`data/` (S&P 500 realized variance, NOAA weather stations, seeded MNIST subset — provenance
below); every script runs offline from the repo root with only `requirements.txt` installed.
No API keys, accounts, or external services are needed for reproduction. (Optional QPU
re-execution via `qpu_run.py` is the one exception: it needs a qBraid API key and credits;
the `openquantum:` device route additionally needs a linked OpenQuantum account.)

**Outputs:** each script prints its verdicts to stdout and writes (i) a `*_results.npy`
array bundle and (ii) a human-readable `results/*_findings.md` with the headline numbers.
The committed `results/` files are the authoritative full-run numbers; `--quick` runs
regenerate the same *verdicts* at reduced seeds/sizes in ~10 min. Hardware campaign outputs
(`results/qpu_run_hw_*.json` + per-job IDs) are committed as executed — QPU runs are
inherently non-rerunnable bit-for-bit, so judges verify them via the platform job records
listed in `results/CREDIT_BUDGET.md`.

## Known limitations & assumptions

The paper's §7 states these plainly; the load-bearing ones:
1. **No quantum advantage at simulable scale** — HAR-X (classical, linear) is the best
   volatility model in every fair test; the QRC is competitive-not-better. This is the
   honest headline, not a caveat.
2. RV sample ends Feb-2020 (the 2008 GFC is in the crisis *test* split; COVID just outside); broader assets/periods are
   daily-proxy supporting studies (`v2_research/`, same negative), not 5-min RV.
3. Simulation noise is per-layer single-qubit channels (depolarizing, amplitude damping,
   readout); combined noisy-circuit-plus-shot execution lives in the hardware campaigns.
4. Hardware point values carry measured day-scale drift (~0.04 on superconducting devices);
   regime statements (signal-bearing vs scrambled vs the depolarized limit) are the robust
   currency — see `results/qpu_hardware_findings.md`.
5. Efficiency/capacity results assume the documented run configurations; the information-
   processing-capacity gap g is regularization-dependent (qualitative, not quantitative).

---

## Headline results (all script-backed; honest, pre-registered)

We pre-register the falsifiable thresholds in `preregistration.py` (transcribed from the
Phase-2 paper §7) **before** running, and report outcomes against them — including negatives.

### 1. The decisive test — and an honest negative (Axis B, hardened)
`python3 cli.py run axisB_rig` → `results/axisB_rigorous_findings.md`

We compare the quantum reservoir to the strongest *fair* baselines — **HAR-X** (the same
leverage/semivariance/jump features used **linearly**, no reservoir), a **true recurrent ESN**,
and an **RFF kernel** — all sharing identical inputs, with **8 seeds, HAC-corrected
Diebold–Mariano, two windows (crisis + calm), and Holm correction**:

| RMSE(log-RV) | HAR-X | recurrent ESN | RFF | CHIMERA | best |
|---|---|---|---|---|---|
| crisis n=10 | 0.6034 | **0.5996** | 0.6047 | 0.6074 | ESN |
| crisis n=12 | **0.5906** | 0.6023 | 0.5964 | 0.6031 | HAR-X |
| calm n=10 | **0.6244** | 0.6445 | 0.6264 | 0.6291 | HAR-X |

**HAR-X is best or co-best everywhere; CHIMERA never beats it, and after Holm correction no
comparison is significant.** An earlier draft reported "CHIMERA beats HAR (p=0.004)" — our own
adversarial review found that was an artifact of comparing against a *feature-poor* HAR; the
gain came from the encoded realized measures (a known SHAR/HARQ effect), **not** from quantum
nonlinearity. **By our pre-registered criteria, H0 is refuted — we report this honestly.**
What survives for the quantum reservoir: it is *competitive* (within ≈0.8–2.1% RMSE), **lower seed variance
than the ESN in 3 of 4 cells** (no cell individually significant), and beats the recurrent ESN on the calm window (raw
p=0.018). The encoding-density *mechanism* is real (informed qubits restore g 52→158, D_eff
1.5→3.1 vs idle), but distinctness is **necessary, not sufficient** for advantage.

### 2. The input-bottleneck mechanism
`python3 cli.py run scaling` → `results/scaling_sweep_findings.md`

With a *fixed* univariate-lag encoder, adding qubits does **not** help — g(n) and effective
rank saturate (idle qubits carry no new information). This pre-registered negative is the
empirical case *for* the informed encoding tested in §1.

### 3. Common MNIST benchmark (cross-team expressivity)
`python3 cli.py run mnist` → `results/mnist_findings.md`

Accuracy grows with qubits (0.63 → 0.86 for n = 5 → 12); CHIMERA beats the linear-PCA
baseline at every n (real nonlinear lift) and a matched ESN **ties or slightly exceeds** it
(within ~1% for n≥8; 2.9% at n=5) — i.e. the quantum reservoir has **sufficient expressivity**
(the benchmark's stated purpose), not dominance. Noise: the classifier is **invariant to
depolarizing** noise (a uniform Bloch contraction that feature-standardization removes exactly)
and **robust to amplitude damping** (<0.5% at 30%).

### 4. Scaling frontier + quantum-complexity metric
`python3 cli.py run tensor` → `results/tensor_findings.md`

A sparse-exact backend (`expm_multiply`, no dense propagator; matches the dense engine to
2.4×10⁻¹⁴) reaches **n=16 exactly**. We measure the **entanglement / bond dimension** of the
random ≈50%-connected reservoir across a balanced cut: χ_eff is **essentially full at every n**
(exactly 2^(n/2) at n=8–14; **255.9 of 256** at n=16) — an exact MPS gets zero compression — so there is **no low-bond-dimension
shortcut** and exact simulation cost stays exponential in n. (Full entanglement is a *necessary,
not sufficient* condition for true classical hardness — the precondition any beyond-frontier
advantage would need; no advantage is observed at the simulable scale here.)

### 5. Phase-2 results (reproduced)
`python3 cli.py run phase2` (+ `crisis`) — kernel geometry g(ESN→CHIMERA) ≈ 64 vs ≈ 3.7 control;
explicit PennyLane circuit matches the engine to ≈ 3.9×10⁻¹⁶. CHIMERA-3scale tracks the crisis
regime on forecast efficiency (MZ R² 0.591 vs **plain** HAR 0.559) — *but note this is vs
feature-poor HAR; the decisive HAR-X test (§1) shows no significant advantage*, so this is a
regime-tracking property, not a win.

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
results/AUDIT_ECONOMICS.md              the audit instrument in dollars: measured cost vs. what it caught
docs/EIGENNEXUS_desk_briefing.pptx      customer-facing desk briefing (generator: docs/build_desk_briefing.js)
```

## Data provenance (all public; no proprietary data)

- **Oxford-Man Realized Library `.SPX` 5-min realized variance**, 2000-01 → 2020-02 incl. the
  2008 GFC (Heber, Lunde, Shephard & Sheppard 2009; redistributed via the R packages
  `highfrequency` and `bvhar`). Bundled in `data/oxfordman_spx_full.csv`. *Note: the sample ends
  2020-02-21, just before the COVID shock; the 2020 COVID regime is tested separately in V2
  (`v2_research/`, daily-proxy panel) — same no-advantage result.*
- **SPY daily OHLCV 2022–2026** — public end-of-day data (Stooq/Yahoo), retrieved via
  Massive.com/Polygon; Garman–Klass proxy. Bundled in `data/massive_spy_daily.csv`.
- **MNIST** — fetched once from the public Keras `.npz` mirror; a seeded subset is cached in
  `data/mnist_subset.npz` for offline runs.

## Hardware execution (Phase 3 — EXECUTED)

**Thirteen executed (ten org-funded + three free-credit S7) provenance-tagged QPU campaigns across three vendors / four devices** (IonQ Forte-1,
IQM Garnet, IQM Emerald, Rigetti Cepheus-1) — every campaign pre-registered (manifest +
amendments with decision rules committed *before* execution), budget-audited to the credit
(`results/CREDIT_BUDGET.md`), and scored against predictions committed in advance:

- **IonQ Forte-1** (trapped-ion, n=8): raw feature error **0.104 — signal-bearing** (below the
  0.196 depolarized limit; prediction (ii) confirmed). Bonus finding: a 2,000-gate/circuit
  device ceiling measured on the native route and corroborated (via an ambiguous platform failure) on the OpenQuantum route → ZNE infeasible there (disclosed fallback).
- **IQM Garnet** n=10 / n=12: **0.159 / 0.190 — signal-bearing**, while a same-session n=8
  anchor stayed scrambled (0.222) — a real effect, drift excluded (S1/S2 refuted). A later
  **cross-seed control (S7)** localized it: it is **seed-0-instance-specific, not a size law**.
- **IQM Emerald** (newer generation) at n=8: **0.169–0.179 — signal-bearing at the very size
  Garnet scrambles**, reproduced in a same-window two-chip pair (S3b refuted high).
- **Instance ensemble (`cli.py run instance_ensemble`)**: across 30 seeded n=8 instances, the
  **scrambled** seed-0 graph is among the *sparsest* (11 two-qubit couplings, 13th pctile) while
  **signal-bearing** seed-1 is among the *densest* (18, 90th) and faced a *tighter* limit —
  on the two instances measured on metal, **entangling-gate count anti-predicted the outcome**. Exact and offline; an ensemble
  characterization, not extra hardware — **exploratory, post-hoc, not pre-registered**
  (`results/instance_ensemble_findings.md`).
- **Garnet / Rigetti** at n=8: 0.222–0.261 across six runs and four days — the **characterized
  negative** that anchors the contrast. It is stable *for the seed-0 instance*: an independent
  **seed-1 n=8 instance on the same chip, same session, is signal-bearing at 0.159** (S7), which
  is why we claim an instance property rather than a size law.

Full detail: `results/qpu_hardware_findings.md` · pre-registration:
`results/qpu_campaign_manifest.md`, `results/qpu_scaling_outlook.md`. The simulator path
remains one command (`python3 cli.py run qsubmit`; exact circuit vs engine = 3.9×10⁻¹⁶).
*(QCi Dirac-3 is the separate optimization challenge's device, not this QRC track.)*

## AI collaboration disclosure

Claude (Anthropic) assisted with code and drafting under the team's direction. All
formulations, design decisions, and results are the team's own and were produced by executing
team code on public data.
