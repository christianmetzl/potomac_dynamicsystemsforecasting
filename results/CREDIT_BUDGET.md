# Credit budget & spend attribution — Team EIGENNEXUS (Track A project)

*Maintained for organizer audit. Every line is verifiable two independent ways: (a) against
qBraid's own job records via the job IDs and tags below, and (b) re-derived from published
per-shot pricing by `credit_audit.py` (`cli.py run credit_audit`) — a self-contained check
that needs no API key and asserts every campaign's cost and the ceiling. Nothing here relies on
our self-reporting. **Program COMPLETE through 2026-07-22 (all campaigns + Amendment 4);
last updated 2026-07-22.**

## 0. Whole-program cost at a glance

| bucket | account / currency | amount | note |
|---|---|---|---|
| **Org-pool hardware (this project)** | EIGENNEXUS org, qBraid cr | **60,698.25** | 10 tagged campaigns; ceiling 65,000 → **reserve 4,301.75** |
| Involuntary personal charge | personal, qBraid cr | 3,350 | Emerald-pair platform attribution anomaly (§2, §4) — outside the ceiling |
| **qBraid hardware total** | — | **64,048.25** | org + the anomaly charge |
| Self-funded de-risking era | personal, qBraid cr | ≈1,380 (≈$14) | Rigetti full protocol; + free-tier sims/rehearsals (0) |
| OpenQuantum-route work | personal, OpenQuantum cr | ≈147 OQ cr | separate free-tier/promotional currency; not qBraid credits |
| Free re-analyses (bootstrap, fingerprint, audit) | — | 0 | committed-counts re-analysis, no hardware |

*Distinct accounts and two currencies (qBraid cr vs OpenQuantum cr) are kept separate rather
than summed into one misleading number. The organizer-relevant figure is the first row:
**60,698.25 of the 65,000 org ceiling.***

## 1. Funding structure

| pool | source | scope |
|---|---|---|
| **Personal account (default org)** | privately funded by C. Metzl | all pre-allocation de-risking: Rigetti full protocol, cloud-simulator validation, OpenQuantum-route IonQ/IQM work |
| **Team org EIGENNEXUS** | organizer allocations: 60,000 (2026-07-18) + 70,000 (2026-07-19) = **130,000** | shared by two projects; **this project's agreed ceiling: 65,000** |

Project attribution on the shared org is mechanical, not estimated: **every quantum job this
project submits embeds `tags = {campaign: <name>, commit: <repo-hash>}` in the platform's job
records.** Our org-pool spend is the sum over tagged quantum jobs; anything else in the org's
drawdown (e.g. GPU/compute instances) belongs to the parallel project.

## 2. Org-pool ledger — this project (complete as of last update)

| platform job ID | campaign tag | status | est. cr | billed cr |
|---|---|---|---|---|
| `aws:iqm:qpu:garnet-4500-qjob-6a5bb22fd17a5abc1d707148` + 11 campaign jobs (see results JSON) | `hw_garnet_native` | COMPLETED | 6,754.5 | 6,754.5 |
| `aws:ionq:qpu:forte-1-4500-qjob-6a5e3f3fd17a5abc1d70e7a0` (orientation, 100 shots) | `hw_ionq_smoke` | COMPLETED | 830.0 | 830.0 |
| 3 fold-5 submissions (gate-limit rejections, see `results/qpu_ionq_smoke.json`) | `hw_ionq_smoke` | FAILED (validation) | 0.0 | 0.0 |
| 5 campaign jobs `...711a74/711ac5/711bbc/711c42/711ce0` (see results JSON) | `hw_ionq_native` | COMPLETED | 20,150.0 | 20,150.0 (5 × 4,030) |
| `openquantum:ionq:qpu:forte-1-bd52-qjob-6a5ead84d17a5abc1d711a81` (fold-3 probe) | `oq_fold3_probe` | FAILED (validation) | 0.0 | 0.0 |
| 12 replication jobs `...711eb7 … 71210d` (see results JSON) | `hw_rigetti_rep` | COMPLETED | 2,234.25 | 2,234.25 (probe 34.25 + 11 × 200) |
| 24 dress-rehearsal jobs on `qbraid:qbraid:sim:qir-sv` (see results JSON) | `dress_n10` | COMPLETED | 0.0 | 0.0 (free device) |
| 12 scaling jobs `...712974 … f18950` (see results JSON) | `hw_garnet_n10` | COMPLETED | 6,754.5 | 6,754.5 (probe 44.5 + 11 × 610) |
| 12 scaling jobs `...f18957 … f189e7` (see results JSON) | `hw_garnet_n12` | COMPLETED | 6,754.5 | 6,754.5 (probe 44.5 + 11 × 610) |
| 12 anchor jobs `...f18971 … f189e4` (see results JSON) | `hw_garnet_n8_anchor` | COMPLETED | 6,754.5 | 6,754.5 (probe 44.5 + 11 × 610) |
| 12 scaling jobs `...f18ac6 … 8aeeb9` (see results JSON) | `hw_emerald_n8` | COMPLETED | 7,416 | 7,416 (probe 46 + 11 × 670) |
| 5 pair jobs `garnet-4500-...072b … 074b` (see results JSON) | `hw_garnet_n8_pair` | COMPLETED | 3,050 | 3,050 (5 × 610) |
| 5+3 pair jobs `emerald-bd52-...072e … 0819` | `hw_emerald_n8_pair` | COMPLETED (3 transient FAILED billed 0) | 3,350 | **0 to org — billed to the personal account** (see §4 and the attribution anomaly note below) |
| `qbraid:qbraid:sim:qir-sv-4500-qjob-6a5c26ded17a5abc1d708762` | `tag_test` | COMPLETED | 0.0 | 0.0 |

