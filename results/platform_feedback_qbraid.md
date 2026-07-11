# Platform feedback — Team EIGENNEXUS (GIC 2026 Phase-3, Track A)

*Two reproducible platform observations from our hardware/simulator campaign, with job IDs and
reproduction details. Environment: qbraid SDK 0.12.1, portable OpenQASM 2.0 (`ry/rx/rz/cx` +
full measurement only), submitted via `QbraidProvider`. Contact: Team EIGENNEXUS.*

---

## Issue 1 — qir-sv cloud simulator: reproducible deviation at n=12 (n≤10 exact to the shot floor)

**Device:** `qbraid:qbraid:sim:qir-sv`  ·  **Shots:** 2,000/job (device cap), counts summed across jobs

**Setup.** The same emitter produced circuits at n=8, 10, 12 (8-qubit-style Trotterized
transverse-field Ising reservoir; ~380 native gates at n=8). Every run is scored two ways:
against a local exact statevector simulation of the *identical QASM string*, and against an
independent exact NumPy engine. Expected agreement: the shot floor (~0.016 mean at 6,000
effective shots).

**Observation.** All n≤10 rows match the shot floor; the n=12 row deviates by ~9× the floor,
reproducibly (two independent runs ~1 hour apart gave the same deviation):

| domain | n | mean&nbsp;\|cloud−local\| | max | mean&nbsp;\|cloud−engine\| | max |
|---|---|---|---|---|---|
| finance | 8 | 0.0150 | 0.0448 | 0.0176 | 0.0647 |
| finance | 10 | 0.0167 | 0.0614 | 0.0167 | 0.0923 |
| mnist | 10 | 0.0190 | 0.0607 | 0.0197 | 0.0695 |
| weather | 10 | 0.0162 | 0.0495 | 0.0194 | 0.0651 |
| **finance** | **12** | **0.1460** | **0.4582** | **0.1427** | **0.4586** |

The local exact simulation of the same QASM matches the independent engine at every n
(max deviation ≈ Trotter systematic, ~0.04), so the emitted circuit is proven correct;
the deviation is cloud-side.

**n=12 job IDs (second run):**
`qbraid:qbraid:sim:qir-sv-bd52-qjob-6a491ef60d6e5eddfaac7df3`,
`...qjob-6a49211c0d6e5eddfaac7ed0`,
`...qjob-6a4923430d6e5eddfaac7fe1`
(full 18-job list in our committed artifact `results/hosted_runtime_check.json`).

**Reproduce:** `python3 hosted_runtime_check.py` in our submission repository re-runs the full
battery and re-scores against both references.

---

## Issue 2 — openquantum:ionq:qpu:forte-1: RY(π)·RY(−π) identity pair executes as net RY(π)

**Device:** `openquantum:ionq:qpu:forte-1`  ·  **Shots:** 500

**Setup.** As a |0…0⟩ readout-calibration circuit we submitted, per qubit (n=8), the exact
identity pair `ry(π) q[i]; ry(−π) q[i];` (used instead of an empty circuit because gate-less
programs are rejected at IonQ JSON validation — that part is presumably intended behavior).

**Observation.** The job COMPLETED normally but measured the *all-ones* state:

- **Job `openquantum:ionq:qpu:forte-1-bd52-qjob-6a4a7ba40d6e5eddfaacfcbe`** (2026-07-05):
  top outcome `11111111` with 474 of 500 shots (94.8%) — i.e. net RY(π) per qubit, as if the
  negative-angle rotation was never applied.

**Client-side evidence.** The qbraid transpiler output for this circuit
(`qbraid.transpiler.conversions.openqasm3.openqasm3_to_ionq`) provably contains **all 16 gates
with signed rotations** — e.g. `{"gate": "ry", "target": 0, "rotation": 3.14159265359}` followed
by `{"gate": "ry", "target": 0, "rotation": -3.14159265359}` — so the loss of the negative-angle
gate happens after client-side conversion (OpenQuantum relay or device-side compilation).

**Control confirming readout is not the cause.** A diagonal-only |0…0⟩ preparation
(`rz(0.5)` per qubit) on the same device the same day measured `00000000` at 99.6%:
**job `openquantum:ionq:qpu:forte-1-bd52-qjob-6a4a93220d6e5eddfaad0802`**. Readout is excellent;
the state preparation in the first job was wrong.

**Impact.** Any circuit containing negative rotation angles is silently mis-executed — this
includes standard zero-noise-extrapolation gate folding (which emits inverse gates) and any
Hamiltonian with mixed-sign couplings. The job completes with no warning.

**Our mitigation (workaround, committed in our repo):** emit every rotation angle mod 2π
(measurement-equivalent up to global phase) and build |0…0⟩ calibrations from diagonal gates
only. After hardening: the 99.6% result above.

---

*Both issues are documented with all artifacts in our Phase-3 submission repository; we're happy
to provide QASM files, raw counts, or run reproductions on request.*
