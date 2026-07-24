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

*Gate-count convention: the "2q gates" columns count **CX gates after the IsingZZ→CX·RZ·CX
decomposition** (440 at n=8). The paper's §6 resource table quotes the underlying **IsingZZ
interaction** count — 220/480/760 at n=8/10/12, exactly half — and on all-to-all trapped-ion each
interaction is a single native two-qubit gate, so IonQ executes 220. Same circuit, different gate
basis.*

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

---

## Post-challenge outlook, pre-registered 2026-07-22 (after the executed program; before any funding)

*The executed program (S1–S4, all resolved — see `qpu_hardware_findings.md`) changes what the
next experiments should be: Emerald retains circuit signal at n=8, so hardware-in-the-loop
inference is no longer meaningless, and dissipation is the one mechanism our simulation study
showed lifting autonomous prediction. Committed now, same discipline: config + falsifiable
statement first, execution only if funded.*

**(S5) End-to-end hardware-in-the-loop forecast (Emerald n=8, scale-1).** Replace simulated
features with hardware features for every test window of the paper's nested-ridge protocol
(one 4k-shot circuit per test window ≈ 670 cr each; the 2008 evaluation window at the paper's
stride ⇒ order 100 circuits ≈ 70k credits — post-challenge funding scale). Method committed
now: before any run, the expected degradation band is computed by injecting the *measured*
same-window per-feature errors (raw 0.1690, `qpu_run_hw_emerald_n8_pair.json`) into the frozen
ridge head. Falsifiable commitments: (S5a) the hardware-in-the-loop forecast lands inside that
pre-computed band; (S5b) it does **not** beat HAR-X — hardware does not rescue the negative.
(S5b failing would be the single most important result this program could produce; we consider
it very unlikely and say so.)

**(S6) Hardware-native dissipative reservoir.** Our simulation study
(`results/dissipative_qrc_findings.md`) showed engineered memory-qubit damping tracing an
inverted-U in damping rate and lifting autonomous VPT ≈+60%. On hardware, amplitude damping is
free (T1 decay): insert calibrated idle delays (or mid-circuit resets where the route exposes
them) on designated memory qubits. Prereqs (all free): per-route delay/reset emission audit +
rehearsals. A 5-level damping sweep at Garnet-class pricing (5 × 3 windows + cals, scale-1)
≈ 10.4k credits. Falsifiable commitments: (S6a) feature quality / autonomous VPT vs damping
strength reproduces the **inverted-U on metal** — intermediate damping beats both zero and
strong; (S6b) the optimum differs measurably between device classes (T1 and gate-time scales
differ by orders of magnitude between superconducting and trapped-ion).

Neither experiment is fundable from the remaining project reserve (4,301.75) and neither will
be run before the Phase-3 deadline; they stand as the program's committed next chapter.

**(S7) Mechanism isolation — embedding vs instance (added 2026-07-22, pre-registered).**
The drift-controlled size effect (S1/S2 refutations) has no established mechanism; the two
leading candidates make different predictions, so we commit the discriminating experiment:
run the *same* seed-0 n=8 instance twice in one Garnet session — once with the default
logical-to-physical assignment, once with the qubit labels permuted in the emitted QASM
(lean scale-1 config, 5 jobs each; ≈3,050 cr per embedding; same-session cals as
fingerprints). Committed hypothesis, falsifiable both ways: **(S7a)** if the permuted
embedding's raw error differs from the default by more than the same-session band we measured
(≈0.01), the effect is **embedding-dominant** (the n=8 default assignment happens to sit on
worse qubits/couplers); **(S7b)** if it matches within the band while n=10/12 remain
signal-bearing, the effect is **instance-dominant** (graph/feature structure, not placement).
Caveat committed in advance: the platform transpiler may re-route a permuted circuit, so the
executed assignment must be read back from the returned program metadata where exposed, and
the claim is made at whichever layer the evidence supports.

**S7 sharpened into two named, competing hypotheses (2026-07-24, committed before execution).**
The size-effect refutations (S1/S2) rest on the seed-0 instance; the open question is *why*
n=8 scrambles while n=10/12 are signal-bearing on the same chip. Two mechanisms, opposite
predictions:

- **H-INSTANCE** — the size effect is a property of the *reservoir circuit class at each n*
  (its coupling-graph density and feature composition), not of the seed-0 instance or its
  lattice placement. **Prediction:** on an **independent instance (seed 1)**, n=8 again
  scrambles (raw ≥ its 0.196 limit) *and* n=10 is again signal-bearing (raw < its 0.179 limit)
  — the size-dependent sign of (raw − limit) reproduces across instances.
- **H-EMBED** — the n=8 scrambling is driven by seed-0's particular logical→physical
  placement. **Prediction:** re-embedding the *same* seed-0 n=8 circuit (permuted qubit
  labels, same session) shifts raw error by more than the measured same-session band (≈0.01).

**Primary arm (transpiler-independent, EXECUTED 2026-07-24 — H-INSTANCE REFUTED): H-INSTANCE.** Same-session OpenQuantum-Garnet
run (personal OQ credits, ~20 cr/campaign; abort/score identical to the funded program):
seed-0 n=8 (same-session re-anchor), **seed-1 n=8**, **seed-1 n=10**. No code change (harness
already parameterizes `--seed`, `--n`); no dependence on embedding control.

**Decision rule (committed):**
- seed-1 n=8 raw ≥ 0.196 **and** seed-1 n=10 raw < 0.179 → **H-INSTANCE supported**: the size
  effect is instance-general, not a seed-0 artifact — the single-seed objection is answered.
- seed-1 n=8 raw < 0.196 (signal-bearing at n=8 on a second instance) → **seed-0 was a
  pathological instance**; the n=8 "scrambled" regime does not generalize, and S1/S2 must be
  re-scoped to "instance-dependent." Reported as measured, either way.
- Any raw within ±0.02 of its limit → unresolved for that point; only the disjunction is claimed.

**Secondary arm (embedding, transpiler-caveated): H-EMBED** — attempted if OQ credits/time and
the returned mapping permit a clean test; otherwise it remains pre-registered for later. **The S7
result is folded into** `qpu_hardware_findings.md` (executed 2026-07-24): seed-1 n=8 raw 0.159
(signal-bearing) **refutes H-INSTANCE** — the n=8 scrambling is seed-0-instance-specific, not
size-driven; seed-1 n=10 raw 0.146 (signal-bearing) independently reproduces the n=10 result while
the same-session seed-0 n=8 anchor stays scrambled (0.228). Provenance tags carry the commit that
contains this text, so the prediction provably predates the data.
