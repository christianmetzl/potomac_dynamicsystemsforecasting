# Pre-registered QPU campaign manifest — 60,000-credit allocation

*Committed BEFORE any allocation credit is spent, in the same spirit as
`results/qpu_hardware_predictions.md`: the complete job list, per-job budget at the
platform-verified rates, execution order, and abort rules. Deviations, if any, will be
documented against this manifest.*

## Verified billing rates (qBraid native routes, from our own billed jobs / pricing API)

| device | per shot | per task |
|---|---|---|
| aws:iqm:qpu:garnet | 0.145 cr | 30 cr |
| aws:ionq:qpu:forte-1 | 8 cr | 30 cr |

## Campaign A — IQM Garnet, full protocol at the pre-registered config (runs first)

4,000 shots/circuit (the configuration `qpu_hardware_predictions.md` was committed at).
Fresh route ⇒ fresh orientation probe and same-session calibrations (no data reuse from the
OpenQuantum partial run; that data remains a corroborating preview only).

| # | circuit | shots | cost (cr) |
|---|---|---|---|
| 1 | orientation probe | 100 | 44.5 |
| 2–3 | cal0 (rz-diagonal), cal1 (all-RY(π)) | 4,000 | 1,220 |
| 4–12 | 3 windows × fold scales 1/3/5 | 4,000 | 5,490 |
| | **Campaign A total** | | **≈6,755** |

Closes pre-registered predictions (i)-Garnet and (iii); supplies the Garnet half of (ii).

## Campaign B — IonQ Forte-1 at 500 shots (the decisive routing-free test)

500 shots/circuit — a disclosed deviation from the 4,000-shot prediction config, forced by the
8 cr/shot list rate (4,000-shot config = ≈352,000 cr, out of scope for this allocation). The
decisive claims — monotone mitigation recovery, cross-platform raw-error ordering — are read
from the mean over 108 observables (s.e. ≈0.004), which 500 shots resolves.

| # | circuit | shots | cost (cr) |
|---|---|---|---|
| 1 | orientation probe | 100 | 830 |
| 2 | fold-5 smoke test (w0_s5 at 100 shots) | 100 | 830 |
| 3–4 | cal0, cal1 | 500 | 8,060 |
| 5–13 | 3 windows × fold scales 1/3/5 | 500 | 36,270 |
| | **Campaign B total** | | **≈45,990** |

The fold-5 smoke test runs BEFORE the paid campaign: largest circuit class
(4,140 IonQ-JSON gates, 2,200 two-qubit — verified convertible client-side, zero negative
angles, `results/qpu_ionq_conversion_audit.json`) has never been billed at this length on
this route; 830 cr of insurance against a systematic class failure that would otherwise cost
~12,000 cr to discover.

## Budget

| | cr |
|---|---|
| Campaign A (Garnet) | 6,755 |
| Campaign B (IonQ) | 45,990 |
| Contingency (re-runs, per-session recalibration, duplicates) | 6,255 |
| **Allocation** | **60,000** |

Perfect-run spend ≈52,750 (saving ≈7,250). Contingency is spent only on documented failure
modes (all three observed on this account previously): platform re-queued duplicates,
completed-but-miscompiled jobs, session-boundary recalibration.

## Abort / decision rules (committed now)

1. **Smoke-test failure** (IonQ fold-5 does not complete or returns a physically impossible
   distribution): halt Campaign B before window circuits; investigate at ≤830 cr/probe;
   fall back to scales (1,3) protocol only if fold-5 is confirmed un-runnable (disclosed).
2. **Credit exhaustion mid-campaign**: harness fails fast on the billed reason and preserves
   every completed circuit in `results/qpu_ckpt_<tag>.json`; resume never re-bills.
3. **Session boundary** (device window closes mid-campaign): recalibrate (cal0+cal1) in the
   new session before any further window circuits; window circuits are only mitigated with
   same-session calibrations.
4. **Anomalous single result** (|feature error| beyond the fully-depolarized reference by >2×
   shot floor): one verification repeat, then accept the replicate.
5. **Leftover ≥2,430 cr after Campaign B lands clean and no further allocation is announced**:
   Rigetti 4,000-shot replication (12 × 200 cr) for error bars on the committed
   characterized-negative. Otherwise leftovers remain unspent.

## Pre-flight validation completed before this manifest (all free)

