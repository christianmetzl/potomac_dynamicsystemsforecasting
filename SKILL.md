# CHIMERA-QRC — qBraid Skill (agent-executable reproduction interface)

**Team EIGENNEXUS · GIC 2026 Phase 3 · Track A (Financial Volatility)**

This is the functional, agent-executable interface the Phase-3 brief requires: it
lets an AI coding agent (or a judge) **navigate the codebase, configure the
reservoir, run training, and reproduce every result end-to-end** — without reading
the source. It is not just documentation; `cli.py` is a working dispatcher and
`qbraid_skill.yaml` is its machine-readable index.

## Quickstart (any environment, incl. qBraid)

```bash
pip install -r requirements.txt        # numpy, scipy, pandas, statsmodels, arch, pennylane, matplotlib
python3 cli.py list                    # enumerate actions + groups
python3 cli.py run headline --quick    # fast smoke of the Phase-3 story
python3 cli.py reproduce               # full Phase-2 + Phase-3 reproduction
```

All data is bundled (Oxford-Man S&P 500 realized variance, SPY 2022–2026, and a
seeded MNIST subset), so it runs **offline**. The core engine is pure NumPy.

## How an agent uses this skill

1. **Discover**: `python3 cli.py list` or parse `qbraid_skill.yaml` → the `actions`
   list gives each action's `id`, `desc`, `cmd`, and `expect` (the headline number
   to look for). `reservoir_config` documents the knobs (n_qubits, tau, encoder,
   noise, …) and their ranges.
2. **Run**: `python3 cli.py run <action>` (add `--quick` where supported). Groups:
   `headline`, `phase2`, `reproduce`, `all`.
3. **Verify**: compare stdout against each action's `expect` field.

## The actions (what each proves)

| Action | What it shows | Expected headline |
|---|---|---|
| `tests` | engine correctness | 23 passed, 0 failed |
| `kernel` | quantum kernel distinctness | g(ESN→CHIMERA) ≈ 62 vs ≈ 4 control |
| `crisis` | regime-transition tracking | CHIMERA-3scale MZ R² 0.591 > HAR 0.559 |
| `prereg` | pre-registered H0/H1/H4 thresholds | printed, fixed before running |
| `axisB` | encoding-density mechanism | informed qubits restore g (52→158), D_eff (1.5→3.1) vs idle |
| **`axisB_rig`** | **decisive honest test (HAR-X, recurrent-ESN, RFF; HAC-DM; Holm)** | **HAR-X best/co-best; CHIMERA n.s. → no quantum advantage at simulable scale; H0 refuted** |
| `scaling` | fixed-encoder bottleneck + noise | g/rank saturate (motivates Axis B) |
| `mnist` | common cross-team benchmark | accuracy 0.63→0.86 (n=5→12); CHIMERA ≫ linear, ≈ ESN |
| `mnist_noise` | noise robustness | invariant to depolarizing; robust to amplitude damping |
| `tensor` | scaling frontier + complexity | g(n) and bond dimension χ_eff(n) to n≈16 |
| `baselines`, `lstm` | classical bars | HAR strong; GARCH/AR/LSTM below it |

## Configuring the reservoir programmatically

```python
from qrc_engine import QuantumReservoir
qr = QuantumReservoir(n_qubits=10, tau=2.0, hamiltonian_type="ising",
                      connectivity=0.5, noise_type="amplitude_damping",
                      noise_rate=0.02, seed=0)
features = qr.step(x)         # encode -> evolve -> Pauli-Z readout
```
or the high-n sparse backend:
```python
from tensor_backend import chimera_features_sparse   # exact to ~1e-14 vs dense, reaches n~16
F = chimera_features_sparse(X, n=14, tau=2.0, seed=0)
```

## Hardware (Phase-3 plan)

Simulator-first (dense statevector ≤12q; sparse/TN to ~16q). QPU validation uses the
gate-Trotter circuit in `sdk_demo.py` (~380 native gates) on IonQ / IQM / IBM via
qBraid, with ZNE (Mitiq) + measurement mitigation (mthree) and a classical
cross-check for every hardware run. (QCi Dirac-3 is for the separate optimization
challenge, not this QRC track.)
