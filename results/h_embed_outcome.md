# S7 secondary arm — H-EMBED: ATTEMPTED, NOT COMPLETED (route degraded)

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

| probe | circuit | shots | poll ceiling | outcome |
|---|---|---|---|---|
| campaign orientation | 8 qubits, 1 gate | 4,000 | 5,400 s (90 min) | never terminal |
| independent health check | **1 qubit, 1 gate** | **100** | 600 s (10 min) | never terminal |

Throughout both attempts the platform reported the device as **`ONLINE` with `queue_depth: 0`**.

A single-gate, one-qubit, 100-shot circuit that does not return within ten minutes on an
idle-and-online device is not a load or queueing effect. We record the route as **degraded at that
time** and stopped, rather than spend the remaining credits submitting into it.

Arm 2 (`--perm-seed 7`) was **never launched**: the pre-registered design requires both arms in the
**same session** for drift control, and with arm 1 unable to complete there was no session to join.

## Ledger

- Jobs submitted: **1** (orientation, 4,000 shots) + **1** health probe (100 shots), both on
  personal OpenQuantum credits, outside the org ceiling. Neither returned counts.
- Jobs completed: **0**. Result files written: **0**. Windows measured: **0**.
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
- Running the arm on a different device (e.g. Emerald) would not answer the question: the n=8
  scrambling under investigation is a **Garnet seed-0** phenomenon, and Emerald is *signal-bearing*
  at n=8. Same-device comparison is what makes H-EMBED meaningful.

## What this changes in the paper

**Nothing.** H-EMBED was already reported as pre-registered-and-unrun; it still is. The mechanism
behind the seed-0 n=8 scrambling — instance structure vs embedding vs per-feature noise sensitivity
— **remains honestly open**, exactly as `qpu_hardware_findings.md` states.

What did change is that the arm is now **execute-ready rather than merely specified**:
`qpu_run.py --perm-seed P` is implemented, the relabeling is verified exact to 9.0e-16, the
depolarized limit is proven bit-identical between arms, and the scoring rule (including the vacuity
guard) is committed. The arm can be run in ~2.2 h whenever the route is healthy.

## Platform observation (third of its kind, still unconfirmed by the vendor)

This is our **third** independent OpenQuantum-route reliability observation, after the two in
`platform_feedback_qbraid.md` and the abandoned single-window preview noted in
`qpu_hardware_findings.md`. The pattern is consistent: the route reports `ONLINE` with an empty
queue while submitted jobs do not reach a terminal state. We report it as **our observation, not a
vendor-confirmed defect**, and it costs us an experiment we had funded and were ready to run.