**Project spend against the 65,000 ceiling: 60,698.25 settled** (Campaign A 6,754.5 + IonQ smoke
gate 830 + Campaign B′ 20,150 + Rigetti replication 2,234.25 + Garnet n=10 6,754.5 + Garnet n=12
6,754.5 + same-session n=8 anchor 6,754.5 + Emerald n=8 7,416 + Garnet pair 3,050 — each at or
under its pre-approved reservation; every failed/rejected submission billed 0). **Remaining
reserve: 4,301.75. The hardware program incl. Amendment 4 is COMPLETE; no further spend planned.**

**Attribution anomaly (disclosed):** the Emerald half of the Amendment-4 pair
(`hw_emerald_n8_pair`, 3,350 cr) was submitted with the same org API key and in the same shell
environment as its Garnet twin, yet the platform created its jobs under the **personal account
context** (job-ID fragment `-bd52-` vs `-4500-` for every org job; the jobs 403 under the org
key and are readable only with the personal key; the 3,350 billed the personal wallet, 0 the
org pool). Yesterday's full Emerald campaign (`hw_emerald_n8`) ran org-attributed on the same
device, so the entitlement context evidently changed after Emerald's maintenance window. Our
reconstruction — silent cross-context re-attribution when org device entitlement diverges — is
documented as unconfirmed platform finding #3 in `results/platform_feedback_qbraid.md`. The
3,350 is accounted in §4 (self-funded, outside the ceiling); the science is unaffected and the
job records remain platform-timestamped and verifiable from the owning account.

Planned-spend history (pre-registered: `results/qpu_campaign_manifest.md` + Amendment 1):
Campaign B was re-scoped to B′ (scale-1-only, ≈20,150 instead of ≈45,990) after the smoke gate
measured IonQ's 2,000-gate/circuit ceiling — abort rule 1, disclosed in
`results/qpu_hardware_findings.md`. The Rigetti replication executed at 2,234.25 of its 2,400
envelope (165.75 released). **Final reserve remaining: 4,301.75 of the 65,000 ceiling**
(65,000 − 60,698.25). Each campaign required an explicit go decision before launch.

## 3. Org-pool cross-check (wallet arithmetic)

| | credits |
|---|---|
| granted | 130,000 |
| → this project, settled (sum of tagged org jobs above; per-job API-verified AND re-derived by `credit_audit.py`) | **60,698.25** |
| → this project, ceiling | 65,000 |
| → this project, reserve remaining | 4,301.75 |
| → parallel project | whatever remains of the org drawdown after subtracting our tagged jobs (non-quantum compute; by elimination) |

The wallet balance moves with both projects, so this file pins only what is mechanically ours:
the per-job billed amounts fetched from qBraid's job records for every tagged job listed above
(5 × 4,030 for `hw_ionq_native`, 830 for `hw_ionq_smoke`, 6,754.5 for `hw_garnet_native`,
34.25 + 11 × 200 for `hw_rigetti_rep`, 44.5 + 11 × 610 each for `hw_garnet_n10`,
`hw_garnet_n12`, and `hw_garnet_n8_anchor`, 46 + 11 × 670 for `hw_emerald_n8`, 5 × 610 for
`hw_garnet_n8_pair`). `credit_audit.py` re-derives every one of these from published per-shot
pricing and asserts the 60,698.25 total and the 65,000 ceiling — reproduce with
`cli.py run credit_audit`.

## 4. Self-funded era (personal account — outside the ceiling)

| item | approx. cost | provenance |
|---|---|---|
| Rigetti Cepheus-1 full protocol (12 jobs, 2,000 shots each) | ≈1,380 qBraid cr (≈$14) | job IDs in `results/qpu_run_hw_rigetti.json` |
| qBraid cloud-simulator validation + cross-domain battery + dress rehearsals (60+ jobs) | 0 (free tier) | `results/qpu_run_cloudsim.json`, `results/hosted_runtime_check.json`, `results/qpu_run_dress_*.json` |
| OpenQuantum-route IonQ/IQM work (probes, calibrations, first Garnet window; incl. the negative-angle discovery jobs) | ≈147 OpenQuantum cr | job IDs in `results/qpu_ckpt_hw_garnet_oq.json`, `results/platform_feedback_bundle/` |
| `hw_emerald_n8_pair` (5 completed jobs @ 670; involuntary — platform attribution anomaly, see §2 note) | 3,350 qBraid cr | job IDs in `results/qpu_run_hw_emerald_n8_pair.json`; readable from the personal account |

## 5. How to verify independently (organizers)

```python
from qbraid.runtime import QbraidProvider   # any account with org visibility
c = QbraidProvider().client
for j in c.list_jobs(limit=100):
    d = j.model_dump()
    if d.get("tags", {}).get("campaign"):    # ← this project's jobs, self-identified
        print(d["jobQrn"], d["tags"], d.get("cost"))
```

The `commit` tag on each job is a hash-preimage commitment: the exact repository state
(manifest, predictions, configs) provably existed before the platform's job-creation
timestamp. See `results/qpu_campaign_manifest.md` for the pre-registered plan these jobs
execute.