- `--selftest` PASS at HEAD (QASM = reservoir 0.0392; fold identity noise-only).
- Rehearsal mitigation chain validated at HEAD, including the 100-shot probe path.
- Client-side IonQ JSON conversion audit: all 12 circuit classes convert; **zero negative
  angles** at every fold scale (post-hardening emitter).
- Free cloud dress rehearsal of BOTH exact campaign configs (tags `dress_garnet_cfg`,
  `dress_ionq_cfg`) on qir-sv, exercising submission, shot-cap batching, checkpoint
  write/replay, and the full mitigation chain with this exact code.
- Native devices confirmed ONLINE (Garnet queue depth 0, IonQ 2 at check time).
- Checkpoint logic verified offline: replay is byte-identical with zero new backend calls;
  config changes invalidate the checkpoint explicitly.

---

## Amendment 1 (2026-07-19, committed before any further spend)

**Budget context change, campaign plan unchanged.** The organizers topped the shared team-org
pool up to 130k credits total; by agreement with the parallel project sharing the org, **this
project's ceiling is 65,000 credits for all its computations**. Project-attributed spend is
auditable via the per-job tags (`campaign=...`) each of our jobs embeds in the platform's
records.

Allocation under the 65k ceiling (execution order and configs identical to the original
manifest; the approval gate before each campaign stands):

| item | credits |
|---|---|
| Campaign A (Garnet, pre-registered 4k-shot config) | 6,755 |
| Campaign B (IonQ smoke pair + 11 circuits at 500 shots) | 45,990 |
| Contingency (per original manifest rules) | 6,255 |
| Rigetti 4,000-shot replication (original manifest rule 5, now pre-funded) | 2,400 |
| Reserve (unallocated; remains unspent absent a documented need) | 3,600 |
| **Project ceiling** | **65,000** |

Project spend to date against this ceiling: 44.5 (Campaign A orientation probe, reserved).

**Scope note:** all hardware execution predating the first 60k allocation — the complete
Rigetti Cepheus-1 protocol, cloud-simulator validation, and the OpenQuantum-route IonQ/Garnet
work — was **privately funded on the PI's personal account (default org)** and does not count
against this ceiling. The ceiling covers org-pool spend only, attributable via the per-job
campaign tags.

---

## Amendment 2 (2026-07-21, committed before scaling-program execution)

**The pre-registered scaling program (`results/qpu_scaling_outlook.md`, committed 2026-07-19
before funding existed) is now approved and funded from remaining headroom.** Ledger at
approval: 29,968.75 settled of 65,000 (`results/CREDIT_BUDGET.md`); statements S1–S4 and the
per-n depolarized limits were committed in the outlook document before this amendment.

| campaign | tag | config | est. credits |
|---|---|---|---|
| Garnet n=10 | `hw_garnet_n10` | identical 12-job protocol, 4k shots, scales 1/3/5 | 6,754.5 |
| Garnet n=12 | `hw_garnet_n12` | identical 12-job protocol, 4k shots, scales 1/3/5 | 6,754.5 |
| Emerald n=8 | `hw_emerald_n8` | Campaign-A config on `aws:iqm:qpu:emerald` (0.16 cr/shot) | 7,416 |
| **program total** | | | **20,925** |

Execution order n=10 → n=12 → Emerald, **explicit go decision before each campaign** (n=10
authorized with this amendment). Gates, inherited from the original manifest: free qir-sv/local
verification before each size (n=10 selftest PASS: Trotter 0.0286, fold identity 3e-12; n=12
qir-sv is blocked by the documented simulator anomaly — the local exact cross-check
substitutes); if a folded circuit is rejected at validation on the IQM route (billed 0, as all
validation rejections to date), fall back scales (1,3) → scale-1-only, disclosed — abort rule 1
pattern. Scoring: `score_campaign.py` per-n extension (S1/S2/S4 at n=10/12, S3 on Emerald),
committed with this amendment before execution. Projected reserve after the full program:
≈14,106 of the 65,000 ceiling.

---

## Amendment 3 (2026-07-21, committed before anchor execution)

