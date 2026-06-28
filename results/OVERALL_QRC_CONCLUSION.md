# What we can conclude overall for Quantum Reservoir Computing (QRC)

*Cross-cutting synthesis of the whole project — V1 (Track A, realized-volatility submission), V2
(Track-A extensions), V3 (Track B, weather), and the methodological probes (capacity, frontier
scaling, noise, recurrence). Every claim below is tied to a script + saved artifact in this repo.
This document is a synthesis; it does not modify the V1 submission (frozen at tag `v1-submission`).*

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

Ten independent fair tests; the quantum reservoir wins **none** of them. Its single closest approach
is one statistical tie (Rapid City h=1) and one near-match (recurrent Lorenz VPT 0.50 vs 0.61).

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

**Honest open frontier (we neither confirm nor refute):**
6. **The large-scale, dissipative, recurrent regime is untested.** Everything above is exact
   simulation at n ≲ 16. A genuine QRC edge — if it exists — most plausibly lives at **100+ qubits
   with engineered dissipation** on analog hardware (Kornjača 2024), beyond classical simulation.
   Our results are silent there by construction.
7. **QRC's value may not be accuracy at all.** Native processing of *quantum* data, analog energy
   efficiency, or tasks with intrinsic quantum structure are real possibilities that classical-data
   financial/weather forecasting simply does not probe.

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
