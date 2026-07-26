# S7 secondary arm — H-EMBED: ATTEMPTED, NOT COMPLETED (device unreachable)

*Outcome of the attempt specified in `results/h_embed_prerun.md` (committed `e6a55b4`, before any
job was submitted). Scored by the abort rule in that file, §5. Reported as measured.*

## Verdict

**H-EMBED remains OPEN.** The arm was attempted on 2026-07-25 and aborted before any campaign
completed. **No data was obtained and nothing is scored** — neither the vacuity check (§4 Step 1)
nor the pre-registered `|Δraw| > 0.01` rule (§4 Step 2) was reached, because no measurement exists
to apply them to.

## What happened

Arm 1 (`hw_hembed_default`, `--seed 0`, `perm_seed=0`) was launched on
`openquantum:iqm:qpu:garnet` at 22:07 UTC, tagged `commit=e6a55b4a7b2e`. Its **first** job — the
bit-order orientation probe — never reached a terminal state.

| job on `openquantum:iqm:qpu:garnet` | circuit | shots | poll ceiling | outcome |
|---|---|---|---|---|
| campaign orientation (22:07 UTC Sat) | 8 qubits, 1 gate | 4,000 | 5,400 s (90 min) | never terminal |
| independent health check (Sat) | **1 qubit, 1 gate** | **100** | 600 s (10 min) | never terminal |
| control probe (05:57 UTC Sun) | **1 qubit, 1 gate** | **100** | 600 s (10 min) | never terminal |

Throughout all three attempts the platform reported the device as **`ONLINE` with
`queue_depth: 0`**.

**Precise diagnosis (queried 2026-07-26 05:13 UTC, 7.1 h after submission).** The orientation job
is still in state **`INITIALIZING`**, with `endedAt: None` and `executionDuration: None`:

```
job  openquantum:iqm:qpu:garnet-bd52-qjob-6a6533930936bd6f4cec9d83
     createdAt  2026-07-25 22:07:19 UTC
     status     INITIALIZING        (8.0 h and counting at 06:08 UTC)
     endedAt    None
     executionDuration  None
```

`INITIALIZING` means the job **never entered the device queue**. That resolves the apparent
contradiction of an idle `queue_depth: 0` device not returning work: nothing is being handed to the
device. A single-gate, one-qubit, 100-shot circuit that does not return within ten minutes on an
idle-and-online device is not a load or queueing effect.

## Matched-pair control (2026-07-26 05:54–06:08 UTC) — and a correction against ourselves

An earlier version of this file attributed the failure to the **OpenQuantum route's dispatch
layer**. We then tested that attribution instead of asserting it, with the cheapest possible
control: the **identical** 1-qubit / 1-gate / 100-shot probe, the **same route**, a **different
device**, submitted 3.5 minutes apart under a common 600 s ceiling.

| probe | device (same `openquantum:` route) | trajectory | outcome |
|---|---|---|---|
| control | `rigetti:qpu:cepheus-1-108q` | `INITIALIZING` → `QUEUED` (46 s) → `COMPLETED` (182 s) | counts `{'0': 4, '1': 96}` — correct |
| test | `iqm:qpu:garnet` | `INITIALIZING`, never left it | **not terminal at 600 s** |

**The route works.** The earlier route-wide attribution was too broad and is withdrawn. The
condition is **specific to IQM Garnet**: three independent Garnet jobs spanning 8 h (orientation
4,000-shot, health probe 100-shot, control probe 100-shot) all sit in `INITIALIZING`, while a job
submitted through the same route to another vendor's device completed in three minutes.

A second, independent measurement agrees and points at the device rather than the broker: the
**other** route to the same physical machine, `aws:iqm:qpu:garnet`, simultaneously reports
`UNAVAILABLE` with **`queue_depth: 855`** (and IQM Emerald likewise `UNAVAILABLE`, queue 140).

We separate what we measured from what we infer:

- **Measured.** Garnet jobs do not leave `INITIALIZING` on the OQ route; an identical control on the
  same route completes; the AWS route to the same device reports `UNAVAILABLE` with an 855-deep
  backlog.
- **Inferred (our reading, not vendor-confirmed).** The IQM Garnet backend is not accepting work.
  The OQ route's status field reports it as `ONLINE, queue_depth 0` regardless, and **that reporting
  gap — not the dispatch itself — is what made the failure expensive to diagnose**: every
  observable signal said "idle and healthy, keep waiting."

We stopped rather than spend the remaining credits submitting into it.

Arm 2 (`--perm-seed 7`) was **never launched**: the pre-registered design requires both arms in the
**same session** for drift control, and with arm 1 unable to complete there was no session to join.

## Ledger

