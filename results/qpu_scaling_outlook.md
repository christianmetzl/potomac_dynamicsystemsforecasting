# Hardware scaling program — pre-registered outlook (execution-ready, not yet funded)

*Committed 2026-07-19, before any funding for this program exists. Dual purpose: (a) if credits
become available post-campaigns, this is the execution-ready, pre-registered plan; (b) if not,
it stands as the falsifiable research outlook — the questions we would ask next, with our
commitments on record either way. Same discipline as `results/qpu_hardware_predictions.md`.*

## The question

Our n=8 campaigns measure a *point* on the coherence-budget wall: raw feature error at or beyond
the fully-depolarized limit on two superconducting vendors. The scaling program would *map* the
wall: how does hardware feature error move with system size (n = 10, 12 on IQM Garnet) and with
hardware generation (n = 8 on IQM Emerald, 54q, newer fidelities)? Simulation already gives us
the exact classical cross-check at every size; nobody, to our knowledge, has published a
pre-registered multi-size QRC scaling curve on cloud hardware.

## Computed inputs (exact, from the engine — the falsifiable scaffolding)

| n | features | 2q gates (scale 1) | 2q gates (fold 5) | depolarized limit | Garnet cost/campaign |
|---|---|---|---|---|---|
| 8 (measured) | 36 | 440 | 2,200 | 0.1958 | 6,755 cr |
| 10 | 55 | 960 | 4,800 | **0.1790** | 6,755 cr |
| 12 | 78 | 1,520 | 7,600 | **0.2140** | 6,755 cr |
| 14, 16 | 105, 136 | — | — | *to be computed with the sparse engine before any run* | 6,755 cr each |

(Billing is per shot, so campaign cost is flat in n — the scaling program is unusually cheap.
Emerald n=8: 0.16 cr/shot ⇒ ≈7,420 cr. The limit values are exact means of |F_exact| over the
3 pre-registered RV windows at each n; note the limit is **non-monotonic in n** while the gate
count more than triples — that separation is what gives the measurements discriminating power.)

## Pre-registered falsifiable statements (committed now)

We deliberately commit ordering/threshold statements rather than fitted point forecasts: the
measured n=8 errors *exceed* the depolarized limit, which a pure depolarizing model cannot
reproduce — fitting one would be overclaiming. The commitments:

- **(S1) The wall persists at every size:** on Garnet, raw scale-1 error at n = 10 and n = 12
  will meet or exceed the n-dependent depolarized limit above (as measured at n=8 on two
  superconducting vendors).
- **(S2) The coherent-scrambling margin grows with depth:** the excess (raw error − limit)
  will be larger at n=12 than at n=8 (two-qubit count 1,520 vs 440).
- **(S3) Generation helps but does not cross the wall:** Emerald (newer IQM chip) raw error at
  n=8 will be *below* Garnet's n=8 raw error, but still at or above the 0.1958 limit at this
  circuit depth.
- **(S4) No ZNE recovery at any size** on this device class (scale 1 beyond budget ⇒ folding
  has no signal to extrapolate), consistent with the n=8 measurements.

Any statement failing is publishable news; S3 failing *high* (Emerald below the limit) would be
the first signal-bearing superconducting execution of this reservoir and would upgrade the
paper's outlook materially.

## Execution plan (if funded; ~29,300 cr for Garnet n∈{10,12} replicated ×0 + Emerald; ~44k with n=14,16)

Per size: identical 12-circuit protocol (100-shot orientation probe, rz-diagonal + all-RY(π)
calibrations, 3 windows × fold scales 1/3/5 at 4,000 shots), checkpointed, provenance-tagged,
same-session calibration rule, scored by `score_campaign.py` extended per-n. Order: Garnet
n=10 → n=12 → Emerald n=8 → (n=14, 16 after sparse-engine predictions are committed).
Approval gate before each campaign, per the standing operating rule.

## Pre-work status (all free)

- [x] Depolarized limits, gate counts, costs computed exactly for n = 8, 10, 12 (this document).
- [x] Statements S1–S4 committed.
- [ ] Emission + conversion audit at n = 10, 12 (extend `qpu_ionq_conversion_audit` pattern).
- [ ] Free qir-sv dress rehearsal at n = 10 (n = 12 blocked by the documented qir-sv anomaly —
  local exact cross-check substitutes there).
- [ ] `score_campaign.py` per-n extension.
- [ ] n = 14, 16 limits via the sparse engine (`frontier_scaling.py` machinery).
- [ ] Manifest amendment on funding.
