# RUNME — CHIMERA-QRC Phase-3 Executable Workflow

**Team:** EIGENNEXUS · **Project:** CHIMERA-QRC — Regime-Aware Quantum Reservoir Computing
for S&P-500 Realized-Volatility Forecasting · **Challenge:** GIC 2026 Dynamic Systems
Forecasting, **Track A — Financial Volatility** (qBraid · MITRE · JonesTrading).

This file is the step-by-step execution guide for judges and autonomous agents. It is written
to be run **top-to-bottom on qBraid with no external configuration**.

---

## 0. What this workflow does (1 paragraph)

Eight lagged log realized-variance values are angle-encoded onto qubits (`RY(π·x)`), evolved
under a fixed transverse-field Ising Hamiltonian `U = exp(-iHτ)`, and read out as single- and
pairwise Pauli-Z expectations into a ridge head that **already contains the HAR information
set** — so any reservoir gain is genuine nonlinearity beyond the strongest econometric
baseline. The headline test is **regime-transition forecast efficiency** (Mincer–Zarnowitz R²)
on the 2008-crisis split, vs HAR and the matched classical ESN reservoir.

---

## 1. Environment & dependencies

Python ≥ 3.10. All dependencies are public and pinned:

```bash
pip install -r requirements.txt
```

`requirements.txt`: `numpy scipy pandas statsmodels arch pennylane==0.45.0 matplotlib`.
No API keys, no private data, no network access required — the dataset is bundled (Section 3).

---

## 2. Launch on qBraid

[![Launch on qBraid](https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_white.png)](https://account.qbraid.com/?gitHubUrl=https://github.com/christianmetzl/potomac_dynamicsystemsforecasting.git)

1. Click **Launch on qBraid** (or `File → New → Clone Repo` in qBraid Lab with the repo URL).
2. Select the **Python 3 [Default]** environment (or create one and `pip install -r requirements.txt`).
3. Open **`qbraid_workflow.ipynb`** and run **Run → Run All Cells**.

Wall-clock: **≈ 30 seconds** end-to-end with the default `BACKEND='exact'` (validated NumPy
statevector engine). Set `BACKEND='pennylane'` in the config cell to route the identical model
through the PennyLane circuit (~100× slower, same numbers — see Section 5).

---

## 3. Inputs (public data, bundled)

| File | Description | Source |
|---|---|---|
| `data/oxfordman_spx_full.csv` | Oxford-Man Institute realized library, `.SPX` 5-min realized variance + measures, 2000–2019 | Oxford-Man Realized Library (public, archived) |

No proprietary or restricted data is used. The panel (rv5 lags + jump-robust measures) is
built by `multivariate_data.build_panel_supervised()`.

---

## 4. Expected outputs (what a correct run prints)

Running `qbraid_workflow.ipynb` top-to-bottom reproduces, in order:

| Cell | Output | Expected value |
|---|---|---|
| 2 — circuit validation | `max\|PennyLane circuit − exact engine\|` | **≈ 3.8e-15** (identical model) |
| 3 — headline MZ result | `CHIMERA-3scale MZ-R²` / `HAR` / `ESN-108` | **0.591 / 0.559 / 0.090** |
|  | `MZ-R² gap (CHIMERA − HAR)` | **+0.032** |
|  | `Diebold–Mariano (CHIMERA vs HAR)` | DM **+3.55**, p<0.001 (HAR better on point loss — honest) |
|  | `95% Model Confidence Set` | contains **CHIMERA-3scale and HAR**; excludes ESN-108 |
| 4 — shot noise | feature error at 100 / 1k / 10k shots | **≈ 0.063 / 0.020 / 0.006** |
| 4 — resource budget | total gates / depth at 10/20/32 Trotter steps | **388/768/1224 gates**, depth **161/321/513** |
| 5 — entanglement sweep | `g` at α = 0 / 0.25 / 1.0 | g large at **S=0**, not entanglement-bound |

**The headline claim:** CHIMERA-3scale has the **best regime-transition forecast efficiency
(MZ-R² = 0.591 > HAR 0.559)** and is in the 95% MCS, with the matched classical ESN excluded.

---

## 5. Running on real quantum hardware (QPU)

The reservoir is a genuine, hardware-portable circuit (`pennylane_reservoir.py`). To dispatch
the identical workflow to a QPU, change only the PennyLane device and set `trotter_steps` for
gate-based hardware (confirm the exact device string against current qBraid PennyLane-plugin
docs / the `qBraid-Computing/QRC-tutorials` repo):

```python
from pennylane_reservoir import make_reservoir_qnode
circuit = make_reservoir_qnode(N_QUBITS, J, tau=2.0, trotter_steps=32, shots=1000,
                               device='<qbraid-pennylane-device-string>')
```

**Backend rationale (resource-budget section of the paper):** IonQ (all-to-all native — best
match for the random-graph Ising, no SWAP overhead) as the gate-based validation control;
QuEra Aquila (analog neutral-atom — maps directly onto `exp(-iHτ)` and matches the 108-qubit-
QRC precedent, Kornjača 2024) as the scale path. Per-input shot budget at n=8, 3 scales,
3 seeds, 36 observables, 1000 shots ≈ **324,000 shots**.

---

## 6. Reproducing the full repository results (beyond the notebook)

The notebook is the **small-scale (n=8) Phase-3 prototype** the challenge calls for. The full
study is reproduced by the scripts (run `bash run_all.sh`, or individually):

| Script | Produces |
|---|---|
| `vol_crisis_benchmark.py` | crisis-split regime-transition benchmark (MZ table) |
| `scaling_sweep.py` | Axis-A scaling sweep g(n) / MZ-gap(n), pre-registered verdict |
| `mps_bond_scaling.py` | MPS tensor-network backend — bond-dimension scaling to n=16 |
| `entanglement_distinctness.py` | the entanglement→distinctness mechanism (full sweep) |
| `sdk_demo.py` | standalone PennyLane circuit validation (~380-gate Trotter) |

---

## 7. Known limitations / assumptions (honest)

- **Small-scale prototype:** the notebook runs n=8 on a simulator, per the Phase-3 brief
  (light-touch prototyping; full multi-qubit benchmarking deferred to execution phase).
- **Finite-shot noise** inflates feature error (Section 4); error mitigation (ZNE / M3 via
  Mitiq) is the planned QPU-path next step, not yet applied here.
- **Point RMSE:** CHIMERA wins on regime-transition MZ-efficiency and MCS membership, **not**
  on calm-period point RMSE (DM is positive) — reported transparently.
- The `'exact'` backend is a NumPy statevector simulator; the PennyLane circuit is proven
  equivalent to it (≈3.8e-15) in Cell 2, so the result is backend-independent.

---

## 8. Reproducibility checklist (for the agent/judge)

- [x] Single zipped folder `EIGENNEXUS_DynamicSystemsForecasting_Phase3.zip`.
- [x] Public data only, bundled in `data/`.
- [x] `requirements.txt` pinned; no external config / API keys.
- [x] `qbraid_workflow.ipynb` runs top-to-bottom on qBraid (~30 s).
- [x] Expected outputs tabulated above (Section 4) for verification.
- [x] Code organized by module; scripts well-commented and executable.
