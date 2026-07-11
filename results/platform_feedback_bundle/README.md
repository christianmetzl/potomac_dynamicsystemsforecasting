# Reproduction bundle — platform feedback, Team EIGENNEXUS (GIC 2026 Phase-3)

Companion to `results/platform_feedback_qbraid.md`. Everything here is either fetched from the
platform by job ID or regenerated deterministically from the committed submission repository
(qbraid SDK 0.12.1; circuits are portable OpenQASM 2.0 using `ry/rx/rz/cx` + measurement only).

## Issue 1 — qir-sv deviation at n=12 (`issue1_qirsv_n12/`)

| file | content |
|---|---|
| `finance_n12_w{0,1,2}_scale1.qasm` | the three n=12 circuits, regenerated deterministically (seed 0, coupling 0.5, 20 Trotter layers, S&P-500 RV lag windows). Angles emitted mod 2π — measurement-equivalent to the originals. |
| `counts_*.json` | raw counts fetched from the three cloud jobs (2,000 shots each) |
| `comparison.json` | per-window scoring, recomputed from these files |

Recomputed from this bundle (mean / max abs deviation over all 78 Z/ZZ observables):

| window | cloud vs exact-sim-of-same-QASM | exact-sim vs independent engine |
|---|---|---|
| 0 | 0.125 / 0.422 | 0.009 (Trotter systematic only) |
| 1 | 0.137 / 0.404 | 0.008 |
| 2 | 0.176 / 0.458 | 0.011 |

At n≤10 the identical pipeline sits at the shot floor (~0.016); artifact
`results/hosted_runtime_check.json` has the full battery including all 18 job IDs, reproducible
end-to-end with `python3 hosted_runtime_check.py`.

Job IDs:
- `qbraid:qbraid:sim:qir-sv-bd52-qjob-6a491ef60d6e5eddfaac7df3`
- `qbraid:qbraid:sim:qir-sv-bd52-qjob-6a49211c0d6e5eddfaac7ed0`
- `qbraid:qbraid:sim:qir-sv-bd52-qjob-6a4923430d6e5eddfaac7fe1`

## Issue 2 — IonQ Forte-1 negative-angle rotation lost (`issue2_ionq_negative_angle/`)

| file | content |
|---|---|
| `cal0_identity_pair_as_submitted.qasm` | the identity circuit as submitted: `ry(π) q[i]; ry(−π) q[i];` per qubit, n=8 |
| `client_side_ionq_json.json` | output of `qbraid.transpiler.conversions.openqasm3.openqasm3_to_ionq` for that QASM — **all 16 gates present with signed rotations**, proving the loss is not client-side |
| `counts_identity_pair_job_6a4a7ba4.json` | measured counts, job `openquantum:ionq:qpu:forte-1-bd52-qjob-6a4a7ba40d6e5eddfaacfcbe`: **`11111111` = 474/500 (94.8%)** — net RY(π) per qubit; expected ~all `00000000` |
| `control_rz_cal0_as_submitted.qasm` | diagonal-only \|0…0⟩ preparation (`rz(0.5)` per qubit) |
| `counts_rz_control_job_6a4a9322.json` | same device, same day, job `...qjob-6a4a93220d6e5eddfaad0802`: **`00000000` = 498/500 (99.6%)** — readout is excellent; the identity-pair job's state preparation was wrong |

One-line reproduction of the client-side evidence:

```python
from qbraid.transpiler.conversions.openqasm3 import openqasm3_to_ionq
print(openqasm3_to_ionq(open("cal0_identity_pair_as_submitted.qasm").read()))
# -> [{'gate': 'ry', 'target': 0, 'rotation': 3.14159265359},
#     {'gate': 'ry', 'target': 0, 'rotation': -3.14159265359}, ...]
```

Impact: any circuit containing negative rotation angles is silently mis-executed on this route —
including standard ZNE gate folding (which emits inverse gates) and Hamiltonians with mixed-sign
couplings. Jobs complete with no warning. Our committed workaround: emit all rotation angles
mod 2π (measurement-equivalent up to global phase) and build \|0…0⟩ calibrations from diagonal
gates only (`qpu_run.py`, commits `90df445` and follow-ups).

## Verifying the fetched counts yourself

Every counts file can be re-fetched by job ID:

```python
from qbraid.runtime import QbraidProvider
from qbraid.runtime.native import QbraidJob
job = QbraidJob("<job id above>", client=QbraidProvider().client)
print(job.result().data.get_counts())
```