**Same-session n=8 anchor approved** (+6,754.5 est., tag `hw_garnet_n8_anchor`): the identical
Campaign-A 12-job protocol at n=8, launched to run interleaved with / immediately adjacent to
`hw_garnet_n12` in the same Garnet session, so the pair (n=8 anchor, n=12) shares one
calibration epoch. Purpose: separate the size/instance effect from day-scale calibration drift
in the n=10 S1 refutation. Same-machine claims are made at **calibration-fingerprint level**
(per-qubit readout-error vectors measured by each campaign's own cal circuits, compared across
the session's start and end), not machine-identity level — cloud access cannot prove silicon.

**Pre-registered decision rule (committed before the anchor runs):**
- Anchor n=8 raw **≥ 0.1958** (beyond its limit, as in Campaign A) while same-session n=10/n=12
  results sit below their size-matched limits → **size/instance effect is real**, drift excluded
  as the driver of the n=10 result.
- Anchor n=8 raw **< 0.1958** → **calibration-day quality is the dominant driver**; the n=10
  below-limit result is then a device-state finding, not a size effect, and will be reported as
  such.
- Intermediate/ambiguous (anchor within ±0.02 of the limit): report as unresolved; no stronger
  claim than the disjunction.

Ledger at approval: 36,723.25 settled + n=12 in flight (6,754.5 reserved). Projected reserve
after anchor + Emerald: ≈7,352 of the 65,000 ceiling.

---

## Amendment 4 (2026-07-22, committed before execution): same-day cross-generation pair

**Purpose:** close the last methodological gap — the S3 cross-generation comparison (Emerald
0.1793 vs Garnet 0.2216–0.2301 at n=8) spans days, and our own Rigetti replication measured a
day swing (0.0385) of the same order as the generation gap (0.042+). This pair puts both chips
on the clock in the same window.

**Design (lean, fit-for-purpose — the claim at issue is raw scale-1 regime only, disclosed):**
per device, 5 jobs at 4,000 shots: 2 readout calibrations (fingerprints + readout stage) +
3 RV windows at scale 1 (no ZNE; single-scale carry-through as validated in Campaign B′).
Orientation probes skipped — both devices measured REVERSED twice each. Launched concurrently;
platform job timestamps establish temporal adjacency, and actual execution windows will be
disclosed as recorded (if one device queues far behind the other, adjacency is judged and
reported honestly).

| campaign | tag | est. credits |
|---|---|---|
| Garnet n=8 pair | `hw_garnet_n8_pair` | 3,050 (5 × 610) |
| Emerald n=8 pair | `hw_emerald_n8_pair` | 3,350 (5 × 670) |
| **total** | | **6,400** |

**Pre-registered decision rule:**
- Same-window Emerald raw < 0.1958 AND Garnet raw ≥ 0.1958 → generation effect **confirmed,
  temporally controlled**; the days-spanning caveat is removed from findings and paper.
- Both inside, or both beyond → **day effect dominates**; the S3 interpretation is revised
  accordingly and reported as such.
- Either raw within ±0.02 of 0.1958 → unresolved; only the disjunction is claimed.

Ledger at approval: 57,648.25 settled of 65,000. Projected after pair: ≈64,048.25 (reserve
≈952). This amendment spends from the reserve against a documented methodological need, per
Amendment 1's reserve rule.

---

## Amendment 5 (2026-07-24, committed before execution): S7 mechanism-isolation run (personal OQ)

**S7 primary arm (H-INSTANCE) EXECUTED on the OpenQuantum route using personal OpenQuantum
credits — outside the org ceiling and the org qBraid pool** (2026-07-24; verdict: seed-1 n=8
signal-bearing 0.159 and seed-1 n=10 signal-bearing 0.146 while the seed-0 n=8 anchor stays
scrambled 0.228 → **H-INSTANCE refuted; the n=8 wall is instance-specific**; folded into
`qpu_hardware_findings.md` §S7) (the 4,301.75 org reserve does not
fit S7 at native rates; OQ-Garnet is ~0.001 cr/shot). Config: same-session Garnet, scale-1
(2 cals + 3 windows, 4,000 shots), campaigns `hw_s7_garnet_seed0_n8`, `hw_s7_garnet_seed1_n8`,
`hw_s7_garnet_seed1_n10`; est. ≈20 OQ cr each (~60 total, within the ~102 held). Hypotheses,
predictions, and the decision rule are pre-registered in `results/qpu_scaling_outlook.md`
(committed before launch; job tags carry that commit). Scored by `score_campaign.py` against
the per-n limits {8: 0.196, 10: 0.179}. Personal-account spend, logged in `CREDIT_BUDGET.md`
§4 (self-funded era), not against the 65,000 org ceiling.
