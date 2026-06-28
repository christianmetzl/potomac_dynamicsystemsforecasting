# What we can conclude overall for Quantum Reservoir Computing (QRC)

*Cross-cutting synthesis of the whole project — V1 (Track A, realized-volatility submission), V2
(Track-A extensions), V3 (Track B, weather), and the methodological probes (capacity, frontier
scaling, noise, recurrence). Every claim below is tied to a script + saved artifact in this repo.
This document is a synthesis. The submitted Track-A paper is currently tag `v1.3-submission` (the
original zero-defect baseline is recoverable at `v1-submission`; tags v1.1–v1.3 surgically fold a few
fully-traceable supporting results — efficiency, recurrent mechanism, domain-generality — into it).*

## The one-sentence conclusion
**At classically-simulable scale (n ≲ 16 qubits), a unitary quantum reservoir is *competitive and
genuinely distinct* but **not more accurate** than a size-matched classical reservoir — across
domains, metrics, architectures, noise, and chaos regimes — and we can explain *why*, which makes the
negative a result rather than a null.**

## The evidence (each row is an independent, fair test we ran)

| # | test | setting | verdict | artifact |
|---|---|---|---|---|
| 1 | Realized-volatility forecast | S&P RV vs HAR-X + canonical HAR family (SHAR/HAR-CJ/HARQ/HEAVY) | CHIMERA ties best; no Holm-significant win; **no model beats HAR-X** | `canonical_baselines_findings.md` |
| 2 | Cross-asset / multi-horizon / crisis | 8–10 indices, GFC+COVID windows | competitive, **no advantage** | `v2_research/` |
| 3 | Weather temperature, **5 stations** | Jena+O'Hare+Denver/Rapid City/Great Falls (chaos +0…+78%) | CHIMERA ties/trails ESN at every horizon; **1 statistical tie, 0 wins** | `V3_README.md §Exp1` |
| 4 | Qubit-count scaling | weather n=5/10/15 | accuracy **improves** with n (0.864→0.692→0.677) yet still ties classical | `v3_weather_sweep_results.npy` |
| 5 | Information-processing capacity | Dambre 2012 probe, matched dim | CHIMERA nonlinear **2.77 < RFF 3.51 / ESN 2.89**; total 8.82 < 10.88/10.71 | `information_capacity_findings.md` |
| 6 | Representational frontier g(n) | fully-informed encoding to n=16 | g **declines** with n (93.6→42.4; ρ=−0.90); matched ESN keeps pace | `frontier_scaling_findings.md` |
| 7 | VPT, static reservoirs | Lorenz-63 autonomous rollout | CHIMERA 0.49 **< RFF 1.18** (matched); **no advantage** | `lorenz_vpt_results.npy` |
| 8 | VPT, **recurrent** QRC | Lorenz-63, fair size-match | CHIMERA 0.50 **< matched ESN 0.61**; closest it ever gets | `recurrent_qrc_results.npy` |
| 9 | VPT, recurrent QRC on **real weather** | Jena/Denver autonomous rollout | CHIMERA 6.5/8.1 h **< matched ESN 13.4/12.3 h**; fails to beat climatology at Jena | `recurrent_weather_vpt_*.npy` |
| 10 | Noise robustness | depol / amplitude-damping | readout-only = invariant (a standardization artifact); per-layer **degrades** | `noise_circuit_findings.md` |
| 11 | **Resource efficiency** (small QRC vs larger classical) | quality vs #features, input held fixed | CHIMERA saturates at ~0.85; RFF reaches 0.78, ESN 0.71 — comparable per-feature only at the smallest sizes; **a small QRC cannot do a larger classical's job** | `efficiency_frontier_findings.md` |
| 12 | **Quantum DATA** (purity / entanglement of input states) | inject quantum states, repeated | QRC **natively reads nonlinear state functionals** (beats classical-linear ≈0); classical-nonlinear w/ full tomography still matches/beats at 2-qubit scale | `quantum_data_outlook_findings.md` |
| 12b | **Quantum-data CROSSOVER** (k=2,3,4) | measurement complexity | QRC reads functionals from 1 setting vs **full-tomography** 3ᵏ, but the SOTA baseline is **classical shadows** (also efficient); budget-matched classical still edges the QRC at k≤4 — **open question, not a demonstrated advantage** | `quantum_data_crossover_findings.md` |

Twelve independent fair tests; on accuracy the quantum reservoir wins **none** of them. Its single
closest approach is one statistical tie (Rapid City h=1) and one near-match (recurrent Lorenz VPT
0.50 vs 0.61). Test 12 is the one place it shows a genuine *qualitative* capability classical-cheap
methods lack — see the outlook below.

## What we can therefore conclude — graded by confidence

