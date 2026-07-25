# QPU run-book — executing CHIMERA-QRC on real quantum hardware

> **Status: EXECUTED.** This run-book was written pre-execution; the program it describes has
> since run — **ten provenance-tagged QPU campaigns across three vendors / four devices** (IonQ,
> IQM Garnet, IQM Emerald, Rigetti). Results and per-job records:
> `results/qpu_hardware_findings.md`, `results/CREDIT_BUDGET.md`. The mechanics below are how
> those runs were produced and how a reader reproduces the *offline* pipeline (no credits needed).

The runner is **one command** from a real-hardware run. Everything except the QPU
credits is built, wired, and — as of `qpu_run.py` — **rehearsed end-to-end offline with the
identical hardware pipeline** (counts readout → readout-error mitigation → gate-folding ZNE
→ classical cross-check).

## The two runners (what each is for)

| script | role |
|---|---|
| `qbraid_submit.py` | *characterization*: shot-budget law, Trotter error, simulator ZNE demo, dry-run cost plan |
| `qpu_run.py` | **the credit-day runner**: hardware-grade pipeline (counts, calibration, folding ZNE, mitigation, job IDs) with an offline full-dress rehearsal mode |

## 0. Prove readiness today (no credits, no API key)
```bash
python3 qpu_run.py --selftest        # the emitted QASM2 IS the reservoir:
                                     #   max|QASM(Trotter20) − exact engine| ≈ 0.039 (the known
                                     #   Trotter systematic); fold-3 identity ≈ 1e-14
python3 cli.py run qpu_rehearsal     # FULL-DRESS offline rehearsal on a stand-in noisy QPU
                                     # (per-gate depolarizing + readout flips): runs calibration,
                                     # folding, ZNE, mitigation, cross-check — and verifies the
                                     # mitigation chain RECOVERS accuracy (see
                                     # results/qpu_readiness_findings.md for the committed run)
python3 qbraid_submit.py --dry-run   # gate/observable/shot/cost plan
```

## 1. What runs on hardware
The **gate-Trotter** circuit (n=8, 20 layers): **220 two-qubit + 160 one-qubit = 380 native
gates**, emitted as **portable OpenQASM 2** using only `ry/rx/rz/cx` (IsingZZ decomposed as
CX·RZ·CX — no plugin-specific decomposition surprises; validated by an independent
interpreter in `--selftest`). All **36 observables** ⟨Z_i⟩,⟨Z_iZ_j⟩ are computational-basis
diagonal → **one shot set per circuit yields every observable.**

Mitigation, hardware-grade (implemented natively in `qpu_run.py`, dependency-free):
- **Readout:** two calibration circuits (|0…0⟩, |1…1⟩) → per-qubit confusion matrices →
  exact tensor-model inversion (2⁸×2⁸ — mthree-style, trivial at n=8).
- **ZNE:** **global gate folding** U → U(U†U)ᵏ at noise scales 1/3/5 (folding verified to be
  an exact identity in the noiseless limit), linear + Richardson extrapolation per observable.
  (This replaces the simulator noise-dial — a real QPU's noise cannot be dialed.)
- **Classical cross-check:** every run scored against the exact NumPy engine features.

## 2. Credit day — the exact three commands
```bash
pip install -r requirements-qpu.txt        # qBraid runtime SDK (much is preinstalled on qBraid)
export QBRAID_API_KEY=<your key>           # qBraid account → API keys

python3 qpu_run.py --list-devices                          # 1. pick an ONLINE gate-model device
python3 qpu_run.py --mode hw --device qbraid_qir_simulator # 2. free cloud smoke test (if listed)
python3 qpu_run.py --mode hw --device <ionq/ibm/... id> --shots 4000   # 3. THE run
```
Job IDs are logged and saved with the results (`results/qpu_run_hw_<tag>.json` and the resumable
`results/qpu_ckpt_hw_<tag>.json`, which also holds the raw per-window counts) for full provenance.

## 3. Cost estimate
3 windows × 3 fold-scales × 4,000 shots + 2 calibration circuits ≈ **11 circuits / ~44k
shots** for the complete mitigated headline run. Budget ~50–80k shots to allow a repeat —
well within a small credit grant. (Fold-5 circuits are ≈1,900 native gates; if the target
device's fidelity budget is tight, run scales 1/3 only — pass `--scales 1 3`.)

## 4. What "success" looks like
- On the **rehearsal** (committed): raw → readout-mitigated → ZNE strictly reduces the mean
  feature error vs the exact engine. On **hardware** the same monotone chain — mitigated
  features converging toward the classical cross-check — **is the validation**, not
  bit-exactness. The known Trotter-20 systematic (~0.04) is the floor.
- **Honest scope:** this validates that the reservoir circuit *runs and is the reservoir
  under mitigation*. It is **not** a quantum-advantage claim — the study's conclusion (no
  advantage at simulable scale) is unchanged; the open question (beyond-frontier scale)
  stays open.

## 5. Expected hardware noise (see `noisy_circuit_study.py`)
Per-layer noise accumulated over 220 two-qubit gates genuinely degrades the features (unlike
readout-only depolarizing, which standardization removes). At ~99.5% two-qubit fidelity the
raw fold-1 circuit fidelity is roughly 0.995²²⁰ ≈ 0.33 — so expect visibly degraded raw
features and rely on the mitigation chain; that is precisely what the rehearsal exercises.

## 6. Fallbacks
- `--mode pl --device <pennylane device string>` runs the identical pipeline through any
  PennyLane plugin (install the plugin per `requirements-qpu.txt` comments).
- If a queue stalls: each window×scale is an independent job — results accumulate; re-run
  with fewer `--windows` / `--scales` to fit an allocation.
