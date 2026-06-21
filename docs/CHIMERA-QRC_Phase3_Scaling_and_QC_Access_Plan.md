# CHIMERA-QRC — Phase 3: Scaling-Study Design & QC-Access Plan

**Team EIGENNEXUS · Global Industry Challenge 2026 · Track A (Financial Volatility)**
*Working draft for team review — finalize against the official Phase 3 spec (live on Aqora end of week).*

---

## 0. The one-sentence thesis

At 8 qubits we proved the quantum reservoir is **measurably distinct** from its matched classical counterpart (geometric difference *g* ≈ 62 vs 4.3 control) and **parameter-efficient** (matched-feature MCS membership, best regime-transition tracking) — Phase 3 tests the single open question that follows: **does that distinctness become a *forecasting-accuracy* advantage as we scale to where classical simulation fails?** Everything below is built to answer that as a falsifiable experiment, not a demo.

---

## 1. Central hypothesis (H0) and what would confirm or refute it

**H0.** The measured parameter-efficiency + kernel-distinctness gap at 8 qubits becomes a forecasting-accuracy gap at neutral-atom scale, in the regime where exact classical simulation is infeasible.

**Confirmation criteria (both must hold, out-of-sample, walk-forward):**
1. The geometric difference *g(ESN → CHIMERA)* **keeps growing** with qubit count *n* (does not saturate), and
2. The **regime-transition Mincer–Zarnowitz R² gap over HAR turns positive and statistically significant** (DM / MCS) at a scale beyond the exact-simulation frontier (≈28–30 qubits).

**Refutation criteria (either kills the thesis honestly):**
- *g* saturates or plateaus as *n* grows (distinctness was a small-system artifact), **or**
- the MZ-R² gap over HAR stays ≤ 0 out-of-sample even at scale (distinctness never converts to skill).

We commit to reporting refutation as a finding. A clean "no" at 80 qubits is a real scientific result about the limits of QRC for volatility, and more credible than an over-claimed "yes."

---

## 2. The three scaling axes

Scaling qubit count alone is a trap: with our current 8-lag input, qubits beyond 8 would re-process the same eight degrees of freedom. **System size must scale in lockstep with input information and measurement budget.** Three coupled axes:

### Axis A — System size (qubit count *n*)
The primary axis. Stages chosen around the classical-simulability frontier so the experiment straddles "checkable" and "hard":

| Stage | *n* | Compute | Why this stage |
|---|---|---|---|
| S1 | 8 | exact statevector | reproduce Phase-2 baseline; sanity anchor |
| S2 | 12–16 | exact statevector | first scaling signal; still fully checkable |
| S3 | 20–28 | statevector (GPU) | upper edge of exact simulation |
| S4 | 30–50 | tensor-network (MPS) | **frontier**: bond dimension must grow → complexity signal |
| S5 | 50–80 | tensor-network (GPU) | beyond comfortable classical reach |
| S6 | 80–256 | **QPU (neutral-atom)** | classically hard; the advantage test |

### Axis B — Encoding density (the input-bottleneck fix)
Each added qubit must carry *new* information. Encoding richness scaled with *n*:

- **n ≤ 16:** univariate RV lags (extend the 8-lag set) + realized-semivariance / signed-jump / bipower-variation components (RV decomposed into its informative parts).
- **n = 20–32:** add a **multivariate panel** — sector-ETF and index RV (e.g. SPY + XLF/XLK/XLE + VIX term structure), so the reservoir sees cross-asset volatility co-movement (the structure HAR cannot represent).
- **n = 50–256:** full multivariate RV panel **+ data re-uploading** — re-inject the input at multiple points in the evolution so a large reservoir processes the input richly rather than diluting it. Data re-uploading is the lever that lets physical qubit count exceed raw input dimension *and still encode new degrees of freedom* (depth of feature interaction, not just width).