- Jobs submitted: **4**, all on personal OpenQuantum credits, outside the org ceiling — the
  campaign orientation (4,000 shots) and three 100-shot diagnostics (Garnet health probe, Garnet
  control probe, Rigetti control probe).
- **Campaign** jobs completed: **0**. Result files written: **0**. Windows measured: **0**. The one
  job that did return counts is the Rigetti *control*, which carries no CHIMERA data by
  construction (1 qubit, 1 gate) and exists only to test our own failure attribution.
- The committed checkpoint `results/qpu_ckpt_hw_hembed_default.json` records exactly this: an empty
  `jobs` map and one `pending` entry. It is kept, not deleted, so the record shows what was
  submitted.

## Why this is reported rather than retried into

The abort rule was committed **before** the run precisely so that a bad device could not turn into
a bad result. Applying it:

- The pre-registered rule is **not** applied to a campaign that produced no data.
- Retrying was considered and rejected on evidence, not preference: the cheapest possible probe
  had already failed, so further submissions had no reasonable expectation of returning.
- The alternative route `aws:iqm:qpu:garnet` reported `UNAVAILABLE`, and a funded campaign there
  (~6,754 cr) exceeds the remaining org reserve (4,301.75) in any case.
- Substituting a device was considered explicitly once the control showed the route itself was
  healthy, and rejected. The full catalogue was enumerated: of every gate-model QPU reachable and
  `ONLINE`, only **Rigetti Cepheus-1** also scrambles at n=8 (raw 0.2226 > limit 0.1958) — Emerald
  (0.1793) and IonQ Forte-1 (0.1042) are *signal-bearing* there, so on them there is no scrambling
  whose mechanism could be tested. Rigetti is therefore the only candidate, and it fails on two
  counts: (i) the pre-registered arm names the Garnet seed-0 n=8 instance, so a Rigetti run is a
  different question and could not honestly be reported as H-EMBED; (ii) Rigetti's scrambling is
  already attributed here to lattice routing (~10³ native two-qubit gates), and permuting qubit
  labels on a 108-qubit lattice changes that routing — so `|Δraw| > 0.01` would be expected for a
  reason that has nothing to do with the hypothesis. A test whose positive outcome is
  near-predetermined by gate count is not a test. **Same-device comparison is what makes H-EMBED
  meaningful.**

## What this changes in the paper

**Nothing.** H-EMBED was already reported as pre-registered-and-unrun; it still is. The mechanism
behind the seed-0 n=8 scrambling — instance structure vs embedding vs per-feature noise sensitivity
— **remains honestly open**, exactly as `qpu_hardware_findings.md` states.

What did change is that the arm is now **execute-ready rather than merely specified**:
`qpu_run.py --perm-seed P` is implemented, the relabeling is verified exact to 9.0e-16, the
depolarized limit is proven bit-identical between arms, and the scoring rule (including the vacuity
guard) is committed. The arm can be run in ~2.2 h whenever IQM Garnet becomes reachable again;
`route_health_probe.py` is the ~0-cost check that decides whether it is.

## Platform observation (third of its kind, still unconfirmed by the vendor)

This is our **third** independent OpenQuantum-route reliability observation, after the two in
`platform_feedback_qbraid.md` and the abandoned single-window preview noted in
`qpu_hardware_findings.md`. This instance is the one we could pin down, because we ran the control
rather than only the complaint:

> **`openquantum:iqm:qpu:garnet` reported `ONLINE, queue_depth: 0` continuously while three
> successive jobs — including a 1-qubit, 1-gate, 100-shot circuit — sat in `INITIALIZING` for up to
> 8 h and never entered the device queue. A byte-identical probe on the same route to
> `openquantum:rigetti:qpu:cepheus-1-108q`, submitted 3.5 minutes earlier, completed in 182 s. The
> alternative route to the same physical device (`aws:iqm:qpu:garnet`) concurrently reported
> `UNAVAILABLE, queue_depth: 855`.**

The actionable part is the **status field**, not the queue: one route called the device idle and
healthy while the other called it unavailable with an 855-deep backlog, at the same moment, for the
same machine. A user polling only the first has no signal to stop on. We report this as **our
observation, not a vendor-confirmed defect**. It cost us an experiment we had funded and were ready
to run.

The reproduction is committed, not described — `route_health_probe.py` is the exact script that
produced both rows of the table above:

```
python3 route_health_probe.py openquantum:rigetti:qpu:cepheus-1-108q   # completed in 182 s
python3 route_health_probe.py openquantum:iqm:qpu:garnet              # not terminal at 600 s
```

It submits one 1-qubit, 1-gate, 100-shot circuit and polls to a 600 s ceiling. Anyone can re-run the
control against any device on any route for effectively zero credits, which is the point: the
observation is falsifiable by a third party in three minutes.
