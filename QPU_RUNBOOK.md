# QPU run-book — executing CHIMERA-QRC on real quantum hardware

The submission is **one flag** from a real-hardware run. Everything except the QPU credits is
built, wired, and validated on a simulator. This run-book is the exact procedure; the only
blocker is qBraid/Braket/IBM credits/access.

## 0. Check readiness (no credits needed)
```bash
python3 qbraid_submit.py --dry-run                       # prints the gate/observable/shot/cost plan
python3 qbraid_submit.py --dry-run --device <backend>    # also probes whether the device opens
```
When `--dry-run --device <backend>` prints `device wiring: OK ... READY`, drop `--dry-run` to run.

## 1. What runs on hardware
The **gate-Trotter** circuit (n=8, 20 layers): **220 two-qubit (IsingZZ) + 160 one-qubit (RX) =
380 native gates**, then **36 Z-diagonal observables** read from **one shot set** (all
`⟨Z_i⟩,⟨Z_iZ_j⟩` are diagonal in the computational basis — no extra bases). The random ~50%-Ising
needs *fewer* two-qubit gates than an all-to-all reservoir (≈720), easing NISQ mapping;
trapped-ion (IonQ) supports the arbitrary couplings natively.

## 2. Cost estimate (per the dry-run)
- ~6 input windows × 4,000 shots ≈ **24k shots** for the headline feature read (one shot set
  yields all 36 observables). The classical cross-check and Trotter-error term are free (simulator).
- ZNE adds 2–3 noise-scaled copies; measurement mitigation adds a calibration circuit.
- Budget ~50–80k shots for a complete headline run with mitigation — well within a small credit grant.

## 3. Device strings (PennyLane plugins; install on qBraid)
- **IonQ via Braket:** `braket.aws.qubit` with the IonQ device ARN (set via the plugin/device args).
- **IQM / IBM via Qiskit:** `qiskit.remote` with the backend handle (needs `pennylane-qiskit`).
- **Local noisy reference:** no `--device` (uses `default.qubit`/`default.mixed`) — fully runnable now.

## 4. Run
```bash
python3 qbraid_submit.py --device <backend> --shots 4000
```
This (i) runs the **classical cross-check** — the exact-evolution circuit (`QubitUnitary`) vs the
NumPy engine, which on a simulator matches to **3.9e-16** (the invariant we re-verify on every
hardware execution), (ii) measures the **shot budget** (ε≈1/√S), and (iii) applies **ZNE**.

## 5. What "success" looks like
- **Cross-check**: on a *simulator* the exact circuit matches the engine to ~1e-16. On hardware the
  *raw* features will differ from the noiseless reference by the device's 2-qubit error accumulated
  over 220 gates; **ZNE + measurement mitigation should move the mitigated features toward the
  noiseless cross-check value.** That convergence — mitigated-hardware → classical cross-check — is
  the validation, not bit-exactness.
- **Honest scope**: this validates that the reservoir *circuit runs and is the reservoir under
  mitigation*. It is **not** a quantum-advantage claim — the study's conclusion (no advantage at
  simulable scale) is unchanged. The open scientific question (advantage beyond the classical-
  simulation frontier, 50–256 qubits) needs a much larger device and is explicitly left open.

## 6. Expected noise on real hardware (see `noisy_circuit_study.py`)
The per-layer-noise study shows accumulated two-qubit error over the 380-gate circuit genuinely
degrades the features (unlike readout-only depolarizing, which per-feature standardization removes
exactly). So budget for ZNE and expect the *mitigated* features — not the raw ones — to track the
classical cross-check.