**Refutation hook for Axis B:** if effective feature-rank saturates as *n* grows (measured via the kernel's spectrum), the architecture is input-bound, not size-bound — we report that.

### Axis C — Reservoir & measurement budget
- **Evolution time / multi-scale τ-bank:** sweep τ and the number of scales; locate the edge-of-chaos operating point (Kobayashi & Motome 2026) as a function of *n*.
- **Hamiltonian family:** Ising ↔ Heisenberg-XXZ switching (regime-adaptive, BOCPD-driven) — confirm the switch still helps at scale.
- **Readout:** ⟨Zᵢ⟩ + ⟨ZᵢZⱼ⟩ = O(n²) observables; characterize how **shot budget** must grow with *n* for stable features, and test a truncated/​sampled-pair readout to control measurement cost.
- **Noise:** treat calibrated dissipation as a *tunable feature* (Innovation 4) — test whether hardware noise / amplitude damping aids generalization (Antoncich 2026) rather than only degrading it.

---

## 3. Metrics & adjudication

**Forecasting skill** (the bottom line): RMSE(log-RV), QLIKE, and especially the **regime-transition Mincer–Zarnowitz R² gap over HAR**. Significance via HLN-corrected Diebold–Mariano and the 95% Model Confidence Set. Walk-forward / expanding-window out-of-sample throughout.

**Quantum-distinctness** (the mechanism, tracked vs *n*): geometric difference *g* (Huang et al. 2021), residual kernel-target alignment (post-HAR), effective feature-rank, and Fisher-information capacity. These test the "*g* keeps growing" prong directly and are computable on simulators up to S5.

**The classical-simulability frontier** (made explicit): for every run we record the resource needed to simulate it classically — statevector memory at small *n*, and **MPS bond dimension χ** at S4–S5. A rising χ that tracks rising forecasting skill is the cleanest evidence that the advantage lives in genuinely quantum correlations. We publish the frontier curve.

---

## 4. Compute strategy: simulator-first backbone + targeted QPU

All on **qBraid** (the challenge's official platform), which gives one-line vendor-agnostic submission and pre-configured access to the QPUs and GH200 GPUs below.

### 4a. Simulation backbone — the de-risked spine (carries the science even with zero hardware time)
- **Exact statevector** (PennyLane-Lightning / qsim) for S1–S3 (≤ ~28 qubits).
- **Tensor-network / MPS** (quimb, PennyLane MPS) for S4–S5 (30–80 qubits), with **bond dimension as a tracked complexity metric**.
- **GPU acceleration** on qBraid's **NVIDIA GH200 Grace-Hopper** nodes (cuQuantum / lightning.gpu) for the large statevector and TN contractions.

The entire H0 simulator-side test (does *g* grow, does the MZ gap open through S5?) runs here. **Hardware is confirmatory, not load-bearing.**

### 4b. QPU access — hardware-agnostic, with two strong architecture matches
We map the *same* reservoir onto whichever QPU we're granted; two are especially well-suited:

- **QuEra Aquila — neutral-atom, analog Rydberg (PREFERRED).** Up to **256 atoms** via qBraid's Braket integration. The Rydberg Hamiltonian (blockade ZZ-type interaction + transverse Rabi drive) **natively realizes our fixed transverse-field Ising reservoir with no gate compilation** — we program the evolution directly. This is the only path that reaches classically-hard scale (S6) *and* matches the architecture. Primary Phase-3 hardware target.
- **Quantinuum (H-series) — trapped-ion, gate-based.** 56 qubits, all-to-all connectivity, **native arbitrary-angle ZZ gates** (exactly our Trotter primitive — the verified ~380-gate, 20-layer circuit compiles almost 1:1), 99.91% two-qubit fidelity, **and mid-circuit measurement** (which directly enables our RZ measurement-feedback innovation). Best high-fidelity mid-scale (S3–S4) validation.
- **IonQ (Forte) — trapped-ion, all-to-all.** Alternative gate-based mid-scale validation; suits the fully-connected Ising coupling.
- **Superconducting (IBM/Rigetti/IQM) — heavy-hex/grid.** Usable with SWAP routing for all-to-all; larger qubit counts; gate-based runs with heavier error mitigation.

### 4c. Error mitigation & the cross-check protocol (non-negotiable)
Every hardware run is paired with: **zero-noise extrapolation** (Mitiq) + **measurement-error mitigation** (mthree), and a **classical-simulation cross-check** wherever the size still permits one (≤ S5). No hardware number is reported without either a simulator cross-check or an explicit "beyond-simulation" flag.

### 4d. Fallback
If QPU queue time or fidelity is the binding constraint, the **TN + density-matrix noise emulation** path delivers the full scaling claim; hardware runs then serve as a fidelity/feasibility demonstration rather than the core evidence. The thesis is never hostage to a hardware queue.

---

## 5. Phased plan with refutation gates

**Phase A — Simulator scaling sweep (S1→S5). The decisive test.**
Sweep Axis A × Axis B × Axis C on statevector→TN→GPU. Produce the two H0 curves: *g* vs *n*, and MZ-gap-over-HAR vs *n*.
→ *Gate:* if *g* saturates or the gap fails to open by S5, we report a negative/limited result and reframe Phase-3 scope honestly. If both trend favourably, proceed.

**Phase B — Hardware validation at mid-scale (S3–S4) on Quantinuum/IonQ.**
Run the verified gate-based circuits; test (i) that features survive real noise within mitigation, (ii) the measurement-feedback innovation via mid-circuit measurement, (iii) noise-as-feature.
→ *Gate:* features must agree with the simulator cross-check within mitigation error.

**Phase C — Classically-hard frontier on QuEra Aquila (S6).**
Run the analog reservoir at 80–256 atoms — beyond comfortable classical reach — and evaluate forecasting skill + the distinctness metrics at a scale where the kernel is not classically reproducible.
→ *Gate:* the advantage thesis stands or falls here; either outcome is reported.

---

## 6. Risks & mitigations (honest)

| Risk | Mitigation |
|---|---|
| **Input bottleneck** — 8 DOF can't justify 256 qubits | Axis B: multivariate panel + data re-uploading; feature-rank tracked as a refutation hook |
| **Hardware noise destroys features** | ZNE + mthree; simulator cross-check; noise-as-feature reframing (may *help*) |
| **Classical simulability creeps up** (better TN) | Publish the bond-dimension frontier; claim advantage only where χ is demonstrably intractable |
| **QPU queue / cost limits** | Simulator-first backbone carries the science; hardware is confirmatory; fallback to TN + noise emulation |
| **Over-claiming** | Pre-registered confirm/refute thresholds; commit to reporting a negative result |

---

## 7. Expected outcomes & honest prior

The kernel result makes a scaling advantage **plausible** — a provably distinct, parameter-efficient feature map that is orthogonal to HAR's linear structure is exactly the precondition for advantage. It does **not** make it certain: the input is low-dimensional and the targets are ones HAR already handles well on calm data. Our honest prior is that the **regime-transition / multivariate** setting is where an advantage is most likely to appear first (turbulent, cross-asset, nonlinear), and calm univariate point-RMSE is where it is least likely. Phase 3 is designed to find the boundary and report it either way.

---

## 8. Deliverables mapping (Phase 3)

| Phase-3 deliverable | Status / plan |
|---|---|
| Technical paper (longer) | extend Phase-2 paper with the scaling results + frontier curves |
| **Executable qBraid repository** | harden the existing repo: qBraid-SDK entry points, `qbraid` job submission wrappers, GH200 TN configs |
| **Agent-reproducible package** | already built (`run_all.sh`, README claim→script map); add the scaling-sweep driver |
| **qBraid "Skill"** | structured, agent-runnable artifact wrapping the sweep + hardware-submission flow |

---

### Immediate next actions (spec-independent, doable now)
1. Build the **scaling-sweep driver** (`scaling_sweep.py`): parametrize *n*, encoding set, τ-bank; emit *g*(n) and MZ-gap(n).
2. Stand up the **multivariate / data-re-uploading encoder** (Axis B) and the **MPS backend** (Axis A, S4–S5).
3. Add **qBraid-SDK submission wrappers** + a tiny QuEra Aquila analog-Hamiltonian mapping smoke-test.
4. Lock the **pre-registered thresholds** (Section 1) into the repo so the experiment is honestly bounded before we run it.

*Finalize formatting, page limits, and any required sections once the official Phase 3 brief is live on Aqora.*
