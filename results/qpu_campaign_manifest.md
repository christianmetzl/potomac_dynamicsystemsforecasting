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
