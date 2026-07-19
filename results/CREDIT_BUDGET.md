# Credit budget & spend attribution — Team EIGENNEXUS (Track A project)

*Maintained for organizer audit. Every line is verifiable against qBraid's own job records via
the job IDs and tags below — nothing here relies on our self-reporting. Last updated
2026-07-19 (pre-Campaign-A execution); this file is refreshed at each campaign completion.*

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
| `aws:iqm:qpu:garnet-4500-qjob-6a5bb22fd17a5abc1d707148` | (probe; pre-dates tagging) | QUEUED | 44.5 | pending |
| `qbraid:qbraid:sim:qir-sv-4500-qjob-6a5c26ded17a5abc1d708762` | `tag_test` | COMPLETED | 0.0 | 0.0 |

**Project spend against the 65,000 ceiling: 44.5 reserved, 0 settled.**

Planned spend (pre-registered: `results/qpu_campaign_manifest.md` + Amendment 1): Campaign A
(Garnet) ≈6,755 · Campaign B (IonQ) ≈45,990 · contingency 6,255 · Rigetti replication 2,400 ·
reserve 3,600 — ceiling 65,000. Each campaign requires an explicit go decision before launch.

## 3. Org-pool cross-check (wallet arithmetic at last update)

| | credits |
|---|---|
| granted | 130,000 |
| wallet balance | ≈116,446 |
| total drawn | ≈13,554 |
| → this project (tagged quantum jobs above) | 44.5 (reserved) |
| → parallel project (non-quantum compute, by elimination) | ≈13,509 |

## 4. Self-funded era (personal account — outside the ceiling)

| item | approx. cost | provenance |
|---|---|---|
| Rigetti Cepheus-1 full protocol (12 jobs, 2,000 shots each) | ≈1,380 qBraid cr (≈$14) | job IDs in `results/qpu_run_hw_rigetti.json` |
| qBraid cloud-simulator validation + cross-domain battery + dress rehearsals (60+ jobs) | 0 (free tier) | `results/qpu_run_cloudsim.json`, `results/hosted_runtime_check.json`, `results/qpu_run_dress_*.json` |
| OpenQuantum-route IonQ/IQM work (probes, calibrations, first Garnet window; incl. the negative-angle discovery jobs) | ≈147 OpenQuantum cr | job IDs in `results/qpu_ckpt_hw_garnet_oq.json`, `results/platform_feedback_bundle/` |

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