**High confidence (multiply confirmed, mechanistically explained):**
1. **No accuracy advantage at simulable scale.** A unitary QRC with angle encoding + Pauli-Z readout
   does not beat a size-matched ESN/RFF on real forecasting (volatility *or* weather), on any metric
   we tested (RMSE, QLIKE, Mincer-Zarnowitz, VPT, information-processing capacity).
2. **It is not the task's fault.** The negative holds in the regime *most* favorable to a nonlinear
   reservoir — chaotic weather, 56–78% more unpredictable than a tame station — not just in
   linear-long-memory volatility. Domain-, metric-, architecture-, and chaos-regime-general.
3. **It is not a too-few-qubits artifact.** More qubits *do* help the quantum model (n=5→10→15
   monotone gain; D_eff and rank grow with n), yet a matched classical reservoir keeps pace — the
   representational gap g(n) *shrinks* toward the frontier rather than widening (ρ(n,g)=−0.90).
4. **At matched readout dimension the quantum reservoir is no more expressive.** Its
   information-processing capacity is in fact *lower* on every axis. The big Hilbert space does not
   translate into more *useful, learnable* nonlinear capacity from local Pauli readout at small n.

**Mechanism (why — a citable insight, not hand-waving):**
5. **Unitarity is a liability for autonomous dynamics.** Across Lorenz and real weather, the
   recurrent QRC learns the one-step map well (R² ≈ 0.92–1.0) yet its closed-loop rollout diverges
   fast — because norm-preserving unitary evolution lacks the *contraction* (dissipation) that gives
   classical ESNs their "generalized synchronization" and autonomous stability (the
   Ahmed-Tennie-Magri 2025 mechanism). This is structural, not a tuning failure.

**Resource efficiency (also negative — and directly relevant to the paper):**
6. **A small QRC cannot match a larger classical reservoir.** Tracing quality vs feature-count with
   the input held fixed, CHIMERA's accuracy *saturates* (~0.85 °C on the test task) while classical
   curves keep improving (RFF 0.78, recurrent ESN 0.71). Per feature the quantum and classical static
   maps are comparable — marginally favouring the quantum map only when features are very scarce — but
   that never compounds into doing a larger reservoir's job. No efficiency advantage either.

**The one genuinely promising direction — quantum data (verified capability, asymptotic edge):**
7. **On quantum data the QRC has a real qualitative capability classical-cheap methods lack.** It
   natively estimates *nonlinear functionals of an input quantum state* — purity (R² 0.75) and
   entanglement (0.50) — where a linear readout of the full state gives ≈0. **But the proper
   classical baseline is classical shadows** (Huang–Kueng–Preskill 2020), which are *also*
   measurement-efficient for low-degree functionals like purity; against full tomography the QRC
   needs 1 setting vs 3ᵏ, yet a budget-matched classical still edges it at k≤4 (crossover doc). So
   there is **no demonstrated quantitative advantage** — a genuine edge would require beating
   *shadows* on a shadows-hard functional, which we have not shown. The credible quantum-advantage
   frontier is therefore **many-qubit quantum-input / hardware-native tasks** (and, for dynamics,
   100+ qubit *dissipative recurrent* reservoirs; Kornjača 2024) — beyond exact simulation, and
   exactly the regime classical-data forecasting (both challenge tracks) never probes. We *verified
   the mechanism* that would drive it; we do not claim to have demonstrated the edge.

## The methodological takeaway (arguably the real contribution)
Much of the QRC literature reports advantages against **weak or non-size-matched** baselines. Under a
fair protocol — *nest the linear block so the quantum model must beat the linear span; size-match the
classical reservoir; require HAC-DM + Holm + MCS significance; report VPT/IPC; test across domains* —
the advantage disappears at simulable scale. **The disciplined evaluation is the deliverable.** An
honest, mechanistically-explained negative, reproducible end-to-end, is more credible and more useful
to the field than an overclaimed win.

## Scope / caveats (stated plainly)
- One reservoir family per paradigm (transverse-field Ising, fixed connectivity 0.5, angle encoding,
  Pauli-Z readout) — though we did vary encoding (data-reuploading / Axis-B), time-scale
  (multi-scale), and architecture (static vs recurrent).
- Exact simulation only (n ≲ 16 dense/sparse); the 100+ qubit regime is out of reach here.
- Classical-data tasks (volatility, weather) — not quantum-data or hardware-native settings.

## Bottom line for the submission
The CHIMERA-QRC work establishes a **robust, fair, mechanistically-grounded no-advantage result** for
unitary QRC on real-world forecasting at simulable scale — while pointing precisely at the one regime
(large-scale dissipative recurrence) where the question stays open. That honesty *is* the strength:
it is the kind of result a field can build on. Submission stays V1 (Track A), tag `v1-submission`.
